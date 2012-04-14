
import os
import sys
from os.path import abspath, dirname
sys.path.insert(0, dirname(dirname(abspath(__file__)))+os.sep+".."+os.sep+"..")
currdir = dirname(abspath(__file__))+os.sep

import pyutilib.th as unittest

tmp = os.environ.get('PYUTILIB_UNITTEST_CATEGORIES','')
os.environ['PYUTILIB_UNITTEST_CATEGORIES'] = '_foo_,_bar_'

#@unittest.category('_foo_')
class Tester3(unittest.TestCase):

    @unittest.category('_bar_ ',' _rab_')
    def test_pass(self):
        print "Executing Tester3.test_pass"

    @unittest.category('_oof_' ,' _rab_')
    def test_fail(self):
        self.fail("test_fail will always fail")

Tester3 = unittest.category('foo')(Tester3)

os.environ['PYUTILIB_UNITTEST_CATEGORIES'] = tmp

if __name__ == "__main__":
    unittest.main()
