class Defaults:
    def __init__(self, *defaults):
        """
            defaults: A list of (name, value, description) tuples.
        """
        self.defaults = defaults

    def load(self, target, config):
        """
            Loads a dict of attributes, using specified defaults, onto target.
        """
        for i in self.defaults:
            val = config.get(i[0], i[1])
            setattr(target, i[0], val)