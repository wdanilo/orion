from orion.wm.nebula.manager import Group
from orion.wm.screen import Screen
from orion import layout

keys = []

groups = [
    Group("a"),
]

layouts = [
    #layout.Max(),
    layout.Stack(stacks=2)
]

screens = [
    Screen(),
]

main = None
follow_mouse_focus = True
cursor_warp = False
floating_layout = layout.Floating()
mouse = ()

