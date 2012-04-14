#
# Unit Tests for util/data
#
#

import os
import sys
from os.path import abspath, dirname
sys.path.insert(0, dirname(dirname(abspath(__file__)))+os.sep+".."+os.sep+"..")
pkgdir = dirname(abspath(__file__))

import pyutilib.th as unittest
from nose.tools import nottest
import pyutilib.excel

try:
    from win32com.client.dynamic import Dispatch
    _win32com=True
except:
    _win32com=False #pragma:nocover


class Test(unittest.TestCase):

    def test_spreadsheet1(self):
        """ Create a spreadsheet with a constructor """
        sheet = pyutilib.excel.ExcelSpreadsheet(pkgdir+"\\test_data.xls")
        tmp = sheet.get_range("Arange")

        self.assertEqual(tmp,('A1','A2','A3'))
        del sheet

    def test_spreadsheet2(self):
        """ Create and open spreadsheet """
        sheet = pyutilib.excel.ExcelSpreadsheet()
        sheet.open(pkgdir+"\\test_data.xls")
        tmp = sheet.get_range("Arange")
        self.assertEqual(tmp,('A1','A2','A3'))
        tmp = sheet.get_range_nrows("Arange")
        self.assertEqual(tmp,3)
        tmp = sheet.get_range_ncolumns("Arange")
        self.assertEqual(tmp,1)

    def test_spreadsheet3(self):
        """ Create and open spreadsheet in the test dir"""
        os.chdir(pkgdir)
        sheet = pyutilib.excel.ExcelSpreadsheet()
        sheet.open("test_data.xls")
        tmp = sheet.get_range("Arange")
        self.assertEqual(tmp,('A1','A2','A3'))
        try:
            tmp = sheet.get_range("Brange")
            self.fail("test_spreadsheet3 - should not have opened range")
        except IOError:
            pass

    def test_spreadsheet4(self):
        """ Create and delete spreadsheet without opening it """
        sheet = pyutilib.excel.ExcelSpreadsheet()
        sheet.close()

    def test_spreadsheet5(self):
        """ Create and open spreadsheet """
        s1 = pyutilib.excel.ExcelSpreadsheet()
        s1.open(pkgdir+"\\test_data.xls")
        tmp = s1.get_range("Arange")
        self.assertEqual(tmp,('A1','A2','A3'))
        #s2 = pyutilib.excel.ExcelSpreadsheet()
        #s2.open(pkgdir+"\\test_data.xls")

    def test_spreadsheet6(self):
        """ Create and open spreadsheet """
        sheet = pyutilib.excel.ExcelSpreadsheet()
        sheet.open(pkgdir+"\\test_data.xls")
        val = (('B1',),('B2',),('B3',))
        sheet.set_range("Arange",val)
        tmp = sheet.get_range("Arange")
        self.assertEqual(tmp,('B1','B2','B3'))

    def test_spreadsheet7(self):
        """ Create and open spreadsheet """
        sheet = pyutilib.excel.ExcelSpreadsheet()
        sheet.open(pkgdir+"\\test_data.xls")
        val = [['B1'],['B2'],['B3']]
        sheet.set_range("Arange",val)
        tmp = sheet.get_range("Arange")
        self.assertEqual(tmp,('B1','B2','B3'))
        val = [['B1'],['B2'],['B3'],['B4']]
        try:
            sheet.set_range("Arange",val)
            self.fail("expected error")
        except IOError:
            pass

    def test_spreadsheet8(self):
        """ Create and open spreadsheet """
        sheet = pyutilib.excel.ExcelSpreadsheet()
        sheet.open(pkgdir+"\\test_data.xls")
        val = [['B1','C1'],['B2','C1'],['B3','C1']]
        sheet.set_array(3,4,val)
        val = sheet.get_array(4,4,5,5)
        self.assertEqual(val,((u'B2', u'C1'), (u'B3', u'C1')))

    def test_spreadsheet9(self):
        """ Create and open spreadsheet """
        sheet = pyutilib.excel.ExcelSpreadsheet()
        sheet.open(pkgdir+"\\test_data.xls")
        val = (('B1','C1'),('B2','C1'),('B3','C1'))
        sheet.set_array(3,4,val)
        val = sheet.get_array(4,4,5,5)
        self.assertEqual(val,((u'B2', u'C1'), (u'B3', u'C1')))

    def test_spreadsheet10(self):
        """ Verify that we can get updated function values """
        sheet = pyutilib.excel.ExcelSpreadsheet()
        sheet.open(pkgdir+"\\test_data.xls")
        sheet.set_range("x", 2.0)
        val = sheet.get_range("x")
        self.assertEqual(val,2.0)
        val = sheet.get_range("xSquared")
        self.assertEqual(val,16.0)
        sheet.calculate()
        val = sheet.get_range("xSquared")
        self.assertEqual(val,4.0)
        sheet.set_range("x", 4.0)
        sheet.close()

    def test_spreadsheet10(self):
        """ Verify that we can activate a spreadsheet """
        sheet = pyutilib.excel.ExcelSpreadsheet()
        sheet.open(pkgdir+"\\test_data.xls")
        sheet.activate("Sheet2")
        val = sheet.get_range("sInfo")
        self.assertEqual(val,("s1","s2","s3"))
        val = sheet.get_range("A2:A2")
        self.assertEqual(val,"s1")
        sheet.close()

    def test_calc_iterations(self):
        """ Verify that iterations can be set """
        sheet = pyutilib.excel.ExcelSpreadsheet()
        sheet.open(pkgdir+"\\test_data.xls")
        tmp = sheet.calc_iterations()
        sheet.calc_iterations(not tmp)
        ttmp = sheet.calc_iterations()
        if tmp is ttmp:
            self.fail("Tried to set calc_iterations to a different value")
        try:
            sheet.calc_iterations(1)
            self.fail("Expected error setting an integer for calc_iterations")
        except ValueError:
            pass
        sheet.close()

    def test_max_iterations(self):
        """ Verify that max iterations can be set """
        sheet = pyutilib.excel.ExcelSpreadsheet()
        sheet.open(pkgdir+"\\test_data.xls")
        tmp = sheet.max_iterations()
        sheet.max_iterations(max(tmp+1,0))
        ttmp = sheet.calc_iterations()
        if tmp is ttmp:
            self.fail("Tried to set max_iterations to a different value")
        try:
            sheet.max_iterations(-1)
            self.fail("Expected error setting a negative integer for max_iterations")
        except ValueError:
            pass
        sheet.close()

    def test_get_column(self):
        """ Verify that we can get a column"""
        sheet = pyutilib.excel.ExcelSpreadsheet()
        sheet.open(pkgdir+"\\test_data.xls")
        val = sheet.get_column("E")
        self.assertEqual(val,(1.0,2.0,None,4.0,5.0))
        val = sheet.get_column("F",contiguous=True)
        self.assertEqual(val,(1.0,2.0,3.0))
        val = sheet.get_column("G")
        self.assertEqual(val,(1.0,2.0,3.0,4.0,None,6.0))
        val = sheet.get_column("G",contiguous=True)
        self.assertEqual(val,(1.0,2.0,3.0,4.0))
        sheet.close()

    def test_range1(self):
        """ Verify that getting range will fail if the worksheets are not setup """
        sheet = pyutilib.excel.ExcelSpreadsheet(pkgdir+"\\test_data.xls")
        try:
            tmp = sheet.get_range("sInfo")
            self.fail("Expected IOError because the range does not exist on the first sheet.")
        except IOError:
            pass
        del sheet

    def test_range2(self):
        """ Verify that ranges can be found on 'other' sheets """
        sheet = pyutilib.excel.ExcelSpreadsheet(pkgdir+"\\test_data.xls")
        try:
            tmp = sheet.get_range("sInfo")
            self.fail("Expected IOError because the range does not exist on the first sheet.", (1,2))
        except IOError:
            pass
        del sheet

Test = unittest.skipIf(not _win32com, "Cannot import 'win32com'")(Test)

if __name__ == "__main__":
    unittest.main()
