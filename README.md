# Inkscape-Extensions
Some extensions for Inkscape

## BatchTask
### What does this do?
This extension applies an effect on multiple objects at once. You can pick them from the dropdown menu containing some common actions, or any of the builtin Inkscape actions or verbs. Run `inkscape --action-list` and `inkscape --verb-list` to show the available effects. Target objects can be selected via an XPath like selector.

## BaseExtension
### What does this do?
Not much by itself - it serves to make writing new extensions simpler. It handles the tempfiles used by the extension when applying effects. Calling an extension made using BaseExtension from another is also easier as there is a call method available.

## How to try these extensions out?
Git clone this repo into your inkscape user extensions folder. You can find this under Edit -> Preferences -> System -> User extensions

