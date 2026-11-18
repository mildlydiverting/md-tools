/*
    Script Name: Swatch Group From CSV
    Author: William Dowling
    Email: illustrator.dev.pro@gmail.com

    If this is useful to you and you'd like to say thanks
        by buying me some coffee:
    Paypal: paypal.me/illustratordev
    
    Description:
        prompt user to select a csv file
        parse csv file and create a new
        swatch group for every valid row of the csv.
        Currently only handles RGB colors, but could be
        easily adapted to work with any color type.

    Modification: added HEX swatches if CSV has 2 columns and CMYK if CSV has 5 columns
    Author: Sergey Osokin, email: hi@sergosokin.ru

    Instructions:
        Open a blank document
        Run Script
        Select CSV file
        Tada. a new swatch group is created containing each
            swatch in the csv file.
        If you want to export this as a swatch library,
            remove all of the default colors leaving only
            the new swatch group. In the top right corner of
            the swatches panel click the menu button, then select
            "Save Swatch Library As ASE".
*/

//@target Illustrator

function createSwatchGroupFromCSV() {
    var valid = true; //running flag validation. if this is ever false, exit
    var csvFileRegex = /.csv$/i;
    var csvRows; //array of all rows in csv file

    //function definitions

    //send message to user
    function saySomething(msg) {
        //no need to check the operating system here
        //alerts work the same on windows and mac
        alert("Script message:\n" + msg);
    }

    function getCSV() {
        var userSelection;

        userSelection = File.openDialog("Select a CSV File", function (f) {
            return f instanceof Folder || csvFileRegex.test(f);
        })

        if (!userSelection) {
            saySomething("No CSV file selected.");
            valid = false;
        }
        return userSelection;
    }

    function readCSV() {
        //open the csv file to read it's contents
        //if the contents is an empty string, alert and exit
        //else, split by \n and set the resulting array to csvRows
        csvFile.open("r");
        var csvContents = csvFile.read();
        csvFile.close();

        if (csvContents === "") {
            saySomething("CSV file is blank.");
            valid = false;
            return;
        }

        csvRows = csvContents.replace(/["']/g,"").split("\n");
    }

    function processCSV() {
        var destSwatchGroup = activeDocument.swatchGroups.add();
        destSwatchGroup.name = csvFile.name.replace(/\.[^\.]+$/, ''); // Without extension

        //loop the csvRows array
        var curRow;
        for (var r = 1, len = csvRows.length; r < len && valid; r++) {
            curRow = csvRows[r];
            processRow(curRow, destSwatchGroup);
        }
    }

    if (valid) {
        var csvFile = getCSV();
    }

    if (valid) {
        readCSV();
    }

    if (valid) {
        processCSV();
    }

    if (valid) {
        saySomething("The swatch group was created successfully!");
    }
}

function processRow(row, swatchGroup) {
    var props;

    if (row === "" ){
        //nothing to see here.. just move on
        return;
    }

    var columns = row.indexOf(",") > -1 ? row.split(",") : row.split(";");

    switch (columns.length) {
      case 2: // HEX
        var rgbValue = hexToRgb(columns[1]);
        if (rgbValue == null) break;
        props =
            {
                name: columns[0] ? columns[0] : rgbValue.name,
                r: rgbValue.r,
                g: rgbValue.g,
                b: rgbValue.b
            }
        createRGBSwatch(swatchGroup, props);
        break;
      case 4: // RGB
      default:
        props =
            {
                name: columns[0],
                r: columns[1],
                g: columns[2],
                b: columns[3]
            }
        createRGBSwatch(swatchGroup, props);
        break;
      case 5: // CMYK
        props =
            {
                name: columns[0],
                c: columns[1],
                m: columns[2],
                y: columns[3],
                k: columns[4]
            }
        createCMYKSwatch(swatchGroup, props);
    }
}

function createRGBSwatch(dest, props) {
    var rgbColor = new RGBColor();
    rgbColor.red = getValidRGB(props.r);
    rgbColor.green = getValidRGB(props.g);
    rgbColor.blue = getValidRGB(props.b);

    var newSwatch = activeDocument.swatches.add();
    newSwatch.name = props.name;
    newSwatch.color = rgbColor;

    dest.addSwatch(newSwatch);
}

function getValidRGB(n) {
    if (n > 255) return 255;
    if (isNaN(n) || n == "" || n < 0) return 0;
    return n;
}

function createCMYKSwatch(dest, props) {
    var cmykColor = new CMYKColor();
    cmykColor.cyan = getValidCMYK(props.c);
    cmykColor.magenta = getValidCMYK(props.m);
    cmykColor.yellow = getValidCMYK(props.y);
    cmykColor.black = getValidCMYK(props.k);
    
    var newSwatch = activeDocument.swatches.add();
    newSwatch.name = props.name;
    newSwatch.color = cmykColor;

    dest.addSwatch(newSwatch);
}

function getValidCMYK(n) {
    if (n > 100) return 100;
    if (isNaN(n) || n == "" || n < 0) return 0;
    return n;
}

function hexToRgb(hex) {
  var hex = hex.replace(/[^0-9A-F]/gi, '');
  if (hex.length > 0 && hex.length < 6) {
    hex = ("000000" + hex).slice(-6);
  }
  return hex.length ? {
    name: hex.toUpperCase(),
    r: parseInt(hex.substr(0, 2), 16),
    g: parseInt(hex.substr(2, 2), 16),
    b: parseInt(hex.substr(4, 2), 16)
  } : null;
}

createSwatchGroupFromCSV();