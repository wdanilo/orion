#! /usr/bin/env python
#  _________________________________________________________________________
#
#  PyUtilib: A Python utility library.
#  Copyright (c) 2008 Sandia Corporation.
#  This software is distributed under the BSD License.
#  Under the terms of Contract DE-AC04-94AL85000 with Sandia Corporation,
#  the U.S. Government retains certain rights in this software.
#  For more information, see the PyUtilib README.txt file.
#  _________________________________________________________________________
#
# This script creates a Python installer script.  Note that this script assumes that
# 'virtualenv' is installed in Python.
#

import os
import os.path
import virtualenv
import sys
import stat

if sys.version_info < (3,):
    files = ['odict.py']
else:
    files = []
# The files that are integrated into a virtualenv installer
files += ['OrderedConfigParser.py', 'header.py']

def main():
    if len(sys.argv) != 3:
        sys.stdout.write("vpy_create <config-file> <name>\n")
        sys.stdout.write("vpy_create vpy <name>\n")
        sys.exit(1)

    script_name = sys.argv[2]

    here = os.path.dirname(os.path.abspath(__file__))
    new_text = ""
    for file in files:
        new_text += "\n"
        new_text += "#\n"
        new_text += "# Imported from %s\n" % file
        new_text += "#\n"
        new_text += "\n"
        INPUT = open(os.path.join(here,file),'r')
        new_text += "".join( INPUT.readlines() )
        INPUT.close()
        new_text += "\n"
    if sys.argv[1] != 'vpy':
        new_text += "\n"
        new_text += "#\n"
        new_text += "# Imported from %s\n" % sys.argv[1]
        new_text += "#\n"
        new_text += "\n"
        INPUT = open(sys.argv[1],'r')
        new_text += "".join( INPUT.readlines() )
        INPUT.close()
    #new_text += "\n"
    #new_text += "Repository.easy_install_path='"+sys.prefix+os.sep+'bin'+os.sep+'easy_install'+"'"

    new_text = virtualenv.create_bootstrap_script(new_text)
    tmp = []
    for line in new_text.split('\n'):
        if 'win32api' in line:
            tmp.append( line[:line.index(line.strip())] + 'pass')
        #elif 'TODO' in line or 'FIXME' in line:
            #tmp.append( line[:line.index(line.strip())] + '# pyutilib.virtualenv: ignoring comment')
        else:
            tmp.append(line)
    new_text = "\n".join(tmp)
    if os.path.exists(script_name):
        f = open(script_name)
        cur_text = f.read()
        f.close()
    else:
        cur_text = ''
    sys.stdout.write('Updating %s' % script_name)
    if cur_text == new_text:
        sys.stdout.write('... no changes.\n')
    else:
        sys.stdout.write('... script changed.\n')
        f = open(script_name, 'w')
        f.write(new_text)
        f.close()
        os.chmod(script_name, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

if __name__ == '__main__':
    main()
