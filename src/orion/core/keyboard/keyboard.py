import xkeysyms

modMapOrder = ["shift", "lock", "control", "mod1", "mod2", "mod3", "mod4", "mod5"]

ModMasks = {
    "shift": 1<<0,
    "lock":  1<<1,
    "control": 1<<2,
    "mod1": 1<<3,
    "mod2": 1<<4,
    "mod3": 1<<5,
    "mod4": 1<<6,
    "mod5": 1<<7,
}
keysyms = xkeysyms.keysyms