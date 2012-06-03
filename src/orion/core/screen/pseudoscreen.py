class PseudoScreen:
    """
        This may be a Xinerama screen or a RandR CRTC, both of which are
        rectagular sections of an actual Screen.
    """
    def __init__(self, x, y, width, height):
        self.x, self.y, self.width, self.height = x, y, width, height