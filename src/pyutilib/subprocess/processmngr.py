#  _________________________________________________________________________
#
#  PyUtilib: A Python utility library.
#  Copyright (c) 2008 Sandia Corporation.
#  This software is distributed under the BSD License.
#  Under the terms of Contract DE-AC04-94AL85000 with Sandia Corporation,
#  the U.S. Government retains certain rights in this software.
#  _________________________________________________________________________

__all__ = ['subprocess', 'SubprocessMngr', 'run_command', 'timer', 'signal_handler', 'run']

import GlobalData
import time
import signal
import os
import sys
import tempfile
import subprocess
import copy
from threading import Thread
if subprocess.mswindows and sys.version_info[0:2] < (2,5):
    import ctypes

import pyutilib.services
from pyutilib.common import *
from pyutilib.misc import quote_split



def kill_process(process, sig=signal.SIGTERM, verbose=False):
    """
    Kill a process given a process ID
    """
    pid = process.pid
    if GlobalData.debug or verbose:
        print "Killing process",pid,"with signal",sig
    if subprocess.mswindows:
        if sys.version_info[0:2] < (2,5):
            os.system("taskkill /t /f /pid "+repr(pid))
        else:
            PROCESS_TERMINATE = 1
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
            ctypes.windll.kernel32.TerminateProcess(handle, -1)
            ctypes.windll.kernel32.CloseHandle(handle)
    else:
        #
        # Kill process and all its children
        #
        pgid=os.getpgid(pid)
        if pgid == -1:
            print "  ERROR: invalid pid",pid
            sys.exit(1)
        os.killpg(pgid,signal.SIGTERM)
        #
        # This is a hack.  The Popen.__del__ method references
        # the 'os' package, and when a process is interupted this
        # package is deleted before Popen.  I can't figure out why
        # _del_ is being called when Python closes down, though.  HOWEVER,
        # we can hard-ware Popen.__del__ to return immediately by telling it
        # that it did not create a child process!
        #
        if not GlobalData.current_process is None:
            GlobalData.current_process._child_created=False


GlobalData.current_process=None
GlobalData.pid=None
GlobalData.signal_handler_busy=False
#
# A signal handler that passes on the signal to the child process.
#
def verbose_signal_handler(signum, frame):
    c = frame.f_code
    print '  Signal handler called from ', c.co_filename, c.co_name, frame.f_lineno
    print "  Waiting...",
    signal_handler(signum, frame, True)

def signal_handler(signum, frame, verbose=False):
    if GlobalData.signal_handler_busy:
        print ""
        print "  Signal handler is busy.  Aborting."
        sys.exit(-signum)
    if GlobalData.current_process is None:
        print "  Signal",signum,"recieved, but no process queued"
        print "  Exiting now"
        sys.exit(-signum)
    if GlobalData.current_process is not None and\
       GlobalData.current_process.pid is not None and\
       GlobalData.current_process.poll() is None:
        GlobalData.signal_handler_busy=True
        kill_process(GlobalData.current_process, signum)
        if verbose:
            print "  Signaled process", GlobalData.current_process.pid,"with signal",signum
        endtime = timer()+1.0
        while timer() < endtime:
            status = GlobalData.current_process.poll()
            if status is None:
                break
            time.sleep(0.1)
        #GlobalData.current_process.wait()
        status = GlobalData.current_process.poll()
        if status is not None:
            GlobalData.signal_handler_busy=False
            if verbose:
                print "Done."
            raise OSError, "Interrupted by signal " + repr(signum)
        else:
            raise OSError, "Problem terminating process" + repr(GlobalData.current_process.pid)
        GlobalData.current_process = None
    raise OSError, "Interrupted by signal " + repr(signum)


#
# A function used to read in data from a shell command, and push it into a pipe.
#
def _read_data(stream, ostr1, ostr2):
    while True:
        data = os.read(stream, 80)
        if data:
            ostr1.write(data)
            ostr2.write(data)
            ostr1.flush()
            ostr2.flush()
        else:
            break

#
# A depricated read_data function
#
def X_read_data(stream, ostr1, ostr2):
    li = [stream]
    ctr = 0
    while ctr < 3:
        i,o,e = select.select(li,[],[], 0.0)
        if i:
            data = os.read(stream,2048)
            if data:
                ostr1.write(data)
                ostr2.write(data)
                ostr1.flush()
                ostr2.flush()
            else:
                li = []
            ctr = 0
        else:
            ctr += 1
        if ctr:
            time.sleep(1.0)

#
# Execute the command as a subprocess that we can send signals to.
# After this is finished, we can get the output from this command from
# the process.stdout file descriptor.
#
def run_command(cmd, outfile=None, cwd=None, ostream=None, stdin=None, stdout=None, stderr=None, valgrind=False, valgrind_log=None, valgrind_options=None, memmon=False, env=None, define_signal_handlers=True, debug=False, verbose=True, timelimit=None, tee=None, ignore_output=False, shell=False, thread_reader=_read_data):
    #
    # Move to the specified working directory
    #
    if cwd is not None:
        oldpwd = os.getcwd()
        os.chdir(cwd)

    cmd_type = type(cmd)
    if cmd_type is list:
        # make a private copy of the list
        _cmd = cmd[:]
    elif cmd_type is tuple:
        _cmd = list(cmd)
    else:
        _cmd = quote_split(cmd.strip())
        
    #
    # Setup memmoon
    #
    if memmon:
        memmon = pyutilib.services.registered_executable("memmon")
        if memmon is None:
            raise IOError, "Unable to find the 'memmon' executable"
        _cmd.insert(0, memmon.get_path())
    #
    # Setup valgrind
    #
    if valgrind:
        #
        # The valgrind_log option specifies a logfile that is used to store
        # valgrind output.
        #
        valgrind_cmd = pyutilib.services.registered_executable("valgrind")
        if valgrind_cmd is None:
            raise IOError, "Unable to find the 'valgrind' executable"
        valgrind_cmd = [ valgrind_cmd.get_path() ]
        if valgrind_options is None:
            valgrind_cmd.extend(
                ( "-v","--tool=memcheck","--trace-children=yes" ))
        elif type(valgrind_options) in (list, tuple):
            valgrind_cmd.extend(valgrind_options)
        else:
            valgrind_cmd.extend(quote_split(valgrind_options.strip()))
        if valgrind_log is not None:
            valgrind_cmd.append("--log-file-exactly="+valgrind_log.strip())
        _cmd = valgrind_cmd + _cmd
    #
    # Redirect stdout and stderr
    #
    tmpfile=None
    if ostream is not None:
        stdout_arg=ostream
        stderr_arg=ostream
        if outfile is None:
            output = "Output printed to specified ostream"
        else:
            output = "Output printed to specified ostream (%s)" % outfile
    elif outfile is not None:
        stdout_arg=open(outfile,"w")
        stderr_arg=stdout_arg
        output = "Output printed to file '%s'" % outfile
    elif not (stdout is None and stderr is None):
        stdout_arg=stdout
        stderr_arg=stderr
        output = "Output printed to specified stdout and stderr streams"
    else:
        tmpfile = tempfile.TemporaryFile()
        stdout_arg=tmpfile
        stderr_arg=tmpfile
        output=""
    #
    # Setup the default environment
    #
    if env is None:
        env=copy.copy(os.environ)
    #
    # Setup signal handler
    #
    if define_signal_handlers:
        if verbose:
            signal.signal(signal.SIGINT, verbose_signal_handler)
            if sys.platform[0:3] != "win" and sys.platform[0:4] != 'java':
                signal.signal(signal.SIGHUP, verbose_signal_handler)
            signal.signal(signal.SIGTERM, verbose_signal_handler)
        else:
            signal.signal(signal.SIGINT, signal_handler)
            if sys.platform[0:3] != "win" and sys.platform[0:4] != 'java':
                signal.signal(signal.SIGHUP, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
    rc = -1
    if debug:
        print "Executing command %s" % (_cmd, )
    try:
        GlobalData.signal_handler_busy=False
        if (tee is None) or (tee is False):
            #
            # Redirect IO to the stdout_arg/stderr_arg files
            #
            process = SubprocessMngr(_cmd, stdin=stdin, stdout=stdout_arg, stderr=stderr_arg, env=env, shell=shell)
            GlobalData.current_process = process.process
            rc = process.wait(timelimit)
            GlobalData.current_process = None
        else:
            #
            # Aggressively wait for output from the process, and
            # send this to both the stdout/stdarg value, as well
            # as doing a normal 'print'
            #
            rpipe1, wpipe1 = os.pipe()
            ##rpipe2, wpipe2 = os.pipe()
            #
            process = SubprocessMngr(_cmd, stdin=stdin, stdout=wpipe1, stderr=wpipe1, env=env, shell=shell)
            GlobalData.current_process = process.process
            #
            # Create a thread to read in stdout and stderr data
            #
            GlobalData.signal_handler_busy=False
            outt = Thread(target=_read_data, args=(rpipe1, sys.stdout, stdout_arg))
            outt.daemon = True
            outt.start()
            ##errt = Thread(target=_read_data, args=(rpipe2, sys.stderr, stderr_arg))
            ##errt.daemon = True
            ##errt.start()
            #
            # Wait for process to finish
            #
            rc = process.wait(timelimit)
            GlobalData.current_process = None
            #
            # 'Closing' the PIPE to send EOF to the reader.
            #
            os.close(wpipe1)
            ##os.close(wpipe2)
            #
            # Wait for readers to finish up with the data in the pipe.
            #
            outt.join()
            ##errt.join()
            del outt
            ##del errt
            os.close(rpipe1)
            ##os.close(rpipe2)

    except WindowsError, err:
        raise ApplicationError(
            "Could not execute the command: '%s'\n\tError message: %s"
            % (' '.join(_cmd), err) )
    except OSError:
        #
        # Ignore IOErrors, which are caused by interupts
        #
        pass
    if ostream is None and outfile is not None:
        stdout_arg.close()
    elif not tmpfile is None and not ignore_output:
        tmpfile.seek(0)
        output = "".join(tmpfile.readlines())
    sys.stdout.flush()
    sys.stderr.flush()
    #
    # Move back from the specified working directory
    #
    if cwd is not None:
        os.chdir(oldpwd)
    #
    # Return the output
    #
    return [rc, output]

# Create an alias for run_command
run=run_command

#
# Setup the timer
#
if subprocess.mswindows:
    timer = time.clock
else:
    timer = time.time


class SubprocessMngr(object):

    def __init__(self, cmd, stdin=None, stdout=None, stderr=None, env=None, bufsize=0, shell=False):
        """
        Setup and launch a subprocess
        """
        self.process = None
        #
        # By default, stderr is mapped to stdout
        #
        if stderr is None:
            stderr=subprocess.STDOUT

        self.stdin = stdin
        if stdin is None:
            stdin_arg = None
        else:
            stdin_arg = subprocess.PIPE
        #
        # We would *really* like to deal with commands in execve form
        #
        if type(cmd) not in (list, tuple):
            cmd = quote_split(cmd.strip())
        #
        # Launch subprocess using a subprocess.Popen object
        #
        if subprocess.mswindows:
            #
            # Launch without console on MSWindows
            #
            startupinfo = subprocess.STARTUPINFO()
            #startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            self.process = subprocess.Popen(cmd, stdin=stdin_arg, stdout=stdout, stderr=stderr, startupinfo=startupinfo, env=env, bufsize=bufsize, shell=shell)
        elif False:   # subprocess.jython:
            #
            # Launch from Jython
            #
            self.process = subprocess.Popen(cmd, stdin=stdin_arg, stdout=stdout, stderr=stderr, env=env, bufsize=bufsize, shell=shell)
        else:
            #
            # Launch on *nix
            #
            self.process = subprocess.Popen(cmd, stdin=stdin_arg, stdout=stdout, stderr=stderr, preexec_fn=os.setsid, env=env, bufsize=bufsize, shell=shell)

    def X__del__(self):
        """
        Cleanup temporary file descriptor and delete that file.
        """

        if False and self.process is not None:
            try:
                if self.process.poll() is None:
                    print "X",self.process.pid
                    self.kill()
            except OSError:
                #
                # It should be OK to ignore this exception.  Although poll() returns
                # None when the process is still active, there is a race condition
                # here.  Between running poll() and running kill() the process
                # may have terminated.
                #
                pass
        if self.process is not None:
            try:
                del self.process
            except:
                pass
        self.process = None

    def wait(self, timelimit=None):
        """
        Wait for the subprocess to terminate.  Terminate if a specified
        timelimit has passed.
        """
        if timelimit is None:
            self.process.communicate(input=self.stdin)
            return self.process.returncode
        else:
            #
            # Wait timelimit seconds and then force a termination
            #
            # Sleep every 1/10th of a second to avoid wasting CPU time
            #
            if timelimit <= 0:
                raise ValueError, "'timeout' must be a positive number"
            endtime = timer()+timelimit

            # This might be dangerous: we *could* deadlock if the input
            # is large...
            if self.stdin is not None:
                self.process.stdin.write(self.stdin)
            
            while timer() < endtime:
                status = self.process.poll()
                if status is not None:
                    return status
                time.sleep(0.1)
            #
            # Check one last time before killing the process
            #
            status = self.process.poll()
            if status is not None:
                return status
            #
            # If we're here, then kill the process and return an error
            # returncode.
            #
            try:
                self.kill()
                return -1
            except OSError:
                #
                # The process may have stopped before we called 'kill()'
                # so check the status one last time.
                #
                status = self.process.poll()
                if status is not None:
                    return status
                else:
                    raise OSError, "Could not kill process " + repr(self.process.pid)

    def stdout(self):
        return self.process.stdout

    def send_signal(self, sig):
        """
        Send a signal to a subprocess
        """
        os.signal(self.process,sig)

    def kill(self, sig=signal.SIGTERM):
        """
        Kill the subprocess and its children
        """
        kill_process(self.process, sig)
        del self.process
        self.process = None


if __name__ == "__main__": #pragma:nocover
    #GlobalData.debug=True
    print "Z"
    stime = timer()
    foo = run_command("./dummy", tee=True, timelimit=10)
    print "A"
    print "Ran for " + repr(timer()-stime) + " seconds"
    print foo
    sys.exit(0)

    if not subprocess.mswindows:
        foo = SubprocessMngr("ls *py")
        foo.wait()
        print ""

        foo = SubprocessMngr("ls *py", stdout=subprocess.PIPE)
        foo.wait()
        for line in foo.process.stdout:
            print line,
        print ""
        foo=None

        [rc,output] = run_command("ls *py")
        print output
        print ""

        [rc,output] = run_command("ls *py", outfile="tmp")
        INPUT=open("tmp",'r')
        for line in INPUT:
            print line,
        INPUT.close()
        print ""

        print "X"
        [rc,output] = run_command("python -c \"while True: print '.'\"",
                                  timelimit=2)
        print "Y"
        #[rc,output] = run_command("python -c \"while True: print '.'\"")
        [rc,output] = run_command("python -c \"while True: print '.'\"", verbose=False)
        print "Y-end"
    else:
        foo = SubprocessMngr("cmd /C \"dir\"")
        foo.wait()
        print ""

    print "Z"
    stime = timer()
    foo = run_command("python -c \"while True: pass\"", timelimit=10)
    print "A"
    print "Ran for " + repr(timer()-stime) + " seconds"


pyutilib.services.register_executable("valgrind")
pyutilib.services.register_executable("memmon")
