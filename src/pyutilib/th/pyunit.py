#  _________________________________________________________________________
#
#  PyUtilib: A Python utility library.
#  Copyright (c) 2008 Sandia Corporation.
#  This software is distributed under the BSD License.
#  Under the terms of Contract DE-AC04-94AL85000 with Sandia Corporation,
#  the U.S. Government retains certain rights in this software.
#  _________________________________________________________________________


__all__ = ['TestCase','TestResult','TestSuite','TextTestRunner','main','nottest','category']

from inspect import getfile
import pyutilib.misc
import stat
import os
import sys
import filecmp
import re
if sys.version_info[:2] < (2,7):
    try:
        import unittest2 as unittest
        main = unittest.main
        using_unittest2 = True
    except ImportError:
        import unittest
        main = unittest.main
        using_unittest2 = False
else:
    import unittest
    using_unittest2 = True
    main = unittest.main

if using_unittest2:
    __all__.extend(['skip','skipIf','skipUnless','expectedFailure','SkipTest'])
    skip = unittest.skip
    skipIf = unittest.skipIf
    skipUnless = unittest.skipUnless
    expectedFailure = unittest.expectedFailure
    SkipTest = unittest.SkipTest
import subprocess
#from misc import *

TextTestRunner = unittest.TextTestRunner
TestResult = unittest.TestResult
TestSuite = unittest.TestSuite

try:
    from nose.tools import nottest
except ImportError:
    def nottest(func):
        """Decorator to mark a function or method as *not* a test"""
        func.__test__ = False
        return func


_test_categories=set()
def _reset_test_categories():
    global _test_categories
    if 'PYUTILIB_UNITTEST_CATEGORIES' in os.environ:
        if _reset_test_categories.cache == os.environ['PYUTILIB_UNITTEST_CATEGORIES']:
            return
        _test_categories=set()
        for cat in re.split(',', os.environ['PYUTILIB_UNITTEST_CATEGORIES']):
            _test_categories.add( cat.strip() )
        _reset_test_categories.cache=os.environ['PYUTILIB_UNITTEST_CATEGORIES']
    else:
        _test_categories=set()
_reset_test_categories.cache=None

def category(*args):
    _reset_test_categories()
    do_wrap=False
    if not using_unittest2 or len(_test_categories) == 0:
        do_wrap=True
    for cat in args:
        if cat.strip() in _test_categories:
            do_wrap=True
            break
    if do_wrap:
        def _id(func):
            for arg in args:
                setattr(func, arg.strip(), 1)
            return func
        return _id
    else:
        return skip("Decorator test categories %s do not include a required test category %s" % (sorted(args), sorted(list(_test_categories))) )

#@nottest
def _run_import_baseline_test(self, cwd=None, module=None, outfile=None, baseline=None, filter=None, tolerance=None):
    if cwd is None:
        cwd = os.path.dirname(os.path.abspath(getfile(self.__class__)))
    oldpwd = os.getcwd()
    os.chdir(cwd)
    sys.path.insert(0, cwd)
    #
    try:
        pyutilib.misc.setup_redirect(outfile)
        pyutilib.misc.import_file(module+".py")
        pyutilib.misc.reset_redirect()
        #
        self.assertFileEqualsBaseline(outfile, baseline, filter=filter, tolerance=tolerance)
    finally:
        os.chdir(oldpwd)
        sys.path.remove(cwd)

#@nottest
def _run_cmd_baseline_test(self, cwd=None, cmd=None, outfile=None, baseline=None, filter=None, cmdfile=None, tolerance=None):
    if cwd is None:
        cwd = os.path.dirname(os.path.abspath(getfile(self.__class__)))
    oldpwd = os.getcwd()
    os.chdir(cwd)

    try:
        OUTPUT=open(outfile,"w")
        proc = subprocess.Popen(cmd.strip(),shell=True,stdout=OUTPUT,stderr=subprocess.STDOUT)
        proc.wait()
        OUTPUT.close()
        if not cmdfile is None:
            OUTPUT=open(cmdfile,'w')
            print >>OUTPUT, "#!/bin/sh"
            print >>OUTPUT, "# Baseline test command"
            print >>OUTPUT, "#    cwd     ", cwd
            print >>OUTPUT, "#    outfile ", outfile
            print >>OUTPUT, "#    baseline", baseline
            print >>OUTPUT, cmd
            OUTPUT.close()
            os.chmod(cmdfile, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)
        self.assertFileEqualsBaseline(outfile, baseline, filter=filter, tolerance=tolerance)
        if not cmdfile is None:
            os.remove(cmdfile)
    finally:
        os.chdir(oldpwd)

#@nottest
def _run_fn_baseline_test(self, fn=None, name=None, baseline=None, filter=None, tolerance=None):
    files = fn(name)
    self.assertFileEqualsBaseline(files[0], baseline, filter=filter, tolerance=tolerance)
    for file in files[1:]:
        os.remove(file)

#@nottest
def _run_fn_test(self, fn, name, suite):
    if suite is None:
        explanation = fn(self, name)
    else:
        explanation = fn(self, name, suite)
    if not explanation is None and explanation != "":
        self.fail(explanation)


class TestCase(unittest.TestCase):

    """ Dictionary of options that may be used by function tests. """
    _options = {}

    def __init__(self, methodName='runTest'):
        unittest.TestCase.__init__(self, methodName)

    def get_options(self, name, suite=None):
        return self._options[suite,name]

    @nottest
    def recordTestData(self, name, value):
        """A method for recording data associated with a test.  This method is only
           meaningful when running this TestCase with 'nose', using the TestData plugin.
        """
        tmp = getattr(self, 'testdata', None)
        if not tmp is None:
            tmp[name] = value

    def assertMatchesYamlBaseline(self, testfile, baseline, delete=True, tolerance=0.0, exact=False):
        try:
            pyutilib.misc.compare_yaml_files(baseline,testfile,tolerance=tolerance,exact=exact)
            if delete:
                os.remove(testfile)
        except Exception, err:
            self.fail("YAML testfile does not match the baseline:\n   testfile="+testfile+"\n   baseline="+baseline+"\n"+str(err))

    def assertMatchesJsonBaseline(self, testfile, baseline, delete=True, tolerance=0.0, exact=False):
        try:
            pyutilib.misc.compare_json_files(baseline,testfile,tolerance=tolerance,exact=exact)
            if delete:
                os.remove(testfile)
        except Exception, err:
            self.fail("JSON testfile does not match the baseline:\n   testfile="+testfile+"\n   baseline="+baseline+"\n"+str(err))

    def assertFileEqualsBaseline(self, testfile, baseline, filter=None, delete=True, tolerance=None):
        [flag,lineno,diffs] = pyutilib.misc.compare_file(testfile, baseline, filter=filter, tolerance=tolerance)
        if not flag:
            if delete:
                os.remove(testfile)
        else:                                   #pragma:nocover
            self.fail("Unexpected output difference at line "+str(lineno) +":\n   testfile="+testfile+"\n   baseline="+baseline+"\nDiffs:\n"+diffs)
        return [flag,lineno]

    def assertFileEqualsLargeBaseline(self, testfile, baseline, delete=True):
        flag = pyutilib.misc.compare_large_file(testfile,baseline)
        if not flag:
            if delete:
                os.remove(testfile)
        else:                                   #pragma:nocover
            self.fail("Unexpected output difference:\n   testfile="+testfile+"\n   baseline="+baseline)
        return flag

    def assertFileEqualsBinaryFile(self, testfile, baseline, delete=True):
        theSame = filecmp.cmp(testfile, baseline)
        if theSame:
            if delete:
                os.remove(testfile)
        else:                                   #pragma:nocover
            self.fail("Unexpected output difference:\n   testfile="+testfile+"\n   baseline="+baseline)
        return theSame

    @nottest
    def add_fn_test(cls, name=None, suite=None, fn=None, options=None):
        if fn is None:
            print "ERROR: must specify the 'fn' option to define the test"
            return
        if name is None:
            print "ERROR: must specify the 'name' option to define the test"
            return
        tmp = name.replace("/","_")
        tmp = tmp.replace("\\","_")
        tmp = tmp.replace(".","_")
        func = lambda self,c1=fn,c2=name,c3=suite: _run_fn_test(self,c1,c2,c3)
        func.__name__ = "test_"+str(tmp)
        #func.__doc__ = "Running function test: "+func.__name__
        func.__doc__ = "function test: "+func.__name__+ \
                       " ("+str(cls.__module__)+'.'+str(cls.__name__)+")"
        setattr(cls, "test_"+tmp, func)
        cls._options[suite,name] = options
    add_fn_test=classmethod(add_fn_test)

    @nottest
    def add_baseline_test(cls, name=None, cmd=None, fn=None, baseline=None, filter=None, cwd=None, cmdfile=None, tolerance=None):
        if cmd is None and fn is None:
            print "ERROR: must specify either the 'cmd' or 'fn' option to define how the output file is generated"
            return
        if name is None:
            print "ERROR: must specify the test name"
            return
        if baseline is None:
            baseline=name+".txt"
        tmp = name.replace("/","_")
        tmp = tmp.replace("\\","_")
        tmp = tmp.replace(".","_")
        #
        # Create an explicit function so we can assign it a __name__ attribute.
        # This is needed by the 'nose' package
        #
        if fn is None:
            func = lambda self,c1=cwd,c2=cmd,c3=tmp+".out",c4=baseline,c5=filter,c6=cmdfile,c7=tolerance: _run_cmd_baseline_test(self,cwd=c1,cmd=c2,outfile=c3,baseline=c4,filter=c5,cmdfile=c6,tolerance=c7)
        else:
            func = lambda self,c1=fn,c2=name,c3=baseline,c4=filter,c5=tolerance: _run_fn_baseline_test(self,fn=c1,name=c2,baseline=c3,filter=c4,tolerance=c5)
        func.__name__ = "test_"+tmp
        #func.__doc__ = "Running baseline test: "+func.__name__
        func.__doc__ = "baseline test: "+func.__name__+ \
                       " ("+str(cls.__module__)+'.'+str(cls.__name__)+")"
        if fn is None and not cmdfile is None:
            func.__doc__ += "  Command archived in "+cmdfile
        setattr(cls, "test_"+tmp, func)
    add_baseline_test=classmethod(add_baseline_test)

    @nottest
    def add_import_test(cls, module=None, name=None, cwd=None, baseline=None, filter=None, tolerance=None):
        if module is None and name is None:
            print "ERROR: must specify the module that is imported"
            return
        if module is None:
            module=name
        if name is None:
            print "ERROR: must specify test name"
            return
        if baseline is None:
            baseline=name+".txt"
        tmp = name.replace("/","_")
        tmp = tmp.replace("\\","_")
        tmp = tmp.replace(".","_")
        #
        # Create an explicit function so we can assign it a __name__ attribute.
        # This is needed by the 'nose' package
        #
        func = lambda self,c1=cwd,c2=module,c3=tmp+".out",c4=baseline,c5=filter,c6=tolerance: _run_import_baseline_test(self,cwd=c1,module=c2,outfile=c3,baseline=c4,filter=c5,tolerance=c6)
        func.__name__ = "test_"+tmp
        func.__doc__ = "Running import test: "+func.__name__
        setattr(cls, "test_"+tmp, func)
    add_import_test=classmethod(add_import_test)

