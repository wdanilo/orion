import os
import sys
from os.path import abspath, dirname
currdir = dirname(abspath(__file__))+os.sep

import pyutilib.th as unittest
from nose.tools import nottest
import pyutilib.services
from pyutilib.subprocess import subprocess, SubprocessMngr, timer

pyutilib.services.register_executable("memmon")
pyutilib.services.register_executable("valgrind")

class Test(unittest.TestCase):

    def test_foo(self):
        if not subprocess.mswindows:
            #foo = SubprocessMngr("ls *py > /tmp/.pyutilib", shell=True)
            #foo.wait()
            #print ""

            foo = SubprocessMngr("ls *py > /tmp/.pyutilib", stdout=subprocess.PIPE, shell=True)
            #for line in foo.process.stdout:
                #print line,
            print ""
            if os.path.exists("/tmp/.pyutilib"):
                os.remove("/tmp/.pyutilib")
        else:
            foo = SubprocessMngr("cmd /C \"dir\" > C:/tmp", shell=True)
            foo.wait()
            print ""

        stime = timer()
        # On MS Windows, do not run this in a shell.  If so, MS Windows has difficulty
        # killing the process after the timelimit
        print "Subprocess python process"
        sys.stdout.flush()
        foo = SubprocessMngr("python -q -c \"while True: pass\"", shell=not subprocess.mswindows)
        foo.wait(5)
        print "Ran for " + `timer()-stime` + " seconds"

    @unittest.skipIf(subprocess.mswindows, "Cannot test the use of 'memmon' on MS Windows")
    @unittest.skipIf(pyutilib.services.registered_executable('memmon') is None, "The 'memmon' executable is not available.")
    def test_memmon(self):
        pyutilib.services.register_executable('ls')
        pyutilib.subprocess.run(pyutilib.services.registered_executable('ls').get_path()+' *.py', memmon=True, outfile=currdir+'ls.out')
        INPUT = open(currdir+'ls.out','r')
        flag = False
        for line in INPUT:
            flag = line.startswith('memmon:')
            if flag:
                break
        if not flag:
            self.fail("Failed to properly execute 'memmon' with the 'ls' command")
        os.remove(currdir+'ls.out')

    @unittest.skipIf(subprocess.mswindows, "Cannot test the use of 'valgrind' on MS Windows")
    @unittest.skipIf(pyutilib.services.registered_executable('valgrind') is None, "The 'valgrind' executable is not available.")
    def test_valgrind(self):
        pyutilib.services.register_executable('ls')
        pyutilib.subprocess.run(pyutilib.services.registered_executable('ls').get_path()+' *.py', valgrind=True, outfile=currdir+'valgrind.out')
        INPUT = open(currdir+'valgrind.out','r')
        flag = False
        for line in INPUT:
            flag = 'Memcheck' in line
            if flag:
                break
        if not flag:
            self.fail("Failed to properly execute 'valgrind' with the 'ls' command")
        os.remove(currdir+'valgrind.out')
        

if __name__ == "__main__":
    unittest.main()
