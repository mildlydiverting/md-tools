/*! wiki-cite bookmarklet
 * Extracts citation data from Wikipedia / Wikimedia Commons File: pages.
 * Pulls from:
 *   - imageinfo extmetadata (artist, title, date, license, credit, usage terms)
 *   - Commons Structured Data (SDC) via wbgetentities on the file's M-id
 *   - Wikidata item for the depicted work (via P6243 "digital representation of"
 *     or the file page's own wikibase_item), giving creator (P170),
 *     inception (P571), medium (P186), dimensions (P2048 h / P2049 w),
 *     collection (P195), location (P276), inventory number (P217),
 *     and the collection URL on the institution's site (P973) when present.
 *
 * Output: floating panel with four tabs:
 *   - YAML frontmatter (machine-readable)
 *   - Markdown — TASL
 *   - Markdown — Kim's smush (Author (yyyy) Title. [Medium][dims]. Org, Loc. Available at url (Accessed) Licensed under License)
 *   - Eagle plain list
 */
(() => {
  if (window.__wikiCiteOpen) { window.__wikiCiteOpen(); return; }

  // ---- helpers ----
  const strip = s => s == null ? '' : String(s).replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim();
  const esc = s => (s == null ? '' : String(s))
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  const api = (base, params) => {
    const u = new URL(base);
    Object.entries({ format: 'json', formatversion: '2', origin: '*', ...params })
      .forEach(([k, v]) => v != null && u.searchParams.set(k, v));
    return fetch(u, { credentials: 'omit' }).then(r => r.json());
  };
  const today = () => {
    const d = new Date();
    return d.toISOString().slice(0, 10);
  };
  const yamlVal = v => {
    if (v == null || v === '') return '""';
    const s = String(v);
    if (/[\n:"'#\[\]{}&*!|>%@`,]/.test(s) || /^\s|\s$/.test(s) || /^(?:true|false|null|~|\d)/i.test(s)) {
      return '"' + s.replace(/\\/g, '\\\\').replace(/"/g, '\\"') + '"';
    }
    return s;
  };
  const unitLabels = { Q174728: 'cm', Q11573: 'm', Q218593: 'in', Q828224: 'km', Q11573: 'm' };
  const parseWdDate = (v) => {
    if (!v || !v.time) return '';
    const m = v.time.match(/^([+-])(\d+)-(\d{2})-(\d{2})/);
    if (!m) return v.time;
    const sign = m[1] === '-' ? '-' : '';
    const year = parseInt(m[2], 10);
    const p = v.precision;
    if (p <= 6) return sign + Math.floor(year / 100) + 'th century';
    if (p === 7) return sign + Math.floor(year / 100) + 'th century';
    if (p === 8) return sign + Math.floor(year / 10) * 10 + 's';
    if (p === 9 || p == null) return sign + year;
    if (p === 10) return sign + year + '-' + m[3];
    return sign + year + '-' + m[3] + '-' + m[4];
  };

  // ---- 1. identify file ----
  const m = location.pathname.match(/\/wiki\/(File:[^#?]+)/i);
  if (!m) {
    alert('wiki-cite: open a Wikipedia or Wikimedia Commons File: page first.');
    return;
  }
  const fileTitle = decodeURIComponent(m[1]).replace(/_/g, ' ');
  const hostApi = location.origin + '/w/api.php';
  const commonsApi = 'https://commons.wikimedia.org/w/api.php';
  const wdApi = 'https://www.wikidata.org/w/api.php';

  // ---- 2. gather data ----
  (async () => {
    // 2a. imageinfo + pageprops from current wiki
    let hostR, commonsR;
    try {
      hostR = await api(hostApi, {
        action: 'query',
        titles: fileTitle,
        prop: 'imageinfo|pageprops|info',
        iiprop: 'url|extmetadata|mime|size|canonicaltitle|timestamp',
        iiextmetadatafilter: 'Artist|ObjectName|ImageDescription|DateTimeOriginal|DateTime|LicenseShortName|LicenseUrl|UsageTerms|Credit|Permission|Categories|Attribution|AttributionRequired|License'
      });
    } catch (e) { hostR = null; }

    const hostPage = hostR && hostR.query && hostR.query.pages && hostR.query.pages[0];
    const ii = hostPage && hostPage.imageinfo && hostPage.imageinfo[0];
    const md = (ii && ii.extmetadata) || {};
    const g = k => md[k] && md[k].value;
    const hostPageProps = (hostPage && hostPage.pageprops) || {};

    // 2b. commons page id (M-id) and pageprops — commons is authoritative for SDC
    let mid = null, commonsPage = null, commonsPid = null;
    try {
      commonsR = await api(commonsApi, {
        action: 'query',
        titles: fileTitle,
        prop: 'info|pageprops|imageinfo',
        iiprop: 'url|timestamp'
      });
      commonsPage = commonsR && commonsR.query && commonsR.query.pages && commonsR.query.pages[0];
      if (commonsPage && commonsPage.pageid) {
        commonsPid = commonsPage.pageid;
        mid = 'M' + commonsPid;
      }
    } catch (e) { }

    const commonsPageProps = (commonsPage && commonsPage.pageprops) || {};

    // 2c. SDC — get statements for the M-id
    let sdc = null;
    if (mid) {
      try {
        const r = await api(commonsApi, {
          action: 'wbgetentities',
          ids: mid,
          props: 'claims'
        });
        sdc = r && r.entities && r.entities[mid];
      } catch (e) { }
    }
    const sdcClaims = (sdc && (sdc.statements || sdc.claims)) || {};

    // 2d. Find the artwork's Wikidata item
    //   priorities: SDC P6243, pageprops.wikibase_item (file page itself if it's an artwork),
    //   on en.wiki pages wikibase_item may point to the artwork item.
    const firstQid = p => {
      const c = sdcClaims[p];
      if (c && c[0] && c[0].mainsnak && c[0].mainsnak.datavalue) {
        const v = c[0].mainsnak.datavalue.value;
        if (v && v.id) return v.id;
      }
      return null;
    };
    // P6243 = digital representation of; P180 = depicts (weaker fallback)
    let workQid = firstQid('P6243')
      || firstQid('P180')
      || commonsPageProps.wikibase_item
      || hostPageProps.wikibase_item
      || null;

    // 2e. Fetch the work item from Wikidata
    let workItem = null, workClaims = {};
    if (workQid) {
      try {
        const r = await api(wdApi, {
          action: 'wbgetentities',
          ids: workQid,
          props: 'claims|labels|descriptions|sitelinks/urls',
          languages: 'en',
          sitefilter: 'enwiki|commonswiki'
        });
        workItem = r && r.entities && r.entities[workQid];
        workClaims = (workItem && workItem.claims) || {};
      } catch (e) { }
    }

    // 2f. Resolve labels for referenced Q-ids
    const needLabels = new Set();
    const addQ = v => { if (v && v.id) needLabels.add(v.id); };
    ['P170', 'P186', 'P195', 'P276', 'P50', 'P571'].forEach(p => {
      (workClaims[p] || []).forEach(st => {
        if (st.mainsnak && st.mainsnak.datavalue) addQ(st.mainsnak.datavalue.value);
      });
    });
    // units for dimensions
    ['P2048', 'P2049'].forEach(p => {
      (workClaims[p] || []).forEach(st => {
        const v = st.mainsnak && st.mainsnak.datavalue && st.mainsnak.datavalue.value;
        if (v && v.unit && /\/(Q\d+)$/.test(v.unit)) needLabels.add(v.unit.match(/(Q\d+)$/)[1]);
      });
    });

    let labels = {};
    if (needLabels.size) {
      try {
        const ids = [...needLabels].join('|');
        const r = await api(wdApi, {
          action: 'wbgetentities',
          ids,
          props: 'labels|sitelinks/urls',
          languages: 'en',
          sitefilter: 'enwiki|commonswiki'
        });
        if (r && r.entities) {
          Object.entries(r.entities).forEach(([q, ent]) => {
            labels[q] = {
              label: ent.labels && ent.labels.en && ent.labels.en.value,
              url: ent.sitelinks && ent.sitelinks.enwiki && ent.sitelinks.enwiki.url
            };
          });
        }
      } catch (e) { }
    }

    const qLabel = qid => (labels[qid] && labels[qid].label) || qid;
    const qUrl = qid => (labels[qid] && labels[qid].url) || `https://www.wikidata.org/wiki/${qid}`;

    const claimStrings = p => (workClaims[p] || []).map(st => {
      const v = st.mainsnak && st.mainsnak.datavalue && st.mainsnak.datavalue.value;
      if (!v) return null;
      if (v.id) return { label: qLabel(v.id), qid: v.id };
      if (v.time) return { label: parseWdDate(v), qid: null };
      if (v.amount != null) {
        const unitQ = v.unit && v.unit.match(/(Q\d+)$/);
        const unit = unitQ ? (unitLabels[unitQ[1]] || qLabel(unitQ[1])) : '';
        return { label: parseFloat(v.amount) + (unit ? ' ' + unit : ''), amount: parseFloat(v.amount), unit };
      }
      if (typeof v === 'string') return { label: v };
      return null;
    }).filter(Boolean);

    // ---- 3. assemble canonical fields ----
    const creators = claimStrings('P170').length ? claimStrings('P170') : claimStrings('P50');
    const creator = creators.length ? creators.map(c => c.label).join(', ') : (strip(g('Artist')) || 'Unknown');
    const creatorUrl = creators[0] && creators[0].qid ? qUrl(creators[0].qid) : '';

    const workLabel = (workItem && workItem.labels && workItem.labels.en && workItem.labels.en.value) || '';
    const workTitle = workLabel || strip(g('ObjectName')) || strip(g('ImageDescription')) || fileTitle.replace(/^File:/, '').replace(/\.[a-z0-9]+$/i, '');

    const dateVals = claimStrings('P571');
    let date = dateVals.length ? dateVals.map(d => d.label).join(' – ') : strip(g('DateTimeOriginal'));
    // handle circa: look for qualifier P1480 Q5727902
    if (workClaims.P571 && workClaims.P571[0] && workClaims.P571[0].qualifiers && workClaims.P571[0].qualifiers.P1480) {
      const q = workClaims.P571[0].qualifiers.P1480[0];
      if (q && q.datavalue && q.datavalue.value && q.datavalue.value.id === 'Q5727902') date = 'c. ' + date;
    }
    // or earliest/latest qualifiers (P580/P582)
    if (workClaims.P571 && workClaims.P571[0] && workClaims.P571[0].qualifiers) {
      const qu = workClaims.P571[0].qualifiers;
      if (qu.P580 && qu.P582) {
        const s = parseWdDate(qu.P580[0].datavalue.value);
        const e = parseWdDate(qu.P582[0].datavalue.value);
        if (s && e) date = `c. ${s}–${e}`;
      }
    }

    const medium = claimStrings('P186').map(c => c.label).join(', ');
    const heights = claimStrings('P2048');
    const widths = claimStrings('P2049');
    const h = heights[0] && heights[0].amount;
    const w = widths[0] && widths[0].amount;
    const hUnit = heights[0] && heights[0].unit || 'cm';
    const dimensions = (h && w) ? `${h} × ${w} ${hUnit}` : '';

    const institutions = claimStrings('P195');
    const institution = institutions[0] ? institutions[0].label : '';
    const institutionUrl = institutions[0] && institutions[0].qid ? qUrl(institutions[0].qid) : '';
    const locations = claimStrings('P276');
    const locationStr = locations[0] ? locations[0].label : '';
    const inventory = (workClaims.P217 && workClaims.P217[0] && workClaims.P217[0].mainsnak.datavalue && workClaims.P217[0].mainsnak.datavalue.value) || '';

    // Canonical collection page URL (institution's own page for the work)
    //   P973 "described at URL" or P2634 varies; many artworks have P973 pointing to the museum page
    const collectionPageUrl = (() => {
      const c = (workClaims.P973 || []);
      for (const st of c) {
        const v = st.mainsnak && st.mainsnak.datavalue && st.mainsnak.datavalue.value;
        if (typeof v === 'string') return v;
      }
      return '';
    })();

    // License
    const license = strip(g('LicenseShortName'));
    const licenseUrl = (md.LicenseUrl && md.LicenseUrl.value) || '';
    const usageTerms = strip(g('UsageTerms'));
    const credit = strip(g('Credit'));
    const permission = strip(g('Permission'));

    // Permalink to file description page, with oldid if we can
    const descUrl = (ii && ii.descriptionurl)
      || (commonsPage && `https://commons.wikimedia.org/wiki/${encodeURIComponent(fileTitle.replace(/ /g, '_'))}`)
      || location.href;
    const descShortUrl = (ii && ii.descriptionshorturl) || '';
    const revid = (commonsPage && commonsPage.lastrevid) || (hostPage && hostPage.lastrevid);
    const permalink = revid ? `${descUrl.split('?')[0]}?oldid=${revid}` : descUrl;

    const imageUrl = ii && ii.url;
    const uploadDate = (ii && ii.timestamp) || strip(g('DateTime'));
    const accessed = today();
    const websiteName = commonsPage ? 'Wikimedia Commons' : (location.hostname.replace(/^www\./, ''));

    const data = {
      creator,
      creator_url: creatorUrl,
      title: workTitle,
      date,
      medium,
      dimensions,
      institution,
      institution_location: locationStr,
      institution_url: institutionUrl,
      collection_url: collectionPageUrl,
      inventory_number: inventory,
      permalink,
      image_url: imageUrl,
      website: websiteName,
      license,
      license_url: licenseUrl,
      usage_terms: usageTerms,
      credit,
      permission,
      date_uploaded: uploadDate,
      date_accessed: accessed,
      source_file: fileTitle,
      source_wikidata: workQid || '',
      source_structured_data: mid || ''
    };

    // ---- 4. formats ----
    // YAML
    const yaml = '---\n'
      + Object.entries(data)
        .map(([k, v]) => `${k}: ${yamlVal(v)}`)
        .join('\n')
      + '\n---';

    // JSON (bonus)
    const json = JSON.stringify(data, null, 2);

    // TASL: Title - Author (profile) - from Source under License
    const tLink = (text, url) => url ? `[${text}](${url})` : text;
    const tasl = [
      tLink(workTitle, permalink),
      creator ? (creatorUrl ? tLink(creator, creatorUrl) : creator) : 'Unknown',
      institution ? `from ${tLink(institution, collectionPageUrl || institutionUrl)}` : `from ${tLink(websiteName, permalink)}`,
      license ? `under ${tLink(license, licenseUrl)}` : ''
    ].filter(Boolean).join(' - ');

    // Kim's smush
    const medBits = [];
    if (medium) medBits.push(`[${medium}]`);
    if (dimensions) medBits.push(`[${dimensions}]`);
    const orgBits = [institution, locationStr].filter(Boolean).join(', ');
    const smush =
      `${creator} (${date || 'n.d.'}) _${workTitle}_.`
      + (medBits.length ? ' ' + medBits.join('') + '.' : '')
      + (orgBits ? ` ${orgBits}.` : '')
      + ` Available at [${permalink}](${permalink})`
      + ` (Accessed ${accessed}).`
      + (license ? ` Licensed under ${licenseUrl ? `[${license}](${licenseUrl})` : license}.` : '')
      + (collectionPageUrl ? `\n\nCollection page: [${institution || 'canonical'}](${collectionPageUrl})` : '');

    // Eagle plain
    const eagle = [
      `Artist: ${creator}`,
      `Title: ${workTitle}`,
      `Date: ${date || ''}`,
      `Medium: ${medium || ''}`,
      `Dimensions: ${dimensions || ''}`,
      `Permalink: ${permalink || ''}`
    ].join('\n');

    // ---- 5. panel ----
    renderPanel({ data, yaml, json, tasl, smush, eagle, workQid, mid });
  })().catch(err => {
    console.error(err);
    alert('wiki-cite: ' + (err && err.message || 'failed to fetch data'));
  });

  function renderPanel(parts) {
    // cleanup previous
    const prev = document.getElementById('wiki-cite-root');
    if (prev) prev.remove();

    const root = document.createElement('div');
    root.id = 'wiki-cite-root';
    root.style.cssText = 'all:initial;position:fixed;top:16px;right:16px;z-index:2147483647;font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text",system-ui,sans-serif;';
    const shadow = root.attachShadow({ mode: 'open' });

    const css = `
      :host { color-scheme: light dark; }
      .panel {
        width: 440px; max-width: calc(100vw - 32px); max-height: calc(100vh - 32px);
        background: #fdfdfc; color: #222;
        border: 1px solid rgba(0,0,0,0.14); border-radius: 10px;
        box-shadow: 0 12px 40px rgba(0,0,0,0.18);
        display: flex; flex-direction: column; overflow: hidden;
        font-size: 13px; line-height: 1.45;
      }
      @media (prefers-color-scheme: dark) {
        .panel { background: #1c1c1e; color: #ececec; border-color: rgba(255,255,255,0.14); }
        pre, textarea { background: #2a2a2c !important; color: #e8e8e8 !important; border-color: rgba(255,255,255,0.1) !important; }
        .tab { color: #cfcfcf !important; }
        .tab.active { color: #fff !important; border-color: #7aa7ff !important; }
        header, footer { background: #262628 !important; border-color: rgba(255,255,255,0.08) !important; }
        button.btn { background: #2f2f31 !important; color: #fff !important; border-color: rgba(255,255,255,0.15) !important; }
        button.btn:hover { background: #3a3a3d !important; }
        a { color: #7aa7ff !important; }
      }
      header {
        display: flex; align-items: center; justify-content: space-between;
        padding: 8px 10px 8px 14px; background: #f3f1ec;
        border-bottom: 1px solid rgba(0,0,0,0.08);
      }
      header .title { font-weight: 600; font-size: 13px; }
      header .sub { font-size: 11px; opacity: 0.7; }
      .tabs { display: flex; border-bottom: 1px solid rgba(0,0,0,0.08); overflow-x: auto; }
      .tab {
        padding: 8px 12px; cursor: pointer; font-size: 12px;
        border: 0; background: transparent; color: #555;
        border-bottom: 2px solid transparent; white-space: nowrap;
      }
      .tab.active { color: #111; border-color: #3a5bd4; }
      .body { padding: 10px 12px; overflow: auto; }
      pre, textarea {
        margin: 0; padding: 10px; background: #f6f4ef; color: #222;
        border: 1px solid rgba(0,0,0,0.08); border-radius: 6px;
        font-family: ui-monospace, "SF Mono", Menlo, monospace;
        font-size: 11.5px; line-height: 1.5;
        white-space: pre-wrap; word-break: break-word; width: 100%;
        box-sizing: border-box; min-height: 160px; max-height: 50vh;
        resize: vertical;
      }
      .row { display: flex; gap: 6px; margin-top: 8px; flex-wrap: wrap; }
      button.btn {
        border: 1px solid rgba(0,0,0,0.15); background: #fff; color: #111;
        border-radius: 6px; padding: 5px 10px; cursor: pointer; font-size: 12px;
      }
      button.btn:hover { background: #efede8; }
      .close { background: transparent; border: 0; cursor: pointer; font-size: 16px; opacity: 0.6; padding: 4px 6px; color: inherit;}
      .close:hover { opacity: 1; }
      .meta { padding: 6px 12px 8px; font-size: 11px; opacity: 0.75; }
      .meta a { color: inherit; }
      footer { padding: 6px 12px; background: #f3f1ec; border-top: 1px solid rgba(0,0,0,0.08); font-size: 11px; opacity: 0.75; display:flex; justify-content: space-between; gap: 8px; }
    `;

    const html = `
      <style>${css}</style>
      <div class="panel" role="dialog" aria-label="Wiki citation">
        <header>
          <div>
            <div class="title">wiki-cite</div>
            <div class="sub">${esc(parts.data.title)} — ${esc(parts.data.creator)}</div>
          </div>
          <button class="close" aria-label="Close">×</button>
        </header>
        <div class="tabs" role="tablist">
          <button class="tab active" data-fmt="yaml">YAML</button>
          <button class="tab" data-fmt="smush">Markdown (yours)</button>
          <button class="tab" data-fmt="tasl">TASL</button>
          <button class="tab" data-fmt="eagle">Eagle</button>
          <button class="tab" data-fmt="json">JSON</button>
        </div>
        <div class="body">
          <textarea id="out" readonly spellcheck="false"></textarea>
          <div class="row">
            <button class="btn" id="copy">Copy</button>
            <button class="btn" id="copyall">Copy all formats</button>
            <a class="btn" style="text-decoration:none;" href="${esc(parts.data.permalink)}" target="_blank">File page ↗</a>
            ${parts.data.collection_url ? `<a class="btn" style="text-decoration:none;" href="${esc(parts.data.collection_url)}" target="_blank">Collection page ↗</a>` : ''}
          </div>
          <div class="meta">
            ${parts.workQid ? `Wikidata: <a href="https://www.wikidata.org/wiki/${esc(parts.workQid)}" target="_blank">${esc(parts.workQid)}</a>` : 'No linked Wikidata work item found.'}
            ${parts.mid ? ` · Commons SDC: <a href="https://commons.wikimedia.org/wiki/Special:EntityPage/${esc(parts.mid)}" target="_blank">${esc(parts.mid)}</a>` : ''}
          </div>
        </div>
        <footer>
          <span>Fields pulled from imageinfo + Commons SDC + Wikidata.</span>
          <span>Accessed ${esc(parts.data.date_accessed)}</span>
        </footer>
      </div>
    `;

    shadow.innerHTML = html;
    document.documentElement.appendChild(root);

    const out = shadow.getElementById('out');
    const tabs = shadow.querySelectorAll('.tab');
    const fmts = { yaml: parts.yaml, smush: parts.smush, tasl: parts.tasl, eagle: parts.eagle, json: parts.json };
    const show = (fmt) => {
      tabs.forEach(t => t.classList.toggle('active', t.dataset.fmt === fmt));
      out.value = fmts[fmt] || '';
    };
    tabs.forEach(t => t.addEventListener('click', () => show(t.dataset.fmt)));
    show('yaml');

    shadow.querySelector('.close').addEventListener('click', () => root.remove());

    const flash = (btn, text) => {
      const old = btn.textContent; btn.textContent = text;
      setTimeout(() => btn.textContent = old, 1200);
    };

    shadow.getElementById('copy').addEventListener('click', async (e) => {
      try { await navigator.clipboard.writeText(out.value); flash(e.target, 'Copied ✓'); }
      catch { out.select(); document.execCommand('copy'); flash(e.target, 'Copied ✓'); }
    });

    shadow.getElementById('copyall').addEventListener('click', async (e) => {
      const bundle =
        '--- YAML ---\n' + parts.yaml +
        '\n\n--- Markdown (yours) ---\n' + parts.smush +
        '\n\n--- TASL ---\n' + parts.tasl +
        '\n\n--- Eagle ---\n' + parts.eagle +
        '\n\n--- JSON ---\n' + parts.json;
      try { await navigator.clipboard.writeText(bundle); flash(e.target, 'Copied ✓'); }
      catch { flash(e.target, 'Copy failed'); }
    });

    window.__wikiCiteOpen = () => {
      if (!document.getElementById('wiki-cite-root')) document.documentElement.appendChild(root);
    };
  }
})();
