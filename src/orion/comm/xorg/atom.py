from orion.wm.window import proto
import xcb

class AtomCache:
    def __init__(self, conn):
        self.conn = conn
        self.atoms = {}
        self.reverse = {}

        # We can change the pre-loads not to wait for a return
        for name in proto.WindowTypes.keys():
            self.insert(name=name)

        for i in dir(xcb.xproto.Atom):
            if not i.startswith("_"):
                self.insert(name=i, atom=getattr(xcb.xproto.Atom, i))

    def insert(self, name = None, atom = None):
        assert name or atom
        if atom is None:
            c = self.conn.conn.core.InternAtom(False, len(name), name)
            atom = c.reply().atom
        if name is None:
            c = self.conn.conn.core.GetAtomName(atom)
            name = str(c.reply().name.buf())
        self.atoms[name] = atom
        self.reverse[atom] = name

    def get_name(self, atom):
        if atom not in self.reverse:
            self.insert(atom=atom)
        return self.reverse[atom]

    def __getitem__(self, key):
        if key not in self.atoms:
            self.insert(name=key)
        return self.atoms[key]