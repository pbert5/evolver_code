context window / main window on the right should be 0 so user can focus to scroll
    and depending on seleciton it shouwld show relevent information, like what goes here, breakdown of contents of things its focused on like specific experiments, evolver units, services
    if the context of one thing is dependent on another, it can start with a refference to the super unit, like if we are entered into  a protocol, and focused on the steps window or on a specific step like it would have a short snipped about that protocol at thge top then, since whatever is happening there is specific to the selected protocol, then under the protocol snippet we would have the step context or the component context
we need more context aware keybindings ( assuming that sugestions are the extent) 
+ way to enable demo mode to add test evolvers and test devices, test inventory

inventory context: describe that here we specify materials and devices that you have availible to your current evolver setup - when focused on inventory window
    auto discover with kybind
    
for any context where the user can edit a list: i.e. live.evolverunits, live.experiments, inventory.protocols/materials/devices
    add x( based on current tab)  with keybind ( like its best if we are specifiyng what they are added so they dont get confused)
    key to delete entry
    key to edit entry
    all of these sugested in the bottom bar,

l

we should figure out interactive popups, things that come up whenever we need input, basicaly forms, need to be able to cleanly let the user fill multiple text entry/multi select/or check box fields, swap between them while keeping progress and then submit them 
    thigns like add would open a new one, while edit would bring open one with the current options preset, options will oftend be dependent on information set in other parts of the ui

? key for fuzy search of availible keybinds, in all scopes

realy we should try to suggest anything relevant in the bottom bar
like in all context where we are viewing the windows, we should show <1-5> select window , and things like that in contexts when we cant select windows like popups when they reuse num keybinds

all of this should be described in json
realisticaly everythign in json:
    tui archetecture, including keybinds, tabs, windows, submenus, 
    user data, like there inventory, protocols, and evolver usnits and everything

for other general interaction, by defualt we are not are not focused on any entry in a list if we havent focused on it yet, like dont start at one or select the first protocol, (we would prompt arrow up down to sellect when in a list) ( maybe arrow left right to cycle through windows in numerical order, but will likely want to rebind that to something more usefull) its only when you click or arrow down to the first or up to the last that we have it in focus and maintain it till the window tab is swapped
    unless it is chosen/selected, either enter for things that will open their own popup, space or enter for selectable entires that will be set as active( only space would be presented) plus can double click to select,the ones set active   will be in focus and retain focus when you go back to their tab if you move the focus off of them with the updown arroows, they will keep that grayed out highlight while the thign that is in focus gets that main hightlight, but on returning to that window the focus will start backup on them ( i gues these will be active entries)

tho for we do need to expand our definition of active to handle selection in components
    active will be associated with one of several things
        1. set context ( to like a specific protocol or step) multiple contexts can be valid at once, i.e nested
        2. togle a flag or value saying that it is enabled liek a component 
        3. expose a form
    so we activate an entry that can be active and dependignb on what its activating soemthing will happen
        either it changes the context, in which case it will be the default selection in the window, while that context is active
        or it togles an option which wont be a default selection but it will have that passive highlight
        or it opens a popup in which case after the popup is closed it will no longer retain any persistant focus
    activation is a concept specific to the ui, not to the actual evovler


---------



need templates and examples
    obv for protocols with populated components and steps
    need test evolver units that we can spin up, i gues when you go to add in that tab if you are admin the pop up will give you the option to scan, select a detected and import config or configure it, or import a demo evolver, that way we can have the options of like devices associated with it, and be able to test assignign those devices to required components in the protocol


+ also for exit behavior
ctrl c should exit first any popups, ( only one popup at a time for now should be posible) then if there are no popups a ctrl c would exit the tui tool
q can still exit
esc should remove any focus if there is a focus in a window ( unless something is activated, then it would deactivate it)


---- 
enter when focused on a inactive service should start it and space should open any config popup it has 
+ the highlight should  be a li ttle less intence and the symbols a little thicker, its hard to see a symbol or its cahnge when it is currently highlighted



 context window does also follow the open tab, but key sugestions dont, they should, and context specific keybinds should also,  so i gues in addition to active contexts from selections, we also have the context of whats selelcted rn in tewrms of window, tab, and line, which will specify the availible keybids and actions
by json iment like in the src the menus and everythign are configured as json
---- 
if we are on in the context window, then techinaly a window.tab or window.tab.list entry should be in focus in that case esc or left arrrow should bring us out of focusing on context
the config option also isnt always availible, same with deleet ore restart for unmanaged services

plus ctrl d should should escape the tui no matter what to prevent soft locks
