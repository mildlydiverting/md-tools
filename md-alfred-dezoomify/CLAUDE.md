# CLAUDE.md — dezoomify upstream contributions

## Who I am

Kim (GitHub: mildlydiverting / ovdixon). Artist and drawing teacher. I use dezoomify-rs in an Alfred workflow to download high-res artwork images from museum sites. I've found a bug in how dezoomify-rs handles IIIF manifests and want to contribute a fix upstream. I also want to check whether the JS dezoomify web app has the same gap.

British English throughout. Be direct, avoid effusiveness.

## Local repos

- **dezoomify-rs** (Rust CLI): `~/Development/dezoomify-rs`
  - Upstream: https://github.com/lovasoa/dezoomify-rs
  - My fork: TBD (will fork before PR)
  
- **dezoomify** (JS web app): `~/Development/dezoomify`
  - Upstream: https://github.com/lovasoa/dezoomify
  - Dezoomers live in: `dezoomers/` directory

## The problem: IIIF Presentation API v2 manifests

dezoomify-rs claims to support IIIF manifests as input. It works with **Presentation API v3** manifests (which use `type: "Manifest"` and `items[]` for canvases). But it **fails on v2 manifests**, which use `@type: "sc:Manifest"` and `sequences[].canvases[]`.

This matters because many major museum sites still serve v2 manifests:
- Art Institute of Chicago (`api.artic.edu`)
- Harvard Art Museums
- Wellcome Collection
- Many others — v2 is still more common than v3 in the wild

### Error observed

```
[WARN ] Attempted to parse IIIF manifest from https://api.artic.edu/api/v1/artworks/103887/manifest.json but 'type' field...
```

dezoomify-rs looks for `type` (v3) but the manifest has `@type` (v2).

### What the fix should do

When parsing an IIIF manifest, dezoomify-rs should:

1. Check for v3 structure first (`type: "Manifest"`, `items[]`)
2. Fall back to v2 structure (`@type: "sc:Manifest"`, `sequences[].canvases[]`)
3. Extract the IIIF Image API service URL from either version
4. Construct the `info.json` URL and proceed with the existing IIIF image dezoomer

### IIIF v2 manifest structure (the one that needs adding)

```json
{
  "@context": "http://iiif.io/api/presentation/2/context.json",
  "@type": "sc:Manifest",
  "sequences": [{
    "@type": "sc:Sequence",
    "canvases": [{
      "@type": "sc:Canvas",
      "label": "Image label",
      "width": 843,
      "height": 1014,
      "images": [{
        "@type": "oa:Annotation",
        "resource": {
          "@type": "dctypes:Image",
          "service": {
            "@context": "http://iiif.io/api/image/2/context.json",
            "@id": "https://www.artic.edu/iiif/2/IMAGE-UUID-HERE",
            "profile": "http://iiif.io/api/image/2/level2.json"
          }
        }
      }]
    }]
  }]
}
```

The key path to the image service: `sequences[0].canvases[].images[].resource.service.@id`

Then append `/info.json` to get the IIIF Image API endpoint.

### IIIF v3 manifest structure (already supported)

```json
{
  "@context": "http://iiif.io/api/presentation/3/context.json",
  "type": "Manifest",
  "items": [{
    "type": "Canvas",
    "items": [{
      "type": "AnnotationPage",
      "items": [{
        "type": "Annotation",
        "body": {
          "type": "Image",
          "service": [{
            "id": "https://example.com/iiif/image1",
            "type": "ImageService3"
          }]
        }
      }]
    }]
  }]
}
```

### Edge cases to handle

- `service` can be a single object or an array (both are valid IIIF)
- v2 uses `@id` for identifiers; v3 uses `id` (but some v3 manifests include `@id` for backwards compatibility)
- v2 `label` is a plain string; v3 `label` is a language map `{"en": ["Label"]}`
- Multi-canvas manifests (e.g. manuscripts) should produce multiple image downloads
- Some manifests have nested service declarations (service within service)

## Test URLs

### v2 manifests (currently failing)

```
https://api.artic.edu/api/v1/artworks/103887/manifest.json
```
→ Should extract: `https://www.artic.edu/iiif/2/2d9fb8b5-b9a3-3e41-270e-3c480f7b317b/info.json`

### v3 manifests (should continue working)

Test with any working IIIF v3 manifest to confirm no regression.

### Direct info.json (should continue working)

```
https://www.artic.edu/iiif/2/2d9fb8b5-b9a3-3e41-270e-3c480f7b317b/info.json
```
→ This already works. The fix is about getting here *via* a manifest.

### Collection page URLs (the real user journey)

```
https://www.artic.edu/artworks/103887/a-young-lady-with-a-parrot
https://www.rijksmuseum.nl/en/collection/object/Nude-Woman-Lying-on-a-Pillow--6af483682af3df3a835a526f7beb07f3
https://harvardartmuseums.org/collections/object/299848
https://wellcomecollection.org/works/zs6gser7/images?id=c7hxpemj
https://www.nationalgallery.org.uk/paintings/paolo-uccello-the-battle-of-san-romano
https://www.metmuseum.org/art/collection/search/435809
```

## Where to look in dezoomify-rs

The IIIF dezoomer code will be in `src/` — likely a file or module named `iiif` or similar. Look for:
- The manifest parsing logic (where `type` is checked)
- The struct definitions for manifest/canvas/image
- JSON deserialization (probably serde)

Start by finding where the warning message is emitted:
```
grep -r "type.*field" src/ --include="*.rs"
grep -r "manifest" src/ --include="*.rs" -l
```

The fix likely involves:
1. Adding v2 struct definitions alongside the v3 ones
2. Trying v3 deserialization first, falling back to v2
3. Both paths converging on extracting the image service URL

## Where to look in dezoomify (JS web app)

Check `dezoomers/iiif.js` to see whether it already handles v2 manifests. If it does, its approach might inform the Rust fix. If it doesn't, it needs the same fix.

```
cat dezoomers/iiif.js
```

Also check `dezoomers/automatic.js` to understand how the dezoomer selection works.

## Approach

1. **Read the existing IIIF code** in dezoomify-rs first. Understand the current parsing before changing anything.
2. **Check dezoomify-rs issues** — someone may have already reported this. Search for "v2", "Presentation 2", "@type", "sc:Manifest".
3. **Write the fix** with tests.
4. **Check the JS version** for the same gap.
5. **Write clear commit messages** and PR descriptions referencing the IIIF spec versions.

## IIIF specs for reference

- Presentation API v2: https://iiif.io/api/presentation/2.1/
- Presentation API v3: https://iiif.io/api/presentation/3.0/
- Image API v2: https://iiif.io/api/image/2.1/
- Image API v3: https://iiif.io/api/image/3.0/

## My Alfred workflow (context, not part of the upstream fix)

I've already worked around this in my Alfred workflow (`dezoomify_save.py` v1.3) by:
1. Adding an AIC-specific scraper that calls their API directly
2. Adding a generic IIIF v2 manifest resolver that parses manifests in Python and extracts info.json URLs

The upstream fix in dezoomify-rs would make both of those workarounds unnecessary for anyone using dezoomify-rs directly.

## Related project files

- Test cases doc: `~/Development/are.na-toolkit/dezoomify-alfred/dezoomify-test-cases.md`
- Alfred workflow: `~/Development/are.na-toolkit/dezoomify-alfred/dezoomify_save.py` (v1.3)
- Structured data audit (museum site markup research): `structured-data-audit-handoff.md`
