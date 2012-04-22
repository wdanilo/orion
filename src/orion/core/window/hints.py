import iccm
from orion import utils

class Hints(object):
    def update(self, dict):
        for key, val in dict.items():
            if not hasattr(self, key):
                raise Exception ("Undefined hint '%s'"%key)
            setattr(self, key, val)
    
    def __str__(self):
        return str(self.__dict__)

class WindowHints(Hints):
    flags = utils.flagEnum(
        'InputHint',        # input
        'StateHint',        # initial_state
        'IconPixmapHint',   # icon_pixmap
        'IconWindowHint',   # icon_window
        'IconPositionHint', # icon_x & icon_y
        'IconMaskHint',     # icon_mask
        'WindowGroupHint',  # window_group
        'MessageHint',      # (this bit is obsolete)
        'UrgencyHint',      # urgency
    )
    def __init__(self):
        self.flags          = None
        self.input          = True
        self.initial_state  = iccm.NormalState
        self.icon_pixmap    = None
        self.icon_window    = None
        self.icon_x         = None
        self.icon_y         = None
        self.icon_mask      = None
        self.window_group   = None
        
class WindowNormalHints(Hints):
    flags = utils.flagEnum(
        'USPosition',       # User-specified x, y
        'USSize',           # User-specified width, height
        'PPosition',        # Program-specified position
        'PSize',            # Program-specified size
        'PMinSize',         # Program-specified minimum size
        'PMaxSize',         # Program-specified maximum size
        'PResizeInc',       # Program-specified resize increments
        'PAspect',          # Program-specified min and max aspect ratios
        'PBaseSize',        # Program-specified base size
        'PWinGravity'       # Program-specified window gravity
    )
    def __init__(self):
        self.flags          = None
        self.max_width      = None
        self.max_height     = None
        self.width_inc      = None
        self.height_inc     = None
        self.min_aspect     = 1
        self.max_aspect     = 1
        self.min_width      = 0
        self.min_height     = 0
        self.base_width     = 0
        self.base_height    = 0
        self.win_gravity    = 'NorthWest'