#  _________________________________________________________________________
#
#  PyUtilib: A Python utility library.
#  Copyright (c) 2008 Sandia Corporation.
#  This software is distributed under the BSD License.
#  Under the terms of Contract DE-AC04-94AL85000 with Sandia Corporation,
#  the U.S. Government retains certain rights in this software.
#  _________________________________________________________________________


import copy
import os
import imp
import sys
import pyutilib.common
try:
    import runpy
    runpy_available=True
except ImportError:   #pragma:nocover
    try:
        import runpy2 as runpy
        runpy_available=True
    except ImportError: #pragma:nocover
        runpy_available=False

def import_file(filename, context=None):
    """
    Import a Python file as a module

    This function returns the module object that is created.
    """

    # First thing to try: see if this is a module and not a file
    if not filename.endswith('.py'):
        module = None
        try:
            # is the module already imported?
            module = sys.modules[filename]
        except KeyError:
            try:
                module = __import__(filename)
                #print "Imported module '%s'" % ( filename )
            except ImportError:
                pass
        if module is not None:
            if not context is None:
                context[name] = module
            return module

    #
    # Parse the filename to get the name of the module to be imported
    #
    if '/' in filename:
        name = (filename).split("/")[-1]
    elif '\\' in filename:
        name = (filename).split("\\")[-1]
    else:
        name = filename

    # NB: endswith accepts tuples of strings starting in python 2.5.
    # For 2.4 compatibility we will call endswith() twice.
    if name.endswith('.py') or name.endswith('.pyc'):
        name = name.rsplit('.', 1)[0]
    if '.' in name:
        raise RuntimeError, \
              "Invalid python module name '%s'.  The head of the filename cannot contain a period." % filename

    #
    # Get the module if it already exists, and otherwise
    # import it
    #
    try:
        module = sys.modules[name]
    except KeyError:
        dirname = os.path.dirname( os.path.abspath(filename) )
        sys.path.insert( 0, dirname )
        try:
            module = imp.load_source( name, filename )
            #print "Loaded module '%s'" % ( filename )
        except Exception, e:
            import logging
            logger = logging.getLogger('pyutilib.misc')
            logger.error("Failed to load python module="+str(filename)+\
                         ":\n" + str(e))
            raise
        except:
            import logging
            logger = logging.getLogger("pyutilib.misc")
            logger.error("Failed to load python module="+str(filename))
            raise
            
        sys.path.remove( dirname )
    #
    # Add module to the give context
    #
    if not context is None:
        context[name] = module
    return module


def run_file(filename, logfile=None, execdir=None):
    """
    Execute a Python file and optionally redirect output to a logfile.
    """
    if not runpy_available:                     #pragma:nocover
        raise pyutilib.common.ConfigurationError, "Cannot apply the run_file() function because runpy is not available"
    #
    # Open logfile
    #
    if not logfile is None:
        sys.stderr.flush()
        sys.stdout.flush()
        save_stdout = sys.stdout
        save_stderr = sys.stderr
        OUTPUT=open(logfile,"w")
        sys.stdout=OUTPUT
        sys.stderr=OUTPUT
    #
    # Add the file directory to the system path
    #
    if '/' in filename:
        tmp= "/".join((filename).split("/")[:-1])
        tmp_import = (filename).split("/")[-1]
        sys.path.append(tmp)
    elif '\\' in filename:
        tmp = "\\".join((filename).split("\\")[:-1])
        tmp_import = (filename).split("\\")[-1]
        sys.path.append(tmp)
    else:
        tmp_import = filename
    name = ".".join((tmp_import).split(".")[:-1])
    #
    # Run the module
    #
    try:
        if not execdir is None:
            tmp=os.getcwd()
            os.chdir(execdir)
        runpy.run_module(name,None,"__main__")
        if not execdir is None:
            os.chdir(tmp)
    except Exception, err:          #pragma:nocover
        if not logfile is None:
            OUTPUT.close()
            sys.stdout = save_stdout
            sys.stderr = save_stderr
        raise
    #
    # Close logfile
    #
    if not logfile is None:
        OUTPUT.close()
        sys.stdout = save_stdout
        sys.stderr = save_stderr
