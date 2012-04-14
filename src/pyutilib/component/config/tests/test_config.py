#
# Unit Tests for pyutilib.options.configuration
#
#

import os
import sys
from os.path import abspath, dirname
sys.path.insert(0, dirname(dirname(abspath(__file__)))+os.sep+".."+os.sep+"..")
currdir = dirname(abspath(__file__))+os.sep

from nose.tools import nottest
from pyutilib.component.core import ExtensionPoint
from pyutilib.component.config import *
import pyutilib.th as unittest
import pyutilib.misc


class Test(unittest.TestCase):

    class TMP(Plugin):
        def __init__(self):
            declare_option("a")
            declare_option("b", local_name="bb")
            declare_option("b")
            declare_option("c")
            declare_option("zz",section='a.b')
            declare_option("yy",default="foo")

    def setUp(self):
        PluginGlobals.clear()
        PluginGlobals.push_env(PluginEnvironment())
        pyutilib.component.config.plugin_ConfigParser.Configuration_ConfigParser(name="Configuration_ConfigParser")
        self.tmp=Test.TMP()

    def tearDown(self):
        del self.tmp
        PluginGlobals.clear()

    def test_init(self):
        """Test Configuration construction"""
        config = Configuration()

    def test_contains(self):
        """Test contains method"""
        config = Configuration()
        self.assertFalse("globals" in config)
        config.load(currdir+"config1.ini")
        self.assertTrue("globals" in config)

    def test_getitem(self):
        """Test getitem method"""
        config = Configuration()
        try:
            config["globals"]
            self.fail("expected error")
        except ConfigurationError:
            pass
        config.load(currdir+"config1.ini")
        keys = config["globals"].keys()
        keys.sort()
        self.assertTrue(keys == ["a","b","c"])

    def test_sections(self):
        """Test getitem method"""
        config = Configuration()
        config.load(currdir+"config1.ini")
        keys = config.sections()
        keys.sort()

    def test_load1(self):
        """Test load method"""
        config = Configuration()
        try:
            config.load(None)
            self.fail("expected error")
        except ConfigurationError:
            pass

    def test_load2(self):
        """Test load method"""
        config = Configuration()
        try:
            config.load("__missing__")
            self.fail("expected error")
        except ConfigurationError:
            pass

    def test_load3(self):
        """Test load method"""
        config = Configuration()
        try:
            config.load(currdir+"config2.ini")
            config.pprint()
            self.fail("expected error")
        except ConfigurationError:
            pass

    def test_load4(self):
        """Test load method"""
        config = Configuration()
        try:
            config.load(currdir+"config3.ini")
            self.fail("expected error")
        except ConfigurationError:
            pass

    @unittest.skipIf(sys.version_info[:2] < (2,6), "Skipping tests because configuration output is not guaranteed to be sorted")
    def test_load5(self):
        """Test load method"""
        PluginGlobals.push_env(PluginEnvironment())
        class TMP2(object):
            def __init__(self):
                declare_option("a")
                declare_option("b", cls=FileOption)
                declare_option("c")
                declare_option("xx",cls=DictOption,section_re='globals.*')

        config = Configuration()
        tmp2=TMP2()
        config.load(currdir+"config4.ini")
        #config.pprint()
        if sys.platform == "win32":
            #
            # A hack, to ensure cross-platform portability of this test
            #
            e = ExtensionPoint(IFileOption)
            for ep in e.extensions():
                ep.set_value("/dev/null", raw=True)
        #PluginGlobals.pprint()
        config.save(currdir+"config4.out")
        #print config
        self.assertFileEqualsBaseline(currdir+"config4.out",currdir+"config4.txt")
        pyutilib.misc.setup_redirect(currdir+"log2.out")
        config.pprint()
        pyutilib.misc.reset_redirect()
        self.assertFileEqualsBaseline(currdir+"log2.out", currdir+"log2.txt")
        PluginGlobals.pop_env()

    @unittest.skipIf(sys.version_info[:2] < (2,6), "Skipping tests because configuration output is not guaranteed to be sorted")
    def test_save1(self):
        """Test save method"""
        config = Configuration()
        config.load(currdir+"config1.ini")
        if sys.platform == "win32":
            #
            # A hack, to ensure cross-platform portability of this test
            #
            e = ExtensionPoint(IFileOption)
            for ep in e.extensions():
                ep.set_value("/dev/null", raw=True)
        config.save(currdir+"config1.out")
        #PluginGlobals.pprint()
        self.assertFileEqualsBaseline(currdir+"config1.out",currdir+"config1.txt")

    def test_save2(self):
        """Test save method"""
        config = Configuration()
        try:
            config.save(None)
            self.fail("expected error")
        except ConfigurationError:
            pass

if __name__ == "__main__":
    unittest.main()
