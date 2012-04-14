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
from os import path
import re
import sys

from subprocess import Popen, PIPE
from pyutilib.svn.core import log, SvnError

dir_re = re.compile('\s+(\d+)\s+\S+\s+\w{3}\s+\d{2}\s+\S+\s+(\S+)')
externals_section_re = re.compile('^(\S+)\s+-(?:\s+(.*))?$')
proto = '(?:(?:svn|svn\+[sr]sh|file|https?)://)'
externals_14link_re = re.compile('^\s*((?!-r)\S+)\s+(?:-r\s*(\d+)\s+)?('+proto+'\S+)')
externals_15link_re = re.compile('^\s*(?:-r\s*(\d+)\s+)?((?:'+proto+'|(?:\.\.|\^)?/)\S+?)(?:\@(\d+))?\s+((?!'+proto+')\S+)')
log_revision_re = re.compile('^\s*r(\d+)')

# the list of subdirectories we will look for in a project
common_project_dirs = [ 'trunk', 'stable', 'tags', 'branches', 'releases',
                        'maintenance', 'snl' ]

# The subset of common_project_dirs that can be treated "normally" (as a
# collection of tags/branch subdirectories)
standard_subdirs = common_project_dirs[:]
standard_subdirs.remove('trunk')
standard_subdirs.remove('stable')


def svn_info(url, rev=None):
    info = {}
    try:
        is_int = int(rev) == rev
        if is_int:
            url += '@' + str(rev)
    except:
        pass
    cmd = ['svn', 'info', url]
    if rev:
        cmd.extend(['-r' + str(rev)])
    p = Popen(cmd, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    if p.returncode:
        raise SvnError( "svn info returned error %i:\n%s" %
                        (p.returncode, stderr) )
    for line in stdout.split('\n'):
        if line:
            key, val = line.split(':', 1)
            info[key.lower()] = val.strip()

    # special cases
    for x in ['revision', 'last changed rev']:
        if x in info:
            info[x] = int(info[x])
    return info


def svn_subdirs(url, subdir=None):
    dir = {}
    if subdir:
        url = url.rstrip('/') + '/' + subdir.lstrip('/')

    p = Popen(['svn', 'ls', '-v', url], stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    if p.returncode:
        raise SvnError( "svn ls returned error %i:\n%s" %
                        (p.returncode, stderr) )
    for line in stdout.split('\n'):
        g = dir_re.match(line)
        if not g:
            continue
        path = g.group(2).strip()
        if path[-1] != '/':
            raise SvnError("[internal] directory doesn't end with "
                           "/: our understanding of svn is wrong!")
        dir[path[0:-1]] = int(g.group(1))
    return dir


def svn_propget(property, url, rev=None):
    cmd = ['svn', 'propget']
    if type(property) in (list, tuple):
        cmd.extend(property)
    else:
        cmd.append(property)
    if rev:
        cmd.append(url + '@' + str(rev))
    else:
        cmd.append(url)
    log.debug(' '.join(cmd))
    p = Popen( cmd, stdout=PIPE, stderr=PIPE )
    stdout, stderr = p.communicate()
    if p.returncode:
        raise SvnError( "svn propget returned error %i:\n%s" %
                        (p.returncode, stderr) )
    return stdout.split('\n')


def svn_externals(url, rev=None):
    prop_data = svn_propget(['-R','svn:externals'], url, rev)
    svn15format = False
    externals = []
    srcdir = ''
    for line in prop_data:
        line = line.strip()
        g = externals_section_re.match(line)
        if g:
            assert g.group(1).startswith(url)
            srcdir = g.group(1)[len(url):].lstrip('/')
            if srcdir:
                srcdir = srcdir + '/'
            if g.group(2):
                line = g.group(2).strip()
            else:
                line = ""
        if line.startswith('#'):
            continue
        if len(line) == 0:
            continue
        g = externals_14link_re.match(line)
        if g:
            externals.append( External( srcdir+g.group(1), g.group(3),
                                        g.group(2) ) )
            continue
        g = externals_15link_re.match(line)
        if g:
            svn15format = True
            externals.append( External( srcdir+g.group(4), g.group(2),
                                        g.group(3) or g.group(1) ) )
            continue
        log.error("Unrecognized external format:\n     %s\n     found in %s" \
                  % (line, srcdir))

    return externals, svn15format


def svn_branch_created(url, rev=None):
    cmd = ['svn', 'log', '-q', '--stop-on-copy']
    if rev:
        cmd.append(url + '@' + str(rev))
    else:
        cmd.append(url)
    log.debug(' '.join(cmd))
    p = Popen( cmd, stdout=PIPE, stderr=PIPE )
    stdout, stderr = p.communicate()
    if p.returncode:
        raise SvnError( "svn log returned error %i:\n%s" %
                        (p.returncode, stderr) )
    for line in stdout.split('\n'):
        g = log_revision_re.match(line)
        if g:
            source_rev = g.group(1)
    return int(source_rev)


class External(object):
    def __init__(self, path, url, rev):
        self.path = path
        self.url = url
        self.revision = rev and int(rev) or None

    def __str__(self):
        return "%s: %s%s" % ( self.path, self.url, self.revision and
                              (" @ %s" % self.revision) or "" )


class Target(object):
    def __init__(self, project, name, rev):
        self.revision = 0
        self.create_rev = -1
        self.name = name
        self.url = project.url.rstrip('/') + '/' + name.lstrip('/')
        self.exernals = []
        self.svn15format = False
        self.update(rev)

    def __str__(self):
        ans = "%s @ %i : %s" % (self.name, self.revision, self.url)
        for e in self.externals:
            ans += "\n   %s" % str(e)
        return ans

    def update(self, new_rev):
        new_rev = int(new_rev)
        if self.revision == new_rev:
            return
        log.info("updating externals for target " + self.name)
        self.revision = new_rev
        self.create_rev = svn_branch_created(self.url)
        self.externals, self.svn15format = svn_externals(self.url)


class Project(object):
    def __init__(self, repo, path, dir):
        self.revision = dir['.']
        self.repo_url = repo.url
        self.url = repo.url.rstrip('/') + '/' + path.lstrip('/')
        # the project name is either the repo name or the subdirectory name...
        self.name = self.url.rstrip('/').split('/')[-1]
        self.targets = {}
        self.update(dir)

    def update(self, dir):
        old_targets = self.targets;
        self.targets = {}
        subdirs = dir.keys()

        log.info("updating project %s" % self.name)

        # Handle trunk... this is easy
        if 'trunk' in subdirs:
            self._record_target(old_targets, 'trunk', dir['trunk']);

        # "stable" is tricky: it can either be a copy of trunk, OR it
        # can be a collection of stable branches, we will assume that if
        # ALL subdirectories within stable either start or end with a
        # number, then the project supports multiple stable tags
        if 'stable' in subdirs:
            stable_dirs = svn_subdirs(self.url, 'stable')
            if len(stable_dirs) == 1: # 1 is the '.' directory!
                # default to multiple stable dirs if stable is empty
                multiple_stable = True
            else:
                ver_count = 0.0
                for d in stable_dirs.keys():
                    if d == '.':
                        continue
                    if d.strip('1234567890.') != d:
                        ver_count += 1

                common_count = 0.0
                if 'trunk' in subdirs:
                    trunk_dirs = svn_subdirs(self.url, 'trunk').keys()
                    for d in stable_dirs.keys():
                        if d == '.':
                            continue
                        if d in trunk_dirs:
                            common_count += 1

                total = float( len(stable_dirs) - 1 )
                if ( ver_count/total > 0.25 ) ^ ( common_count/total < 0.25 ):
                    log.warn("I am confused as to if stable is a branch "\
                             "or collection of branches; assuming a "\
                             "collection of branches")
                    multiple_stable = True
                else:
                    multiple_stable = bool( ver_count/len(stable_dirs) > 0.25 )
            if multiple_stable:
                for key, rev in stable_dirs.items():
                    if key == '.':
                        continue
                    self._record_target(old_targets, 'stable/'+key, rev)
            else:
                self._record_target(old_targets, 'stable', dir['stable'])

        # handle the other common "collections" of branch- or tag-like
        # constructs
        for d in standard_subdirs:
            if d in subdirs:
                for key, rev in svn_subdirs(self.url, d).items():
                    if key == '.':
                        continue
                    self._record_target(old_targets, d+'/'+key, rev)


    def _record_target(self, old, name, rev):
        if name in old:
            self.targets.setdefault(name, old[name]).update(rev)
        else:
            self.targets[name] = Target(self, name, rev)

    def __str__(self):
        ans = "Project: %s\nRevision: %i\nURL: %s\nTargets:\n" % \
              (self.name, self.revision, self.url)

        target_list = self.targets.keys()
        target_list.sort()
        for t in target_list:
            ans = ans + ( "   %s\n" %
                          ( str(self.targets[t]).replace('\n', '\n   ') ) )
        return ans


class Repository(object):
    def __init__(self, url, rev=None):
        info = svn_info(url, rev)
        if 'repository root' not in info:
            raise SvnError("ERROR: Specified repository url (%s) does "
                           "not appear to exist" % url)
        self.url = info['repository root']
        self.revision = 0
        self.projects = {}

    def update(self):
        log.info("updating repository %s" % self.url)
        info = svn_info(self.url)
        if self.url != info['repository root']:
            raise SvnError("ERROR: Specified repository url (%s) does "
                           "not match repository root (%s)" %
                           (self.url, info['Repository Root']))

        # duck out if nothing has changed
        if self.revision == info['revision']:
            return False
        self.revision = info['revision']

        old_projects = self.projects
        self.projects = {}
        potential_projects = ['']
        while potential_projects:
            target = potential_projects.pop()
            dir = svn_subdirs(self.url, target)
            subdirs = dir.keys()
            project_found = False
            for d in common_project_dirs:
                if d in subdirs:
                    project_found = True
                    self._record_project(old_projects, target, dir)
                    break
            if not project_found:
                subdirs.remove('.')
                potential_projects.extend([target+'/'+x for x in subdirs])

        # catch-all for repositories that don't honor trunk/tags/etc
        if len(self.projects) == 0:
            self._record_project(old_projects, '', svn_subdirs(self.url,''))

        return True

    def _record_project(self, old, name, dir):
        name = name.strip('/')
        if name in old:
            self.projects.setdefault(name, old[name]).update(dir)
        else:
            self.projects[name] = Project(self, name, dir)


    def __str__(self):
        ans = "Repository: %s\nRevision: %i\nProjects:\n" % \
              (self.url, self.revision)

        project_list = self.projects.keys()
        project_list.sort()
        for p in project_list:
            ans = ans + ( "   %s\n" %
                          ( str(self.projects[p]).replace('\n', '\n   ') ) )
        return ans


if __name__ == "__main__":
    # Check for sane usage.
    if len(sys.argv) != 2:
        sys.stderr.write("Usage: %s REPOS_PATH\n"
                         % (path.basename(sys.argv[0])))
        sys.exit(1)

    r = Repository(sys.argv[1])
    r.update()
    print r
