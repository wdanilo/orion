from orion.utils import flagEnum, enum

# These should be in xpyb:
ModMasks = flagEnum (
    'shift',
    'lock',
    'control',
    'mod1',
    'mod2',
    'mod3',
    'mod4',
    'mod5',               
)

ButtonCodes = enum (
    'Button1',
    'Button2',
    'Button3',
    'Button4',
    'Button5',             
)

               
AllButtonsMask = 0b11111 << 8
ButtonMotionMask = 1 << 13
ButtonReleaseMask = 1 << 3


HintsFlags = flagEnum (
    'InputHint',                # input
    'StateHint',                # initial_state
    'IconPixmapHint',           # icon_pixmap
    'IconWindowHint',           # icon_window
    'IconPositionHint',         # icon_x & icon_y
    'IconMaskHint',             # icon_mask
    'WindowGroupHint',          # window_group
    'MessageHint',              # (this bit is obsolete)
    'UrgencyHint',              # urgency
)


WindowTypes = {
    '_NET_WM_WINDOW_TYPE_DESKTOP'       : "desktop",
    '_NET_WM_WINDOW_TYPE_DOCK'          : "dock",
    '_NET_WM_WINDOW_TYPE_TOOLBAR'       : "toolbar",
    '_NET_WM_WINDOW_TYPE_MENU'          : "menu",
    '_NET_WM_WINDOW_TYPE_UTILITY'       : "utility",
    '_NET_WM_WINDOW_TYPE_SPLASH'        : "splash",
    '_NET_WM_WINDOW_TYPE_DIALOG'        : "dialog",
    '_NET_WM_WINDOW_TYPE_DROPDOWN_MENU' : "dropdown",
    '_NET_WM_WINDOW_TYPE_POPUP_MENU'    : "menu",
    '_NET_WM_WINDOW_TYPE_TOOLTIP'       : "tooltip",
    '_NET_WM_WINDOW_TYPE_NOTIFICATION'  : "notification",
    '_NET_WM_WINDOW_TYPE_COMBO'         : "combo",
    '_NET_WM_WINDOW_TYPE_DND'           : "dnd",
    '_NET_WM_WINDOW_TYPE_NORMAL'        : "normal",
}

WindowStates = {
    None: 'normal',
    '_NET_WM_STATE_FULLSCREEN': 'fullscreen',
    }

# Maps property names to types and formats.
PropertyMap = {
    # ewmh properties
    "_NET_DESKTOP_GEOMETRY"     : ("CARDINAL",      32),
    "_NET_SUPPORTED"            : ("ATOM",          32),
    "_NET_SUPPORTING_WM_CHECK"  : ("WINDOW",        32),
    "_NET_WM_NAME"              : ("UTF8_STRING",   8),
    "_NET_WM_PID"               : ("CARDINAL",      32),
    "_NET_CLIENT_LIST"          : ("WINDOW",        32),
    "_NET_CLIENT_LIST_STACKING" : ("WINDOW",        32),
    "_NET_NUMBER_OF_DESKTOPS"   : ("CARDINAL",      32),
    "_NET_CURRENT_DESKTOP"      : ("CARDINAL",      32),
    "_NET_DESKTOP_NAMES"        : ("UTF8_STRING",   8),
    "_NET_WORKAREA"             : ("CARDINAL",      32),
    "_NET_ACTIVE_WINDOW"        : ("WINDOW",        32),
    "_NET_WM_STATE"             : ("ATOM",          32),
    "_NET_WM_DESKTOP"           : ("CARDINAL",      32),
    "_NET_WM_STRUT_PARTIAL"     : ("CARDINAL",      32),
    "_NET_WM_WINDOW_OPACITY"    : ("CARDINAL",      32),
    "_NET_WM_WINDOW_TYPE"       : ("CARDINAL",      32),
    # ICCCM
    "WM_STATE"                  : ("WM_STATE",      32),
    # Qtile-specific properties
    "QTILE_INTERNAL"            : ("CARDINAL",      32)
}