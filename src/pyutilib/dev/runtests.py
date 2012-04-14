
import os
import sys
import pyutilib.subprocess
import glob
import optparse

if sys.platform.startswith('win'):
    platform='win'
else:
    platform='linux'

def run(package, argv):
    parser = optparse.OptionParser(usage='run [OPTIONS] <dirs>')

    parser.add_option('-v','--verbose',
        action='store_true',
        dest='verbose',
        default=False,
        help='Verbose output')
    parser.add_option('--coverage',
        action='store_true',
        dest='coverage',
        default=False,
        help='Enable the computation of coverage information')
    parser.add_option('-p','--package',
        action='store',
        dest='pkg',
        default='pyutilib',
        help='Limit the coverage to this package')
    parser.add_option('-o','--output',
        action='store',
        dest='output',
        default=None,
        help='Redirect output to a file')

    options, args = parser.parse_args(argv)

    if len(args) == 1:
        parser.print_help()
        sys.exit(1)

    if 'performance' in os.environ.get('PYUTILIB_UNITTEST_CATEGORIES','').split(','):
        os.environ['NOSE_WITH_TESTDATA'] = '1'
        os.environ['NOSE_WITH_FORCED_GC'] = '1'
        attr = ['-a','performance']
    else:
        attr = []

    if options.pkg != "":
        cpkg=['--cover-package='+options.pkg]
    else:
        cpkg=[]
    if options.verbose:
        vflag=['-v']
    else:
        vflag=[]

    if options.coverage:
        coverage_flags = ['--with-coverage','--cover-erase'] + cpkg
        os.environ['COVERAGE_FILE'] = os.getcwd()+os.sep+'.coverage'
    else:
        coverage_flags = []

    dirs=set()
    dirs.add( os.getcwd() )
    for arg in args[1:]:
        for dir in glob.glob(arg+'*'):
            dirs.add(dir)

    cwd = os.path.dirname(os.getcwd())
    if platform == 'win':
        srcdirs=[]
        for dir in glob.glob('*'):
            if os.path.isdir(dir):
                srcdirs.append(os.path.abspath(dir))
        os.environ['PYTHONPATH']=os.pathsep.join(srcdirs)
        cmd = [ os.path.join(sys.exec_prefix,'Scripts','python.exe'),
                os.path.join(sys.exec_prefix,'Scripts','nosetests-script.py') ]
        os.environ['PATH'] = os.path.join(cwd,'Scripts') + os.pathsep + \
                             os.environ.get('PATH','')
    else:
        cmd = [ os.path.join(sys.exec_prefix,'bin','nosetests') ]
        os.environ['PATH'] = os.path.join(cwd,'bin') + os.pathsep + \
                             os.environ.get('PATH','')

    cmd.extend(coverage_flags)
    cmd.extend(vflag)
    cmd.append('--with-xunit')
    cmd.append('--xunit-file=TEST-' + package + '.xml')
    cmd.extend(attr)
    cmd.extend(list(dirs))
    
    print "Running... ",cmd
    print ""
    if options.output:
        print "Redirecting output to file '%s' ..." % options.output,
        sys.stdout.flush()
        pyutilib.subprocess.run(cmd, outfile=options.output)
        print "done."
        sys.stdout.flush()
    else:
        pyutilib.subprocess.run(cmd, tee=True)


def runPyUtilibTests():
    parser = optparse.OptionParser(usage='test.pyutilib [options] <dirs>')

    parser.add_option('-d','--dir',
        action='store',
        dest='dir',
        default=None,
        help='Top-level source directory where the tests are applied.')
    parser.add_option('--all',
        action='store_true',
        dest='all_cats',
        default=False,
        help='All tests are executed.')
    parser.add_option('--cat','--category',
        action='append',
        dest='cats',
        default=[],
        help='Specify test categories.')
    parser.add_option('--cov','--coverage',
        action='store_true',
        dest='coverage',
        default=False,
        help='Indicate that coverage information is collected')
    parser.add_option('-v','--verbose',
        action='store_true',
        dest='verbose',
        default=False,
        help='Verbose output')
    parser.add_option('-o','--output',
        action='store',
        dest='output',
        default=None,
        help='Redirect output to a file')

    _options, args = parser.parse_args(sys.argv)

    #if len(args) == 1:
        #parser.print_help()
        #sys.exit(1)

    if _options.output:
        outfile = os.path.abspath(_options.output)
    else:
        outfile = None
    if _options.dir is None:
        os.chdir( os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))) )
    else:
        os.chdir( _options.dir )

    print "Running tests in directory",os.getcwd()
    if _options.all_cats is True:
        _options.cats = []
    elif len(_options.cats) == 0:
        _options.cats = ['smoke']
    elif 'all' in _options.cats:
        _options.cats = []
    if len(_options.cats) > 0:
        os.environ['PYUTILIB_UNITTEST_CATEGORIES'] = ",".join(_options.cats)
        print " ... for test categories: "+ os.environ['PYUTILIB_UNITTEST_CATEGORIES']
    options=[]
    if _options.coverage:
        options.append('--coverage')
    if _options.verbose:
        options.append('-v')
    if outfile:
        options.append('-o')
        options.append(outfile)
    if len(args) == 1:
        dirs=['pyutilib']
    else:
        dirs=[]
        for dir in args:
            if dir.startswith('-'):
                options.append(dir)
            elif dir.startswith('pyutilib'):
                dirs.append(dir)
            else:
                dirs.append('pyutilib.'+dir)
        if len(dirs) == 0:
            dirs = ['pyutilib']
    pyutilib.dev.runtests.run('pyutilib',['runtests']+options+['-p','pyutilib']+dirs)
