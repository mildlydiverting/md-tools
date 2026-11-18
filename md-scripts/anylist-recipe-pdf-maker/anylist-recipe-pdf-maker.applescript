
tell application "Safari"
	activate
end tell

# The recipe list "overflows" to the top, so keep track of the first recipe we've seen so we can use that to know once we've gone through them all
set firstRecipeName to getCurrentRecipeName()
set currentRecipeName to firstRecipeName
repeat
	printPage(currentRecipeName)
	set previousRecipeName to currentRecipeName
	delay 1
	selectNextRecipe()
	delay 1
	set currentRecipeName to getCurrentRecipeName()
	if currentRecipeName is equal to firstRecipeName then
		exit repeat
	end if
end repeat



on getCurrentRecipeName()
	tell application "Safari"
		tell window 1
			tell tab 1
				set recipeName to do JavaScript "document.getElementsByClassName(\"recipe-detail-recipe-name\")[0].innerHTML"
			end tell
		end tell
	end tell
	return recipeName
end getCurrentRecipeName

on selectNextRecipe()
	tell application "System Events"
		tell process "Safari"
			key code 125 using command down # cmd + down arrow is hotkey to select next recipe
		end tell
	end tell
end selectNextRecipe

on printPage(recipeName)
	tell application "System Events"
		tell process "Safari"
			# keystroke "2" using control down # hotkey to go to recipes page
			# Get the recipeName from the page
			keystroke "p" using command down
			tell front window
				repeat until exists sheet 1
					delay 0.02
				end repeat
				tell sheet 1 # print dialog
					tell splitter group 1
						tell group 2
							click button 1
						end tell
					end tell
					repeat until exists sheet 1
						delay 0.02
					end repeat
					tell sheet 1 # save as dialog
						tell splitter group 1
							set value of text field "Save As:" to recipeName & ".pdf"
							click button "Save"
						end tell
					end tell
				end tell
			end tell
		end tell
	end tell
end printPage
