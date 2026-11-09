// https://community.adobe.com/t5/photoshop-ecosystem-discussions/sort-order-selected-layers-alphabetically/m-p/11821061#M511630

var layers = activeDocument.layers;
    var layersArray = [];
    var len = layers.length;
    


    // store all layers in an array
    for (var i = 0; i < len; i++) {
        layersArray.push(layers[i]);
    }

    // sort layer top to bottom
    layersArray.sort();

    for (i = 0; i < len; i++) {
        layersArray[i].move(layers[i], ElementPlacement.PLACEBEFORE);
    }
