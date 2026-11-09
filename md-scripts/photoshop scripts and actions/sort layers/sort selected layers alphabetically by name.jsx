// Sort selected layers alphabetically by name with a sorting order dialog
function sortSelectedLayersByName() {
    var doc = activeDocument;
    var selectedLayers = getSelectedLayers();

    // Show a dialog box to choose sorting order
    var sortingOrder = showSortingDialog();
    if (sortingOrder === null) return; // Exit if the dialog was canceled

    // Sort the selected layers by name based on the chosen order
    selectedLayers.sort(function (a, b) {
        var comparison = a.name.toLowerCase().localeCompare(b.name.toLowerCase());
        return sortingOrder === "A-Z" ? comparison : -comparison;
    });

    // Move each layer to its new position
    for (var i = 0; i < selectedLayers.length; i++) {
        selectedLayers[i].move(doc, ElementPlacement.PLACEATEND);
    }

    // Function to get selected layers
    function getSelectedLayers() {
        var selLayers = [];
        var ref = new ActionReference();
        ref.putEnumerated(charIDToTypeID("Dcmn"), charIDToTypeID("Ordn"), charIDToTypeID("Trgt"));
        var desc = executeActionGet(ref);
        if (desc.hasKey(stringIDToTypeID("targetLayers"))) {
            var list = desc.getList(stringIDToTypeID("targetLayers"));
            for (var i = 0; i < list.count; i++) {
                var layerIndex = list.getReference(i).getIndex();
                activeDocument.activeLayer = activeDocument.layers[layerIndex];
                selLayers.push(activeDocument.activeLayer);
            }
        } else {
            selLayers.push(activeDocument.activeLayer);
        }
        return selLayers;
    }

    // Function to show sorting order dialog
    function showSortingDialog() {
        var dialog = new Window("dialog", "Sort Layers");
        dialog.orientation = "column";
        dialog.alignChildren = "left";

        dialog.add("statictext", undefined, "Select sorting order:");

        var dropdown = dialog.add("dropdownlist", undefined, ["A-Z", "Z-A"]);
        dropdown.selection = 0; // Default to "A-Z"

        var buttonGroup = dialog.add("group");
        buttonGroup.alignment = "right";
        var okButton = buttonGroup.add("button", undefined, "OK");
        var cancelButton = buttonGroup.add("button", undefined, "Cancel");

        okButton.onClick = function () {
            dialog.close(1);
        };
        cancelButton.onClick = function () {
            dialog.close(0);
        };

        if (dialog.show() == 1) {
            return dropdown.selection.text;
        } else {
            return null; // Dialog was canceled
        }
    }
}

sortSelectedLayersByName();