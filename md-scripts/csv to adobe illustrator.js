// convert csv to adobe illustrator script from https://community.adobe.com/t5/illustrator-discussions/convert-csv-to-swatch-library/m-p/4377683
function main() {
     if (isOSX()) {
               var csvFile = File.openDialog('Select a CSV File', function (f) { return (f instanceof Folder) || f.name.match(/\.csv$/i);} );
               } else {
               var csvFile = File.openDialog('Select a CSV File','comma-separated-values(*.csv):*.csv;');
               }
          if (csvFile != null) {
               fileArray = readInCSV(csvFile);
                    var columns = fileArray[0].length;
                    //alert('CSV file has ' + columns + ' columns…');
                    var rows = fileArray.length;
                    //alert('CSV file has ' + rows + ' rows…');
                    if (columns == 4 && rows > 0) {
                         exchangeSwatches(csvFile);
                         } else {
                         var mess = 'Incorrect CSV File?';
                              isOSX ? saySomething(mess) : alert(mess);
                         }
               } else {
               var mess = 'Ooops!!!';
                    isOSX ? saySomething(mess) : alert(mess);
               }
               }
     main();
function exchangeSwatches(csvFile) {
//    var docRef = app.documents.add();
     var docRef = app.activeDocument;
          var swatchgroup = docRef.swatchGroups.add();
          swatchgroup.name = csvFile.name;
          with (docRef) {     
             /*  for (var i = swatches.length-1; i >= 0; i--) {
                       swatches.remove();
                         } */
                    for (var a = 0; a < fileArray.length; a++) {
                         var n = fileArray[0]; // First Column is name               
                              if (n == 'Cyan' || n == 'Magenta' || n == 'Yellow' || n == 'Black') {          
                                   n = n + '-???'; // Reserved swatch name;
                                   }          
                              r = parseFloat(fileArray[1]); // Second Column is Red
                              g = parseFloat(fileArray[2]); // Third Column is Green
                              b = parseFloat(fileArray[3]); // Forth Column is Bloo
                              if (r >= 0 && r <= 255 && g >= 0 && g <= 255 && b >= 0 && b <= 255) {
                                var color = new RGBColor;
                                  color.red = r;
                                  color.green = g;
                                  color.blue = b;
                                  var swatch = swatches.add();
                                  swatch.name = n;
                                  swatch.color = color;
                                  swatchgroup.addSwatch(swatch);
                                } else {
                                   var mess = 'Color values are out of range?';
                                        isOSX ? saySomething(mess) : alert(mess);
                                   }
                         }
               }
               }
     function readInCSV(fileObj) {
     var fileArray = new Array();
          fileObj.open('r');
          fileObj.seek(0, 0);
          while(!fileObj.eof) {
               var thisLine = fileObj.readln();
                    var csvArray = thisLine.split(',');
                    fileArray.push(csvArray);
               }
          fileObj.close();
          return fileArray;
          }
     function saySomething(stringObj) {
     var speakThis = 'I say, "' + stringObj + '"';
          alert(speakThis);
          }
     function isOSX() {
  return $.os.match(/Macintosh/i);
  }