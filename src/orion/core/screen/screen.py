from orion import hook
from orion import utils



class Colormap:
    def __init__(self, conn, cid):
        self.conn, self.cid = conn, cid

    def alloc_color(self, color):
        """
            Flexible color allocation.
        """
        if color.startswith("#"):
            if len(color) != 7:
                raise ValueError("Invalid color: %s"%color)
            def x8to16(i):
                return 0xffff * (i&0xff)/0xff
            r = x8to16(int(color[1] + color[2], 16))
            g = x8to16(int(color[3] + color[4], 16))
            b = x8to16(int(color[5] + color[6], 16))
            return self.conn.conn.core.AllocColor(self.cid, r, g, b).reply()
        else:
            return self.conn.conn.core.AllocNamedColor(self.cid, len(color), color).reply()
        
class ScreenRect(object):

    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def __repr__(self):
        return '<%s %d,%d %d,%d>' % (self.__class__.__name__,
            self.x, self.y, self.width, self.height)

    def hsplit(self, columnwidth):
        assert columnwidth > 0
        assert columnwidth < self.width
        return (self.__class__(self.x, self.y, columnwidth, self.height),
                self.__class__(self.x+columnwidth, self.y,
                               self.width - columnwidth, self.height))

    def vsplit(self, rowheight):
        assert rowheight > 0
        assert rowheight < self.height
        return (self.__class__(self.x, self.y, self.width, rowheight),
                self.__class__(self.x, self.y + rowheight,
                               self.width, self.height - rowheight))
        
class Screen(object):
    """
        A physical screen, and its associated paraphernalia.
    """
    group = None
    def __init__(self, x=None, y=None, width=None, height=None):
        """
            - top, bottom, left, right: Instances of bar objects, or None.

            Note that bar.Bar objects can only be placed at the top or the
            bottom of the screen (bar.Gap objects can be placed anywhere).

            x,y,width and height aren't specified usually unless you are
            using 'fake screens'.
        """
#        self.top, self.bottom = top, bottom
#        self.left, self.right = left, right
        self.top, self.bottom = None, None
        self.left, self.right = None, None
        self.qtile = None
        self.index = None
        self.x = x # x position of upper left corner can be > 0 if one screen is "right" of the other
        self.y = y
        self.width = width
        self.height = height


    def _configure(self, qtile, index, x, y, width, height, group):
        self.qtile = qtile
        self.index, self.x, self.y = index, x, y,
        self.width, self.height = width, height
        self.setGroup(group)
        for i in self.gaps:
            i._configure(qtile, self)

    @property
    def gaps(self):
        lst = []
        for i in [self.top, self.bottom, self.left, self.right]:
            if i:
                lst.append(i)
        return lst

    @property
    def dx(self):
        return self.x + self.left.size if self.left else self.x

    @property
    def dy(self):
        return self.y + self.top.size if self.top else self.y

    @property
    def dwidth(self):
        val = self.width
        if self.left:
            val -= self.left.size
        if self.right:
            val -= self.right.size
        return val

    @property
    def dheight(self):
        val = self.height
        if self.top:
            val -= self.top.size
        if self.bottom:
            val -= self.bottom.size
        return val

    def get_rect(self):
        return ScreenRect(self.dx, self.dy, self.dwidth, self.dheight)

    def setGroup(self, new_group):
        """
        Put group on this screen
        """
        if new_group.screen == self:
            return
        elif new_group.screen:
            # g1 <-> s1 (self)
            # g2 (new_group)<-> s2 to
            # g1 <-> s2
            # g2 <-> s1
            g1 = self.group
            s1 = self
            g2 = new_group
            s2 = new_group.screen

            s2.group = g1
            g1._setScreen(s2)
            s1.group = g2
            g2._setScreen(s1)
        else:
            if self.group is not None:
                self.group._setScreen(None)
            self.group = new_group
            new_group._setScreen(self)
        hook.fire("setgroup")
        hook.fire("focus_change")
        hook.fire("layout_change", self.group.layouts[self.group.currentLayout])

    def _items(self, name):
        if name == "layout":
            return True, range(len(self.group.layouts))
        elif name == "window":
            return True, [i.window.wid for i in self.group.windows]
        elif name == "bar":
            return False, [x.position for x in self.gaps]

    def _select(self, name, sel):
        if name == "layout":
            if sel is None:
                return self.group.layout
            else:
                return utils.lget(self.group.layouts, sel)
        elif name == "window":
            if sel is None:
                return self.group.currentWindow
            else:
                for i in self.group.windows:
                    if i.window.wid == sel:
                        return i
        elif name == "bar":
            return getattr(self, sel)

    def resize(self, x=None, y=None, w=None, h=None):
        x = x or self.x
        y = y or self.y
        w = w or self.width
        h = h or self.height
        self._configure(self.qtile, self.index, x, y, w, h, self.group)
        for bar in [self.top, self.bottom, self.left, self.right]:
            if bar:
                bar.draw()
        self.group.layoutAll()

    def cmd_info(self):
        """
            Returns a dictionary of info for this screen.
        """
        return dict(
            index=self.index,
            width=self.width,
            height=self.height,
            x = self.x,
            y = self.y
        )

    def cmd_resize(self, x=None, y=None, w=None, h=None):
        """
            Resize the screen.
        """
        self.resize(x, y, w, h)