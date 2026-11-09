//from https://colorslurp.com/blog/a-complete-guide-to-clr-files-on-mac

import Cocoa

// Create a color list
let filePath = "./your-file.clr"
let list = NSColorList(name: "My Palette")
        
// Add colors to the color list
colorList.setColor(NSColor.red, forKey: "Red")
colorList.setColor(NSColor.green, forKey: "Green")
colorList.setColor(NSColor.blue, forKey: "Blue")

try? list.write(to: filePath)

// Read a color list 
if let colorList = NSColorList.init(name: "My Palette", fromFile: filePath) {
    for key in colorList.allKeys {
        if let color = colorList.color(withKey: key) {
            print(key, color)
        }
    }
}