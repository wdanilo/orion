from orion.utils import flagEnum, enum

# ICCM Constants
# Bitmask returned by XParseGeometry().  Each bit tells if the corresponding
# value (x, y, width, height) was found in the parsed string.
NoValue = 0x0000
XValue = 0x0001
YValue = 0x0002
WidthValue = 0x0004
HeightValue = 0x0008
AllValues = 0x000F
XNegative = 0x0010
YNegative = 0x0020

ReleaseByFreeingColormap = 1
BitmapSuccess = 0
BitmapOpenFailed = 1
BitmapFileInvalid = 2
BitmapNoMemory = 3
XCSUCCESS = 0
XCNOMEM = 1
XCNOENT = 2

RectangleOut = 0
RectangleIn = 1
RectanglePart = 2

NormalHintsFlags = flagEnum (
        'USPosition',               # User-specified x, y
        'USSize',                   # User-specified width, height
        'PPosition',                # Program-specified position
        'PSize',                    # Program-specified size
        'PMinSize',                 # Program-specified minimum size
        'PMaxSize',                 # Program-specified maximum size
        'PResizeInc',               # Program-specified resize increments
        'PAspect',                  # Program-specified min and max aspect ratios
        'PBaseSize',                # Program-specified base size
        'PWinGravity',              # Program-specified window gravity
)

sizeHintsFlags = flagEnum(
        'USPosition',
        'USSize',
        'PPosition',
        'PSize',
        'PMinSize',
        'PMaxSize',
        'PResizeInc',
        'PAspect',
        'PBaseSize',
        'PWinGravity',
)
                      
PAllHints = (sizeHintsFlags.PPosition|sizeHintsFlags.PSize|sizeHintsFlags.PMinSize|sizeHintsFlags.PMaxSize|sizeHintsFlags.PResizeInc|sizeHintsFlags.PAspect)

wmHintsFlags = flagEnum(
        'InputHint',
        'StateHint',
        'IconPixmapHint',
        'IconWindowHint',
        'IconPositionHint',
        'IconMaskHint',
        'WindowGroupHint',
        'MessageHint',
        'UrgencyHint',
)

AllHints = (wmHintsFlags.InputHint|wmHintsFlags.StateHint|wmHintsFlags.IconPixmapHint|wmHintsFlags.IconWindowHint|
            wmHintsFlags.IconPositionHint|wmHintsFlags.IconMaskHint|wmHintsFlags.WindowGroupHint|wmHintsFlags.MessageHint|
            wmHintsFlags.UrgencyHint)

# DontCareState = 0
wmState = enum(
        'WITHDRAWN',
        'NORMAL',
        'ZOOM',
        'ICONIC',
        'INACTIVE',
)


visualMask = enum(
        VisualNoMask = 0x0,
        VisualIDMask = 0x1,
        VisualScreenMask = 0x2,
        VisualDepthMask = 0x4,
        VisualClassMask = 0x8,
        VisualRedMaskMask = 0x10,
        VisualGreenMaskMask = 0x20,
        VisualBlueMaskMask = 0x40,
        VisualColormapSizeMask = 0x80,
        VisualBitsPerRGBMask = 0x100,
        VisualAllMask = 0x1FF,
)