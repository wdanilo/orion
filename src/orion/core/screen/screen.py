class Screen(object):
    """ A physical screen, and its associated paraphernalia. """
    group = None
    def __init__(self, x=None, y=None, width=None, height=None):
        self.index = None
        self.x = x # x position of upper left corner can be > 0
                   # if one screen is "right" of the other
        self.y = y
        self.width = width
        self.height = height


    def _configure(self, qtile, index, x, y, width, height):
        self.qtile = qtile
        self.index, self.x, self.y = index, x, y,
        self.width, self.height = width, height
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
        """ Put group on this screen """
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
        #hook.fire("setgroup")
        #hook.fire("focus_change")

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
        """ Returns a dictionary of info for this screen. """
        return dict(
            index=self.index,
            width=self.width,
            height=self.height,
            x = self.x,
            y = self.y
        )

    def cmd_resize(self, x=None, y=None, w=None, h=None):
        """ Resize the screen. """
        self.resize(x, y, w, h)