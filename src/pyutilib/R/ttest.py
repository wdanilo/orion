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
from misc_utilities import *

def t_test(x, y=None, mu=0, paired=False, var_equal=False, correct=True,
                conf_level=0.95, alternative=None):
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
    if y is not None:
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
    #
    # Print command line
    #
    print >>OUTPUT, "t.test(x,",
    #
    if y is not None:
        print >>OUTPUT, "y,",
    #
    if not correct:
        print >>OUTPUT, "correct=FALSE , ",
    else:
        print >>OUTPUT, "correct=TRUE , ",
    #
    print >>OUTPUT, "mu="+`mu`,",",
    #
    #print >>OUTPUT, "conf.level="+`conf_level`,",",
    #
    if not var_equal:
        print >>OUTPUT, "var.equal=FALSE ,",
    else:
        print >>OUTPUT, "var.equal=TRUE ,",
    #
    if not paired:
        print >>OUTPUT, "paired=FALSE",
    else:
        print >>OUTPUT, "paired=TRUE",
    #
    print >>OUTPUT, ")"
    OUTPUT.close()
    #
    # Execute R
    #
    cmdout = commands.getoutput("R --quiet --vanilla < R_script.R")
    ci_flag=False
    warning_flag=False
    warnings=[]
    ci = None
    pvalue=None
    df=None
    t_statistic=None
    for line in cmdout.split("\n"):
        #print line
        words = re.split('[ \t]+',line.strip())
        #print words
        if len(words) == 9 and words[6] == "p-value":
            pvalue= eval(words[8])
            df= eval(words[5].split(",")[0])
            t_statistic = eval(words[2].split(",")[0])
        if ci_flag == True:
            ci = [ eval(words[0]), eval(words[1]) ]
            ci_flag = False
        if len(words) > 2 and words[2] == "confidence":
            ci_flag=True
        if warning_flag:
            warnings.append(line)
        if len(words) > 0 and words[0] == "Warning":
            warning_flag=True
    #
    # Cleanup
    #
    commands.getoutput("rm R_script.R")
    return Bunch(conf_int=ci, t=t_statistic, warnings=warnings, df=df, p_value=pvalue)

##
## Launch 'main' if in interactive mode
##
if __name__ == '__main__':
    x = [1,2,3,4,5,6,7,8,9,10]
    print t_test(x)
    print t_test(x,x)
