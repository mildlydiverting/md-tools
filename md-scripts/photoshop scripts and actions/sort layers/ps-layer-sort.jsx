// Layer sort https://community.adobe.com/t5/photoshop-ecosystem-discussions/sort-order-selected-layers-alphabetically/m-p/9672558#M148703 Here is new version whithout "while" cycle )

var idx_shift = 0;    
try { activeDocument.backgroundLayer } catch (e) { idx_shift = 1; }    
var list = get_selected_layers();    
if (list) 
    {
    var orig_idx = new Array();    
    for (var i in list) orig_idx.push(list[1]);    
    function cmp(a, b)     
        {    
        var x = expand_numbers(a[0]);    
        var y = expand_numbers(b[0]);    
        if (x > y) return -1;    
        if (x < y) return 1;    
        return 0;    
        }    
    list.sort(cmp);    
    for (var i = list.length-1; i >= 0; i--) set_layers_index(list[2], orig_idx);    
    }
alert("Done!");    
    
//////////////////////////////////////////////////////////////////    
function set_layers_index(id, idx)    
    {    
    try {    
        var d = new ActionDescriptor();    
    
        var r1 = new ActionReference();    
        r1.putIdentifier( charIDToTypeID( "Lyr " ), id);    
    
        var r2 = new ActionReference();    
        r2.putIndex( charIDToTypeID( "Lyr " ), idx-idx_shift );    
    
        d.putReference( charIDToTypeID( "null" ), r1 );    
        d.putReference( charIDToTypeID( "T   " ), r2 );    
    
        executeAction( charIDToTypeID( "move" ), d, DialogModes.NO );    
        }    
    catch (e) { alert(e); throw(e); }    
    }    
    
//////////////////////////////////////////////////////////////////    
function get_selected_layers()    
    {    
    try {    
        var r = new ActionReference();        
        r.putProperty(charIDToTypeID("Prpr"), stringIDToTypeID("targetLayers"));       
        r.putEnumerated(charIDToTypeID("Dcmn"), charIDToTypeID("Ordn"), charIDToTypeID("Trgt"));    
    
        var list = executeActionGet(r).getList(stringIDToTypeID("targetLayers"));    
    
        var len = list.count;    
        
        var selected_layers = new Array();    
        
        for (var i = 0; i < len; i++)    
            {    
            try     
                {    
                var idx = list.getReference(i).getIndex() + idx_shift;    
    
                var r = new ActionReference();    
                r.putIndex( charIDToTypeID( "Lyr " ), idx);    
                var ret = executeActionGet(r);
    
                selected_layers.push([ret.getString(stringIDToTypeID("name")), idx, ret.getString(stringIDToTypeID("layerID"))]);    
                }    
    
            catch (e) { alert(e); return null; }    
            }    
        
        return selected_layers;    
        }    
    
    catch (e) { return null; }    
    }    
    
////////////////////////////////////////////////////////////////////////////////////////////    
function expand_numbers(s, max_digit)    
    {    
    if (max_digit == undefined) max_digit = 10;        
    
    var digit_cnt;    
    
    s = s.toString();    
        
    var len = s.length;    
    
    var s1 = "";    
    
    for (var i = len-1; i >= 0; i--)     
        {    
        var c = s.charAt(i);    
    
        if (c >= "0" && c <="9")    
            {    
            if (digit_cnt == undefined)         
                digit_cnt = 1;    
            else                            
                ++digit_cnt;    
    
            s1 += c;    
            }    
        else if (digit_cnt != undefined)     
            {    
            if (digit_cnt < max_digit) for (var n = 0; n < max_digit-digit_cnt; n++) s1 += "0";    
    
            s1 += c;    
            digit_cnt = undefined;    
            }    
        else    
            {    
            s1 += c;    
            }    
        }    
    
    if (digit_cnt != undefined && digit_cnt < max_digit)    
        for (var n = 0; n < max_digit-digit_cnt; n++) s1 += "0";    
    
    len = s1.length;    
    
    var ret = "";    
    
    for (var i = len-1; i >= 0; i--) ret += s1.charAt(i);    
    
    ret = ret.toUpperCase();    
    
    return ret;    
    }    