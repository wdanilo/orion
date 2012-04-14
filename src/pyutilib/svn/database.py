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
import sys
import yaml

from pyutilib.svn.core import log
from pyutilib.svn.repository import Repository, SvnError

class DatabaseError(Exception):
    """Exception raised accessing Repository Database cache."""

class RepositoryDatabase(object):

    def __init__(self, filename=None):
        self.repos = {}
        if filename:
            self.cache_file = filename
        else:
            self.cache_file = RepositoryDatabase.default_db()

    @staticmethod
    def default_db():
        return os.environ["HOME"]+os.sep+".pyutilib.svn" + os.sep+'cache.yaml'

    def load(self):
        if not os.path.exists( self.cache_file ):
            raise DatabaseError("Repository database file %s does not exist" % \
                                 self.cache_file)
        log.info("Reading repository database from '%s'" % self.cache_file)
        INPUT=open(self.cache_file)
        self.repos = yaml.load(INPUT)
        INPUT.close()

    def save(self, stream=None):
        dir, fname = os.path.split(self.cache_file)
        if not fname:
            raise DatabaseError( "Cache file (%s) specifies a directory!" % \
                              self.cache_file )
        if dir and not os.path.exists( dir ):
            os.mkdir( dir )
        if stream is None:
            log.info("Writing repository database to '%s'" % self.cache_file)
            OUTPUT=open(self.cache_file, 'w')
        else:
            OUTPUT=stream

        print >>OUTPUT, "# All svn repositories added to this database"
        yaml.dump(self.repos, OUTPUT, default_flow_style=False,
                  explicit_start=True, explicit_end=True)

        if stream is None:
            OUTPUT.close()

    def add(self, url):
        try:
            r = Repository(url)
        except SvnError, e:
            log.error("adding repository (%s) failed:\n%s" % ( url, str(e) ))
            raise
        if r.url in self.repos:
            raise DatabaseError( "Repository (%s) already in database as %s"
                              % ( url, r.url ) )
        r.update()
        self.repos[r.url] = r
        return r

    def remove(self, url):
        # If the user provided a valid repo URL, delete it and return.
        try:
            del self.repos[url]
            return
        except KeyError:
            pass

        # Hopefully, this repo still exists: try and resolve it.
        try:
            r = Repository(url)
        except SvnError, e:
            log.error("deleting repository (%s) failed:\n%s" % ( url, str(e) ))
            raise
        try:
            del self.repos[r.url]
        except KeyError:
            raise DatabaseError( "Repository (%s) not in database" % url )

    def update(self, repo=None):
        updated = False
        for r in self.get_repositories(repo):
            updated |= r.update()
        return updated

    def rescan(self, repo=None):
        for r in self.get_repositories(repo):
            r.revision = 0;
            r.projects = {}
            r.update()

    def get_repositories(self, repo):
        if repo is None:
            return self.repos.values()
        else:
            if repo is Repository:
                return [ repo ]
            elif repo in self.repos:
                return [ self.repos[repo] ]
            else:
                repos = []
                for name, r in self.repos.iterkeys():
                    if re.search(repo, name):
                        repos.append(r)
                return repos

    def __str__(self):
        ans = ""
        repo_list = self.repos.keys()
        repo_list.sort()
        for r in repo_list:
            ans = ans + str(self.repos[r])
        return ans


if __name__ == "__main__":
    me = os.path.basename(sys.argv[0])
    # Check for sane usage.
    if len(sys.argv) < 2:
        print "Usage: %s command [options]" % (me)
        print ""
        print "Available commands:"
        print "   add"
        print "   remove"
        print "   update"
        print "   rescan"
        print "   print"
        print ""
        sys.exit(1)

    db = RepositoryDatabase()
    try:
        db.load()
    except DatabaseError:
        log.info("cache file DNE; initializing empty database")

    cmd = sys.argv[1]
    if cmd == "add":
        if len(sys.argv) != 3:
            print "Usage: %s add repository_url" % (me)
            sys.exit(1)
        db.add(sys.argv[2])
        db.save()
    if cmd == "remove":
        if len(sys.argv) != 3:
            print "Usage: %s remove repository_url" % (me)
            sys.exit(1)
        db.remove(sys.argv[2])
        db.save()
    if cmd == "update":
        if len(sys.argv) != 2:
            print "Usage: %s update" % (me)
            sys.exit(1)
        db.update()
        db.save()
    if cmd == "rescan":
        if len(sys.argv) != 2:
            print "Usage: %s rescan" % (me)
            sys.exit(1)
        db.rescan()
        db.save()
    if cmd == "print":
        if len(sys.argv) != 2:
            print "Usage: %s print" % (me)
            sys.exit(1)
        print db
    if cmd == "list":
        if len(sys.argv) != 3:
            print "Usage: %s list <component>" % (me)
            sys.exit(1)
        if sys.argv[2] == 'repos':
            repos = db.repos.keys()
            repos.sort()
            for r in repos:
                print r
