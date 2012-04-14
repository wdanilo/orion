#
# Unit Tests for xml_utils
#
#

import os
import sys
from os.path import abspath, dirname
sys.path.insert(0, dirname(dirname(abspath(__file__)))+"/../..")
pkgdir = dirname(abspath(__file__))

import unittest
from nose.tools import nottest
import pyutilib.misc
from xml.dom import minidom, Node

class XMLDebug(unittest.TestCase):

    def setUp(self):
        self.doc = minidom.parse(pkgdir+"/test.xml")
        self.node = self.doc.documentElement

    def tearDown(self):
        self.doc = None
        self.node=None

    def test_get_text(self):
        """Verify that we can get XML text"""
        str = pyutilib.misc.get_xml_text(self.node)
        target="a b c\n  \n  d e f"
        self.assertEqual(target,str)

    def test_escape(self):
        source="&'<>\""
        str = pyutilib.misc.escape(source)
        target = "&amp;'&lt;&gt;\""
        self.assertEqual(target,str)

if __name__ == "__main__":
    unittest.main()
