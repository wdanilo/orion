from orion.manager import Key, Screen, Group
from orion.command import lazy
from orion import layout, bar, widget

keys = []

groups = [
    Group("a"),
]

layouts = [
    layout.Max(),
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

