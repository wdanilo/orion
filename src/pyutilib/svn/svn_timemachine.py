#!/usr/bin/env python
#  _________________________________________________________________________
#
#  PyUtilib: A Python utility library.
#  Copyright (c) 2008 Sandia Corporation.
#  This software is distributed under the BSD License.
#  Under the terms of Contract DE-AC04-94AL85000 with Sandia Corporation,
#  the U.S. Government retains certain rights in this software.
#  _________________________________________________________________________
#
import os
import re
import sys

from datetime import datetime, timedelta
from subprocess import Popen, PIPE

from pyutilib.svn.repository import svn_info, svn_externals, SvnError


def checkout(path_list, date_str):
    target, url, rev = path_list.pop(0)

    # If the revision wasn't specified (i.e. fixed by the external
    # itself), then we need to determine the correct revision number
    # from the main date_str.
    if rev is None:
        # find the repo (the deep link may no longer exist) and get the rev
        tmp_url = url;
        while len(tmp_url):
            try:
                rev = svn_info(tmp_url, '{'+date_str+'}')['revision']
            except SvnError:
                pass
            if rev is not None:
                break
            try:
                tmp_url,junk = tmp_url.rsplit('/',1)
            except ValueError:
                tmp_url = ""
        if not tmp_url:
            raise SvnError( ("unable to determine repository revision number "
                             "for '%s' on %s" % (url, date_str) ) )

    # Check out the url to the target path, but DO NOT automatically
    # checkout the externals
    print "(INFO) Checking out %s at r%s to %s" % (url, rev, target)
    cmd = [ 'svn', 'co', '-r', str(rev), '--ignore-externals',
            url+'@'+str(rev), target ]
    #print ' '.join(cmd)
    p = Popen(cmd, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    if p.returncode:
        raise SvnError( "svn info returned error %i:\n%s" %
                        (p.returncode, stderr) )

    # Parse the repo and get any externals that still need to be checked
    # out.  Because we never change the working directory, we need to
    # prepend the current target path to the external path before pushing
    # the external onto the list of pending paths.
    print "(INFO) Parsing externals for %s" % (url)
    externals, svn15format = svn_externals(url, rev)
    while externals:
        tmp = externals.pop(0)
        path_list.append((target+'/'+tmp.path, tmp.url, tmp.revision))


#-----------------------------------------------------------------------
# MAIN SCRIPT
#

def main():
    # Check for sane usage.
    me = os.path.basename(sys.argv[0])
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print "Usage: %s {revision|date} repo_url [path]" % (me)
        print ""
        print "  revision : the revision number to warp back to"
        print "  date     : the date to warp back to (YYYY-MM-DD hh:mm:ss -TZ)"
        print "  repo_url : the repository url to check out"
        print "  path     : the destination path for the working copy"
        print ""
        sys.exit(1)

    rev_or_date = sys.argv[1]
    url = sys.argv[2]
    if len(sys.argv) > 3:
        target = sys.argv[3]
    else:
        target = url.rsplit('/',1)[1]

    # First, get the date that we will be using to interrogate the repository
    if re.match('^\d+$', rev_or_date):
        fields = svn_info(url, rev_or_date)['last changed date'] \
                 .split('(', 1)[0].strip().split(' ')

        # Because this is the time that the revision was actually committed,
        # we need to add a second to get the state immediately *after* the
        # commit.
        d = [int(x) for x in fields.pop(0).split('-')]
        f = []
        if len(fields):
            f = [int(x) for x in fields.pop(0).split(':')]
        while len(f) < 3:
            f.append(0)
        Date = datetime(d[0],d[1],d[2],f[0],f[1],f[2]) + timedelta(seconds=1)
        fields.insert(0, Date.isoformat(' '))
        date_str = ' '.join(fields)
    else:
        date_str = rev_or_date

    print "(INFO) checking out the repository as it existed on %s" % date_str

    # Do the actual checkout -- this is recursive, so it will pick up ALL
    # externals.
    path_list = [(target, url, None)]
    while path_list:
        checkout(path_list, date_str)

if __name__ == '__main__':
    main()
