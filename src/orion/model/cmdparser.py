import argparse
import orion

class CmdParser(object):
    def __init__(self):
        self.args = None
        self.parser = argparse.ArgumentParser(
                                prog = 'orion',
                                fromfile_prefix_chars='@',
                                description='Orion Window Manager')
        self.parser.add_argument('--version',       action='version', version='%(prog)s '+str(orion.version), help="show program's version")
        self.parser.add_argument('-v', '--verbose', action='store_true', help="enables verbose mode")
        self.parser.add_argument('-c', '--no-color', action='store_true', help="disables colored terminal output")
        self.parser.add_argument('-i', '--use-ident', action='store_true', help="displays idented terminal output")
        self.parser.add_argument('-s', '--silent', action='store_true', help="output only errors")
        self.args = self.parser.parse_known_args()[0]
    
    def parse(self):
        self.args = self.parser.parse_args()
