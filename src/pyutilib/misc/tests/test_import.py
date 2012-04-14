#
# Unit Tests for util/misc/import_file
#
#

import os
import sys
from os.path import abspath, dirname
sys.path.insert(0, dirname(dirname(abspath(__file__)))+os.sep+".."+os.sep+"..")
pkgdir = dirname(abspath(__file__))+os.sep+".."+os.sep+".."
currdir = dirname(abspath(__file__))+os.sep

from nose.tools import nottest
import pyutilib.misc
import pyutilib.th as unittest

try:
    import runpy
    _runpy=True
except:
    _runpy=False

class Test(unittest.TestCase):

    def test_import_file(self):
        pyutilib.misc.import_file(currdir+"import1.py")
        if "import1" in globals():
            self.fail("test_import_file - globals() should not be affected by import")
        import1 = pyutilib.misc.import_file(currdir+"import1.py")
        try:
            c = import1.a
        except:
            self.fail("test_import_file - could not access data in import.py")
        pyutilib.misc.import_file(currdir+"import1.py", context=globals())
        if not "import1" in globals():
            self.fail("test_import_file - failed to import the import1.py file")

    def test_run_file1(self):
        pyutilib.misc.run_file(currdir+"import1.py", logfile=currdir+"import1.log")
        if not os.path.exists(currdir+"import1.log"):
            self.fail("test_run_file - failed to create logfile")
        self.assertFileEqualsBaseline(currdir+"import1.log",currdir+"import1.txt")

    def test_run_file2(self):
        pyutilib.misc.run_file("import1.py", logfile=currdir+"import1.log", execdir=currdir)
        if not os.path.exists(currdir+"import1.log"):
            self.fail("test_run_file - failed to create logfile")
        self.assertFileEqualsBaseline(currdir+"import1.log",currdir+"import1.txt")

    def test_run_file3(self):
        try:
            pyutilib.misc.run_file("import2.py", logfile=currdir+"import2.log", execdir=currdir)
            self.fail("test_run_file - expected type error in import2.py")
        except TypeError:
            pass
        self.assertFileEqualsBaseline(currdir+"import2.log",currdir+"import2.txt")

# Apply decorator explicitly
Test = unittest.skipIf(not _runpy, "Cannot import 'runpy'")(Test)

if __name__ == "__main__":
    unittest.main()
