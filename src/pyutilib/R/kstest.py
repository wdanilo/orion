#  _________________________________________________________________________
#
#  PyUtilib: A Python utility library.
#  Copyright (c) 2008 Sandia Corporation.
#  This software is distributed under the BSD License.
#  Under the terms of Contract DE-AC04-94AL85000 with Sandia Corporation,
#  the U.S. Government retains certain rights in this software.
#  _________________________________________________________________________

import re
import os
import sys
import string
import commands
import types
from misc_utilities import *

def ks_test(x, y, mu=0, exact=None, alternative=None):
    OUTPUT = open("R_script.R","w")
    #
    # Print 'x'
    #
    print >>OUTPUT, "x <- c(",
    first=True
    for val in x:
        if not first:
            print >>OUTPUT, " , ",
        else:
            first=False
            print >>OUTPUT, " ",
        print >>OUTPUT, val,
    print >>OUTPUT, ")"
    #
    # Print 'y'
    #
    if isinstance(y,types.ListType):
        print >>OUTPUT, "y <- c(",
        first=True
        for val in y:
            if not first:
                print >>OUTPUT, " , ",
            else:
                first=False
                print >>OUTPUT, " ",
            print >>OUTPUT, val,
        print >>OUTPUT, ")"
        y=",y"
    else:
        y = ", \""+y.split(",")[0]+"\", " + ",".join(y.split(",")[1:])
    #
    # Print command line
    #
    print >>OUTPUT, "ks.test(x"+y,
    #
    if alternative is not None:
        print >>OUTPUT, ",alternative="+`alternative`,
    #
    if exact is not None:
        if not exact:
            print >>OUTPUT, ",exact=FALSE",
        else:
            print >>OUTPUT, ",exact=TRUE",
    #
    print >>OUTPUT, ")"
    OUTPUT.close()
    #
    # Execute R
    #
    #os.system("cat R_script.R")
    cmdout = commands.getoutput("R --quiet --vanilla < R_script.R")
    warning_flag=False
    warnings=[]
    pvalue=None
    ks_statistic=None
    for line in cmdout.split("\n"):
        #print line
        words = re.split('[ \t]+',line.strip())
        if len(words) == 6 and words[3] == "p-value":
            pvalue= eval(words[5])
            ks_statistic = eval(words[2].split(",")[0])
        if warning_flag:
            warnings.append(line)
        if len(words) > 0 and words[0] == "Warning":
            warning_flag=True
    #
    # Cleanup
    #
    commands.getoutput("rm R_script.R")
    return Bunch(D=ks_statistic, warnings=warnings, p_value=pvalue)

##
## Launch 'main' if in interactive mode
##
if __name__ == '__main__':
    x = [1,2,3,4,5,6,7,8,9,10]
    y = [1.1,2.1,3.1,4.1,5.1,6.1,7.1,8.1,9.1,10.1]
    print ks_test(x,y)
    y = "pgamma, 3, 2"
    print ks_test(x,y)
