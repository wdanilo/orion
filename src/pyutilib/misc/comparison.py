#  _________________________________________________________________________
#
#  PyUtilib: A Python utility library.
#  Copyright (c) 2008 Sandia Corporation.
#  This software is distributed under the BSD License.
#  Under the terms of Contract DE-AC04-94AL85000 with Sandia Corporation,
#  the U.S. Government retains certain rights in this software.
#  _________________________________________________________________________

import re
import copy
import sys
import os
import os.path
import difflib
import zipfile
import gzip
import filecmp
import math

float_p = r"[+-]? *(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"

def remove_chars_in_list(s, l):
    if len(l) == 0:
        return s

    schars = []
    for c in s:
        if c not in l:
            schars.append(c)

    snew = "".join(schars)

    return snew


def get_desired_chars_from_file(f, nchars, l=""):
    retBuf = ""
    while nchars > 0:
        buf = f.read(nchars)
        if len(buf) == 0:
            break

        buf = remove_chars_in_list(buf, l)
        nchars -= len(buf)
        retBuf = retBuf + buf

    return retBuf


def open_possibly_compressed_file(filename):
    if not os.path.exists(filename):
        raise IOError("cannot find file `"+filename+"'")
    if sys.version_info[:2] < (2,6) and zipfile.is_zipfile(filename):
        raise IOError( "cannot unpack a ZIP file with Python %s" 
                       % '.'.join(map(str,sys.version_info)) )
    if zipfile.is_zipfile(filename):
        zf1=zipfile.ZipFile(filename,"r")
        if len(zf1.namelist()) != 1:
            raise IOError("cannot compare with a zip file that contains "
                          "multiple files: `"+filename+"'")
        return zf1.open(zf1.namelist()[0],'r')
    elif filename.endswith('.gz'):
        return gzip.open(filename,"r")
    else:
        return open(filename,"r")


def file_diff(filename1, filename2, lineno=None, context=None):
    INPUT1=open_possibly_compressed_file(filename1)
    lines1 = INPUT1.readlines()
    for i in range(0,len(lines1)):
        lines1[i] = lines1[i].strip()
    INPUT1.close()

    INPUT2=open_possibly_compressed_file(filename2)
    lines2 = INPUT2.readlines()
    for i in range(0,len(lines2)):
        lines2[i] = lines2[i].strip()
    INPUT2.close()

    s=""
    if lineno is None:
        for line in difflib.unified_diff(lines2,lines1,fromfile=filename2,tofile=filename1):
            s += line+"\n"
    else:
        if context is None:
            context = 3
        start = lineno-context
        stop = lineno+context
        if start < 0:
            start=0
        if stop > len(lines1):
            stop = len(lines1)
        if stop > len(lines2):
            stop = len(lines2)
        for line in difflib.unified_diff(lines2[start:stop],lines1[start:stop],fromfile=filename2,tofile=filename1):
            s += line+"\n"
    return s


def compare_file_with_numeric_values(filename1, filename2, ignore=["\n","\r"], filter=None, tolerance=0.0):
    """
    Do a simple comparison of two files that ignores differences
    in newline types and whitespace.  Numeric values are compared within a specified tolerance.

    The return value is the tuple: (status,lineno).  If status is True,
    then a difference has occured on the specified line number.  If
    the status is False, then lineno is None.

    The goal of this utility is to simply indicate whether there are
    differences in files.  The Python 'difflib' is much more comprehensive
    and consequently more costly to apply.  The shutil.filecmp utility is
    similar, but it does not ignore differences in file newlines.  Also,
    this utility can ignore an arbitrary set of characters.
    """
    if not os.path.exists(filename1):
        raise IOError("compare_file: cannot find file `"+filename1+
                      "' (in "+os.getcwd()+")")
    if not os.path.exists(filename2):
        raise IOError("compare_file: cannot find file `"+filename2+
                      "' (in "+os.getcwd()+")")

    if filecmp.cmp(filename1, filename2):
        return [False, None, ""]

    INPUT1=open_possibly_compressed_file(filename1)
    INPUT2=open_possibly_compressed_file(filename2)
    lineno=0
    while True:

        # If either line is composed entirely of characters to
        # ignore, then get another one.  In this way we can
        # skip blank lines that are in one file but not the other

        line1 = ""
        while len(line1) == 0:
            line1=INPUT1.readline()
            if line1 == "":
                break
            if not filter is None and filter(line1):
                line1 = ""
            else:
                line1 = remove_chars_in_list(line1, ignore)
                line1.strip()
                if not filter is None and filter(line1):
                    line1 = ""
            lineno = lineno + 1

        line2 = ""
        while len(line2) == 0:
            line2=INPUT2.readline()
            if line2 == "":
                break
            if not filter is None and filter(line2):
                line2 = ""
            else:
                line2 = remove_chars_in_list(line2, ignore)
                line2.strip()
                if not filter is None and filter(line2):
                    line2 = ""

        #print "line1 '%s'" % line1
        #print "line2 '%s'" % line2

        if line1=="" and line2=="":
            return [False, None, ""]

        if line1=="" or line2=="":
            return [True, lineno, file_diff(filename1,filename2, lineno=lineno)]

        floats1 = re.findall(float_p, line1)
        floats2 = re.findall(float_p, line2)
        #print "floats1 '%s'" % floats1
        #print "floats2 '%s'" % floats2

        if len(floats1) != len(floats2):
            return [True, lineno, file_diff(filename1,filename2, lineno=lineno)]

        if len(floats1) > 0:
            for i in xrange(len(floats1)):
                if floats1[i] == floats2[i]:
                    continue
                try:
                    v1 = float(floats1[i])
                    v2 = float(floats2[i])
                except Exception, e:
                    return [True, lineno, file_diff(filename1,filename2, lineno=lineno)]
                if math.fabs(v1-v2) > tolerance:
                    return [True, lineno, file_diff(filename1,filename2, lineno=lineno)]

        line1 = re.sub(float_p, '#', line1.strip())
        line2 = re.sub(float_p, '#', line2.strip())

        #print "Line1 '%s'" % line1
        #print "Line2 '%s'" % line2

        index1=0
        index2=0
        while True:
            # Set the value of nc1
            if index1 == len(line1):
                nc1=None
            else:
                nc1=line1[index1]
            # Set the value of nc2
            if index2 == len(line2):
                nc2=None
            else:
                nc2=line2[index2]
            # Compare curent character values
            if nc1 != nc2:
                return [True, lineno, file_diff(filename1,filename2, lineno=lineno)]
            if nc1 is None and nc2 is None:
                break
            index1=index1+1
            index2=index2+1

    return [False, None, ""]
                        

def compare_file(filename1,filename2, ignore=["\t"," ","\n","\r"], filter=None, tolerance=None):
    """
    Do a simple comparison of two files that ignores differences
    in newline types.  If filename1 or filename2 is a zipfile, then it is
    assumed to contain a single file.

    The return value is the tuple: (status,lineno).  If status is True,
    then a difference has occured on the specified line number.  If
    the status is False, then lineno is None.

    The goal of this utility is to simply indicate whether there are
    differences in files.  The Python 'difflib' is much more comprehensive
    and consequently more costly to apply.  The shutil.filecmp utility is
    similar, but it does not ignore differences in file newlines.  Also,
    this utility can ignore an arbitrary set of characters.

    The 'filter' function evaluates each line separately.  If it returns True,
    then that line should be ignored.
    """
    if not tolerance is None:
        tmp = copy.copy(ignore)
        tmp.remove(' ')
        tmp.remove('\t')
        return compare_file_with_numeric_values(filename1, filename2, ignore=tmp, filter=filter, tolerance=tolerance)

    if not os.path.exists(filename1):
        raise IOError("compare_file: cannot find file `"+filename1+
                      "' (in "+os.getcwd()+")")
    if not os.path.exists(filename2):
        raise IOError("compare_file: cannot find file `"+filename2+
                      "' (in "+os.getcwd()+")")

    INPUT1 = open_possibly_compressed_file(filename1)
    INPUT2 = open_possibly_compressed_file(filename2)
    #
    # This is check is deferred until the zipfiles are setup to ensure a
    # consistent logic for zipfile analysis.  If the files are the same,
    # but they are zipfiles with > 1 files, then we raise an exception.
    #
    if not sys.platform.startswith('win') and os.stat(filename1) == os.stat(filename2):
        return [False, None, ""]
    #
    lineno=0
    while True:

        # If either line is composed entirely of characters to
        # ignore, then get another one.  In this way we can
        # skip blank lines that are in one file but not the other

        line1 = ""
        while len(line1) == 0:
            line1=INPUT1.readline()
            if line1 == "":
                break
            if not filter is None and filter(line1):
                line1 = ""
            else:
                line1 = remove_chars_in_list(line1, ignore)
                if not filter is None and filter(line1):
                    line1 = ""
            lineno = lineno + 1

        line2 = ""
        while len(line2) == 0:
            line2=INPUT2.readline()
            if line2 == "":
                break
            if not filter is None and filter(line2):
                line2 = ""
            else:
                line2 = remove_chars_in_list(line2, ignore)
                if not filter is None and filter(line2):
                    line2 = ""

        if line1=="" and line2=="":
            return [False, None, ""]

        if line1=="" or line2=="":
            return [True, lineno, file_diff(filename1,filename2, lineno=lineno)]

        index1=0
        index2=0
        while True:
            # Set the value of nc1
            if index1 == len(line1):
                nc1=None
            else:
                nc1=line1[index1]
            # Set the value of nc2
            if index2 == len(line2):
                nc2=None
            else:
                nc2=line2[index2]
            # Compare curent character values
            if nc1 != nc2:
                return [True, lineno, file_diff(filename1,filename2, lineno=lineno)]
            if nc1 is None and nc2 is None:
                break
            index1=index1+1
            index2=index2+1


def compare_large_file(filename1,filename2, ignore=["\t"," ","\n","\r"], bufSize=1 * 1024 * 1024):
    """
    Do a simple comparison of two files that ignores white space, or
    characters specified in "ignore" list.

    The return value is True if a difference is found, False otherwise.

    For very long text files, this function will be faster than
    compare_file() because it reads the files in by large chunks
    instead of by line.  The cost is that you don't get the lineno
    at which the difference occurs.
    """

    if not os.path.exists(filename1):
        raise IOError, "compare_large_file: cannot find file `"+filename1+"'"
    if not os.path.exists(filename2):
        raise IOError, "compare_large_file: cannot find file `"+filename2+"'"

    if sys.version_info[:2] < (2,6) and (zipfile.is_zipfile(filename1) or zipfile.is_zipfile(filename2)):
        raise IOError, "compare_file: cannot unpack a ZIP file with Python %s" % '.'.join(map(str,sys.version_info))
    if zipfile.is_zipfile(filename1):
        zf1=zipfile.ZipFile(filename1,"r")
        if len(zf1.namelist()) != 1:
            raise IOError, "compare_file: cannot compare with a zip file that contains multiple files: `"+filename2+"'"
        INPUT1 = zf1.open(zf1.namelist()[0],'r')
    elif filename1.endswith('.gz'):
        INPUT1=gzip.open(filename1,"r")
    else:
        INPUT1=open(filename1,"r")
    #
    if zipfile.is_zipfile(filename2):
        zf2=zipfile.ZipFile(filename2,"r")
        if len(zf2.namelist()) != 1:
            raise IOError, "compare_file: cannot compare with a zip file that contains multiple files: `"+filename2+"'"
        INPUT2 = zf2.open(zf2.namelist()[0],'r')
    elif filename2.endswith('.gz'):
        INPUT2=gzip.open(filename2,"r")
    else:
        INPUT2=open(filename2,"r")
    #
    # This is check is deferred until the zipfiles are setup to ensure a consistent logic for
    # zipfile analysis.  If the files are the same, but they are zipfiles with > 1 files, then we
    # raise an exception.
    #
    if not sys.platform.startswith('win') and os.stat(filename1) == os.stat(filename2):
        return False

    f1Size = os.stat(filename1).st_size
    f2Size = os.stat(filename2).st_size

    result = False

    while True:
        buf1 = get_desired_chars_from_file(INPUT1, bufSize, ignore)
        buf2 = get_desired_chars_from_file(INPUT2, bufSize, ignore)

        if len(buf1) == 0 and len(buf2) == 0:
            break
        elif len(buf1) == 0 or len(buf2) == 0:
            result = True
            break

        if len(buf1) != len(buf2) or buf1 != buf2 :
            result = True
            break

    INPUT1.close()
    INPUT2.close()
    return result



    if len(l) == 0:
        return s


