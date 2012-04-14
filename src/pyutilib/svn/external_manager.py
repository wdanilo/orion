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
import yaml
from copy import deepcopy
from pyutilib.svn.core import log, SvnError, VerifySvnVersion
from pyutilib.svn.repository import Repository, svn_info, svn_externals, \
     svn_propget, externals_14link_re, externals_15link_re
from pyutilib.svn.database import DatabaseError, RepositoryDatabase
from subprocess import Popen, PIPE

class ExternalError(Exception):
    """Exception raised due to tracing error."""

def clean_url(a):
    return '://'.join([re.sub('//+','/',x) for x in a.strip('/').split('://')])

illegal_characters = "(){}[]\\ \t\n"


class ResolvedRepo(object):
    def __init__(self, repo):
        self.raw     = repo
        self.url     = repo.url
        self.rev     = repo.revision
        self.projects = {} # map of Project name -> ResolvedProject

class ResolvedProject(object):
    def __init__(self, project, repo):
        self.raw     = project
        self.name    = project.name
        self.url     = project.url
        self.rev     = project.revision
        self.repo    = repo
        self.targets = {} # map of Target name -> ResolvedTarget

class ResolvedTarget(object):
    def __init__(self, target, project):
        self.raw       = target
        self.name      = target.name
        self.url       = target.url
        self.rev       = target.revision
        self.project   = project
        self.externals = {} # map of external.path -> ResolvedExternal

    def __str__(self):
        return self.project.name + " % " + str(self.name)

class ResolvedExternal(object):
    def __init__(self, raw, target, url, deep):
        self.raw      = raw
        self.url      = clean_url(url + '/' + deep)
        self.rev      = raw.revision
        self.path     = raw.path
        self.target   = target
        if target is None:
            self.deep_ref = None
        else:
            self.deep_ref = deep

class Description_External(object):
    def __init__(self, path, link=None, project=None):
        if not ( bool(link is None) ^ bool(project is None) ):
            raise ExternalError("Description_External: cannot specify "
                                "both link and project")
        self.path = path
        self.link = link
        self.project = project
        self.target = None
        self.deep_ref = None
        self.rev = None

    def name(self):
        return self.project is not None and self.project or self.link

    def url(self, em, repo):
        if self.link is not None:
            a = self.link
        else:
            p = em.get_project(self.project, repo)
            if p is None:
                log.warning("Unable to uniquely identify project %s" %
                            self.project)
                a = self.project + '/' + self.target
            else:
                a = p.url + '/' + self.target
        return clean_url(a + '/' + (self.deep_ref or ""))

    def __str__(self):
        if self.link is not None:
            s = self.link
        else:
            s = self.project
            if self.target is not None:
                s += " % " + self.target
            if self.deep_ref is not None:
                s += " > " + self.deep_ref
        if self.rev is not None:
            s += " @ " + str(self.rev)
        return s.strip()

    @staticmethod
    def parse_from(path, info, em, repo):
        seps = {}
        for sep in ['%', '>', '@']:
            i = info.find(sep)
            if i >= 0:
                seps[i] = sep
        rev = deep = target = None
        for index, sep in sorted(seps.items(), reverse=True):
            fields = info.split(sep)
            if len(fields) > 2:
                raise ExternalError("ERROR: bad external syntax")
            if sep == '@':
                rev = int(fields[1])
            elif sep == '>':
                deep = fields[1].strip()
            elif sep == '%':
                target = fields[1].strip()
            info = fields[0].strip()
        info = info.strip()
        if len(info) == 0 or em.get_project(info, repo) is not None:
            
            e = Description_External(path, project=info)
        else:
            e = Description_External(path, link=info)
        e.rev = rev
        e.deep_ref = deep
        e.target = target
        return e

class Description_Retarget(object):
    def __init__(self, target, rev=None):
        self.target = target
        self.rev = rev

    def __eq__(this, that):
        return that and this.target == that.target and this.rev == that.rev

    def __str__(self):
        if self.target:
            s = self.target
        else:
            s = ''
        if self.rev is not None:
            s += " @ " + str(self.rev)
        return s.strip()

    @staticmethod
    def parse_from(path, info):
        fields = info.split('@')
        if len(fields) > 2:
            raise ExternalError("ERROR: bad retarget syntax")
        return Description_Retarget( fields[0].strip(),
                                     len(fields)>1 and int(fields[1]) or None )

class Description_Inherit(object):
    def __init__(self, target, project=None):
        self.target = target
        self.project = project

    def __eq__(this, that):
        return that \
            and this.target == that.target \
            and this.project == that.project

    def __str__(self):
        if self.project is not None:
            s = self.project + " % " + self.target
        else:
            s = self.target
        return s.strip()

    @staticmethod
    def parse_from(info):
        fields = info.split('%')
        if len(fields) > 2:
            raise ExternalError("ERROR: bad inherit syntax")
        if len(fields) == 1:
            fields.insert(0,None)
        else:
            fields[0] = fields[0].strip()
        return Description_Inherit( fields[1].strip(), fields[0] )

url_re = re.compile('([^/]+://)?(.*)')

class Status:
    ok          = ''
    aliased_url = '~'
    excluded    = '>'
    non_target  = '?'
    dne_in_head = '-'
    broken      = 'X'
    not_pegged  = 'F'
    out_of_date = '<'

    @staticmethod
    def print_key():
        print """Key to integrity error codes:
  > : external points to a repository excluded from analysis by configuration
  ~ : external references target through an alias (e.g. svn+ssh instead of https)
  ? : external points to a location not affiliated with a known target
  X : external is broken and unresolvable
  - : external points to a valid pegged location that does not exist in HEAD
  F : external is floating (not pegged), but referenced through a pegged target
  < : external is pegged at a revision earlier than HEAD
"""


class ExternalManager(object):
    def __init__(self, config=None):
        self.all_repos    = [] # List of ResolvedRepo
        self.all_targets  = {} # map of target url -> ResolvedTarget
        self.all_projects = {} # map of project url -> ResolvedProject
        self.projects     = {} # map of project name -> ResolvedProject;
            # could be None if multiple projects by the same name and no
            # PromaryProject is declared.
            
        self.config       = {}

        # Path to the repository database cache file
        self.config['repo_db'] = None # <- use default db

        # list of URLs to exclude (treat as truly external and do not
        # add them to the repository database)
        self.config['exclude'] = []

        # Sometimes the same repository can be accessed through multiple
        # URLs.  This tells which URLs can be treated as an alias of the
        # "real" URL.  Each entry in the list is a (alias URL, real URL)
        # tuples.
        self.config['aliases']          = []

        # Sometimes there are multiple *different* projects that use the
        # same name.  This tells the ExternalManager which one we will
        # usually use (and can be referenced through the project name).
        # All non-primary projects will have to use full URL references.
        #
        # This is a map of "project_name -> repo_URL:project_name".
        # Note: if the repository *is* the project (that is, has a
        # top-level trunk directory), the map value *must* end with a
        # ":" (to define a "" project name)
        self.config['primary_projects'] = {}

        # The list of default targets that should have pegged revision numbers
        self.config['pegged_targets']   = ['releases', 'tags', 'maintenance']

        # directory for instantiating changeset
        self.config['workingdir']       = 'svnpm-tmp'

        if not config:
            config = ExternalManager.default_config()
        if isinstance(config, dict):
            self.config.update(config)
        elif os.path.exists(config):
            self.load_config(config)

        self.db = RepositoryDatabase(self.config['repo_db'])
        try:
            self.db.load()
        except DatabaseError:
            log.info("Database file DNE; initializing empty database")

    @staticmethod
    def default_config():
        return os.environ["HOME"]+os.sep+".pyutilib.svn"+os.sep+'config.yaml'

    def get_repository(self, repo_name):
        for r in self.all_repos:
            if r.url == repo_name:
                return r
        if repo_name in self.all_projects:
            return self.all_projects[repo_name].repo
        if repo_name in self.projects:
            return self.projects[repo_name].repo
        return None

    def get_project(self, project_name, repo=None):
        if project_name in self.all_projects:
            return self.all_projects[project_name]
        elif project_name in self.projects:
            proj = self.projects[project_name]
            if proj is None and repo is not None:
                if project_name in repo.projects:
                    if repo.projects[project_name] is not None:
                        return repo.projects[project_name]
            #log.warning("Looking up project '%s', but there are multiple "
            #            "projects with that name." % (project_name,))
            return proj
        else:
            return None

    def load_config(self, fname):
        if not os.path.exists( fname ):
            raise ExternalError("Configuration file %s does not exist" % fname)
        log.info("Reading configuration from '%s'" % fname)
        INPUT=open(fname)
        config = yaml.load(INPUT)
        INPUT.close()
        self.config.update(config)

    def update(self):
        """Update all repository caches.  Also, look for any externals
        pointing to new repositories and add those repositories to the
        cache."""
        def _locate_external_repo(self, external, known, pending):
            url = external.url
            if not url:
                raise ExternalError( "bad external: %s" % str(external) )
            for alias, main in self.config['aliases']:
                if url.startswith(alias):
                    url = url.replace(alias, main, 1)
            for e in self.config['exclude']:
                if url.startswith(e):
                    return
            for r in known:
                if url.startswith(r):
                    return

            # Now it is likely that this is a url to a new repo --
            # figure out what the repo root url is
            protocol, url = url_re.match(url).groups()
            while len(url):
                try:
                    tmp = Repository((protocol or "")+url, external.revision)
                    if tmp.url not in known:
                        log.info("external (%s)\nreferences new repo %s" % \
                                 ( external.url, tmp.url ))
                        known.append(tmp.url)
                        new_repo = self.db.add(tmp.url)
                        pending.insert(0, new_repo)

                        # We save things as we go so aborting early
                        # doesn't lose work
                        self.db.save()
                    break
                except SvnError:
                    try:
                        (url,junk) = url.rsplit('/',1)
                    except ValueError:
                        return # it's OK not to find a repo --
                               # broken links will be handled later
        # { end def _validate_external_repo() }

        # First, update all the repos we know about
        if self.db.update():
            # We save things as we go so aborting early doesn't lose work
            self.db.save()

        # We now need to make sure we have loaded and indexed all the
        # repositories we will need
        known_repos = self.db.repos.keys()
        pending_repos = self.db.repos.values()
        while pending_repos:
            repo = pending_repos.pop()
            for project in repo.projects.itervalues():
                for target in project.targets.itervalues():
                    for external in target.externals:
                        _locate_external_repo\
                            ( self, external, known_repos, pending_repos )


    def resolve_targets(self):
        """Converts the simple tree (DAG) representation of the
        repository managed by the repo database into a fully
        cross-linked repository graph."""

        # Pass 1: resolve all the projects and targets
        for repo in self.db.repos.itervalues():
            r = ResolvedRepo(repo)
            self.all_repos.append(r)
            for project in repo.projects.itervalues():
                if project.name in self.projects and \
                       project.name not in self.config['primary_projects']:
                    tmp = self.projects[project.name]
                    log.warning("duplicate project (%s)\n[new ] %s\n[main] %s"
                                % ( project.name, project.url,
                                    tmp and tmp.url or None ))
                    self.projects[project.name] = None
                p = self.all_projects[project.url] = ResolvedProject(project,r)
                self.projects.setdefault(project.name, p)
                r.projects.setdefault(project.name, p)
                for target in project.targets.itervalues():
                    if target.url in self.all_targets:
                        raise ExternalError( "(ERROR): duplicate target URL "
                                             "found (%s)" % target.url )
                    self.all_targets[target.url] \
                            = p.targets[target.name] \
                            = ResolvedTarget(target, p)


        # sanity check the duplicate project names, and override the
        # name resolution
        for name, project in self.config['primary_projects'].iteritems():
            (repo, proj) = project.rsplit(':', 1)
            if repo not in self.db.repos:
                log.error("primary_projects: unknown repository (%s)" % repo)
            elif proj not in self.db.repos[repo].projects:
                log.error("primary_projects: unknown project (%s)" % project)
            else:
                self.projects[name] =  self.all_projects[ \
                    self.db.repos[repo].projects[proj].url ]

        # Pass 2: try and resolve all the external urls to Target objects
        for target in self.all_targets.itervalues():
            for external in target.raw.externals:
                url = external.url
                for alias, main in self.config['aliases']:
                    if url.startswith(alias):
                        url = url.replace(alias, main, 1)
                deepRef = ''
                while len(url):
                    t = self.all_targets.get(url, None)
                    if t is not None:
                        break
                    if url in self.db.repos:
                        break
                    try:
                        (url, tmp) = url.rsplit('/',1)
                    except ValueError:
                        tmp = url
                        url = ""
                    deepRef = tmp + '/' + deepRef
                # ...We won't complain about broken externals (yet)
                #if e is None:
                #    raise ExternalError( "target (%s) not found" %
                #                         str(e) )
                target.externals[external.path] = \
                    ResolvedExternal(external, t, url, deepRef)


    def check_integrity(self, repo=None, project=None, key=None):
        """Perform a basic integrity check on the repositories.  This
        will identify common errors like:
          - broken externals.
          - externals that point through an aliased URL.
          - externals that point to an excluded URL.
          - externals that point to a location other than a known
            project target.
          - pegged externals that work but point to locations that no
            longer exist at the HEAD."""

        def _integrity_error(target, external, error):
            return "%s  %-15s : %-25s (%s)" % \
                  ( error, target.project.name,
                    target.name, str(external.raw) )

        if repo is not None and project is not None:
            if repo == project.repo:
                repo = None
            else:
                raise ExternalError("(ERROR) check_integrity: cannot specify "
                                    "both repo and project")
        if key:
            Status.print_key()

        if project is not None:
            projects = [ project ]
        elif repo is not None:
            projects = sorted( repo.projects.values(),
                               cmp=lambda x,y: cmp(x.url, y.url) )
        else:
            projects = sorted( self.all_projects.values(),
                               cmp=lambda x,y: cmp(x.url, y.url) )

        for p in projects:
            targets = sorted( p.targets.values(),
                              cmp=lambda x,y: cmp(x.name, y.name) )
            for t in targets:
                for e in t.externals.itervalues():
                    error, rev = self._resolve_external(e)
                    if error:
                        print _integrity_error(t, e, error)


    def check_pegged_target(self, target, peg=None, parent=''):
        """Utility function that performs the check_pegged() on a
        single target."""

        def _peg_error(path, e, error, rev=None):
            return "%s  %-30s %-8s: %s%s" % \
                   ( error, path, rev and (": %s" % rev) or "", e.url,
                     e.rev and (" @ %s" % e.rev) or "" )

        if peg is None:
            for x in self.config['pegged_targets']:
                if target.name.startswith(x):
                    peg = target.rev
                    break

        ans = []
        for e in target.externals.itervalues():
            if parent and e.path:
                path = parent + '/' + e.path
            else:
                path = parent + e.path

            error, rev = self._resolve_external(e)
            if rev and e.rev and e.rev < rev:
                ans.append( _peg_error(path, e, Status.out_of_date, rev) )
            elif peg is not None:
                if e.rev is None:
                    ans.append( _peg_error(path, e, Status.not_pegged) )
                elif error and error != Status.dne_in_head:
                    ans.append( _peg_error(path, e, error) )
            elif error and error != Status.dne_in_head:
                ans.append( _peg_error(path, e, error) )

            if e.target is not None:
                ans.extend(self.check_pegged_target(e.target, e.rev, path))
        return ans

    def check_pegged(self, repo=None, project=None, key=None):
        """Perform a check for pegged externals in the repositories.  In
        addition to basic integrity errors identified by
        check_integrity, this will identify errors like:

          - externals that are pegged to revisions older than HEAD for
            that location.
          - externals that should be pegged, but are not."""

        if repo is not None and project is not None:
            if repo == project.repo:
                repo = None
            else:
                raise ExternalError("(ERROR) check_pegged: cannot specify "
                                    "both repo and project")
        if key:
            Status.print_key()

        if project is not None:
            print_header = True
            targets = sorted( project.targets.values(),
                              cmp=lambda x,y: cmp(x.name, y.name) )
            for t in targets:
                ans = self.check_pegged_target(t)
                if len(ans):
                    if print_header:
                        print project.url
                        print_header = False
                    print "   %s" % t.name
                    print "      %s" % ( '\n      '.join(ans) )
            return


        repos = repo is None and self.all_repos or [ repo ]
        for repo in repos:
            for p in sorted( repo.projects.values(),
                             cmp=lambda x,y: cmp(x.url, y.url) ):
                print_header = True
                for t in sorted( p.targets.values(),
                                 cmp=lambda x,y: cmp(x.name, y.name) ):
                    ans = self.check_pegged_target(t)
                    if len(ans):
                        if print_header:
                            print p.url
                            print_header = False
                        print "   %s" % t.name
                        print "      %s" % ( '\n      '.join(ans) )

    def print_status(self, repo=None, project=None):
        """Print the status of the project/repository."""

        if repo is not None and project is not None:
            if repo == project.repo:
                repo = None
            else:
                raise ExternalError("(ERROR) print_status: cannot specify "
                                    "both repo and project")

        maxRev = 0
        maxLen = 0

        if project is not None:
            print_header = True
            targets = sorted( project.targets.values(),
                              cmp=lambda x,y: cmp(x.name, y.name) )
            for t in targets:
                maxRev = max(maxRev, t.rev)
                maxLen = max(maxLen, len(t.name))
            field = "   %%-%is %%1s%%s" % maxLen
            for t in targets:
                if print_header:
                    print project.url
                    print_header = False
                print field % ( t.name, t.rev==maxRev and '*' or '', t.rev )
            return

        repos = repo is None and self.all_repos or [ repo ]
        for repo in repos:
            for p in sorted( repo.projects.values(),
                             cmp=lambda x,y: cmp(x.url, y.url) ):
                maxRev = maxLen = 0
                for t in p.targets.itervalues():
                    maxRev = max(maxRev, t.rev)
                    maxLen = max(maxLen, len(t.name))
                field = "   %%-%is\t%%1s%%s" % maxLen
                print_header = True
                for t in sorted( p.targets.values(),
                                 cmp=lambda x,y: cmp(x.name, y.name) ):
                    if print_header:
                        print p.url
                        print_header = False
                    print field % ( t.name, t.rev==maxRev and '*' or '', t.rev )

    def find_references(self, url):
        ans = []
        for tUrl, t in self.all_targets.iteritems():
            for e in t.externals.itervalues():
                if e.url.startswith(url):
                    ans.append((t.project.name, t.name))
                    break
        return ans

    def reference_map(self):
        ans = {}
        for tUrl, t in self.all_targets.iteritems():
            refs = self.find_references(tUrl)
            if refs:
                ans[t] = refs
        return ans

    def load_repo_definition(self, definition_fname):
        if not os.path.exists( definition_fname ):
            raise ExternalError("Repository definition file %s does not exist" %
                                definition_fname)
        log.info("Reading repository definition from '%s'" % definition_fname)
        FILE = open(definition_fname)
        defn = yaml.load(FILE)
        FILE.close()
        self.expand_repo_definition(defn)
        return defn

    def generate_repo_definition(self, repo=None, proj=None):
        """Generate a definition dictionary for a single repository,
        based on the current status of that repository.  This attempts
        to identify and leverage common inheritance patterns used in
        repositories in order to reduce the size and complexity of the
        definition."""

        def _reduce_pegged(target):
            pass
            #targetExternals = target.get('externals', {})
            #for eName, e in targetExternals.iteritems():
            #    if e.target:
            #        retarget = Description_Retarget(e.target, e.rev)
            #        if target.setdefault('retarget', {}).setdefault \
            #                ( e.name(), retarget ) == retarget:
            #            e.target = None
            #            e.rev = None
        # { END def _reduce_pegged() }

        def _reduce_inherited(trunkExternals, target):
            modified = False
            targetExternals = target.get('externals', {})
            for eName, e in trunkExternals.iteritems():
                tmpE = targetExternals.get(eName, None)
                if tmpE is None or tmpE.name() != e.name() or \
                        tmpE.deep_ref != e.deep_ref:
                    target.setdefault('remove',[]).append(eName)
                    modified = True
                elif tmpE.target != e.target or tmpE.rev != e.rev:
                    retarget = Description_Retarget(tmpE.target, tmpE.rev)
                    if target.setdefault('retarget', {}).setdefault \
                            ( tmpE.name(), retarget ) == retarget:
                        del targetExternals[eName]
                        modified = True
                else:
                    del targetExternals[eName]

            if modified:
                target['inherit'] = [ Description_Inherit('trunk') ]
        # { END def _reduce_inherited() }


        if not ((repo is None) ^ (proj is None)):
            raise ExternalError("ERROR: cannot specify both repo and proj")

        if repo is not None:
            projects = repo.projects.keys()
        else:
            projects = [ proj.name ]
            repo = proj.repo

        ans = { '__repo__' : repo.url }
        for pName in projects:
            p = {}
            ans[pName] = p
            # generate the definition of each target in the project
            for tName, target in repo.projects[pName].targets.iteritems():
                if not target.externals:
                    p[tName] = {}
                    continue

                t = {'externals':{}}
                p[tName] = t
                for e in target.externals.itervalues():
                    if e.target is None or \
                           self.projects.get(e.target.project.name) is None:
                        ref = Description_External(e.path, link=e.url)
                    else:
                        ref = Description_External \
                            (e.path, project=e.target.project.name)
                        ref.target = e.target.name
                    if e.deep_ref:
                        ref.deep_ref = e.deep_ref.strip('/')
                        if len(ref.deep_ref) == 0:
                            ref.deep_ref = None
                    if e.rev:
                        ref.rev = e.rev
                    t['externals'][e.path] = ref

            # attempt to reduce the definition to something closer to
            # what a user would write
            if 'trunk' in p:
                trunk = p['trunk']
                trunkExternals = trunk.get('externals', {})
                for tName, target in p.iteritems():
                    if tName == 'trunk':
                        continue
                    pegged = False
                    for pegDir in self.config['pegged_targets']:
                        if tName.startswith(pegDir):
                            pegged = True
                    if pegged:
                        _reduce_pegged(target)
                    else:
                        _reduce_inherited(trunkExternals, target)

        return ans

    def collapse_repo_definition(self, rd):
        """Collapse a repository definition dictionary down to a format
        that generates more human-readable and editable YAML."""

        for pName, p in rd.iteritems():
            if pName == '__repo__':
                continue
            for tName, t in p.iteritems():
                eDict = t.setdefault('externals', {})
                for eName, e in eDict.iteritems():
                    if isinstance(e, Description_External):
                        eDict[eName] = str(e)
                if not len(eDict):
                    del t['externals']

                eDict = t.setdefault('retarget', {})
                for eName, e in eDict.iteritems():
                    if isinstance(e, Description_Retarget):
                        eDict[eName] = str(e)
                if not len(eDict):
                    del t['retarget']

                inherit = t.setdefault('inherit', [])
                for i in range(len(inherit)):
                    if isinstance(inherit[i], Description_Inherit):
                        inherit[i] = str(inherit[i])
                if not len(inherit):
                    del t['inherit']

                branch = t.setdefault('branched-from', "")
                if isinstance(branch, Description_Inherit):
                    t['branched-from'] = branch = str(branch)
                if not branch:
                    del t['branched-from']

                if 'finalized' in t:
                    del t['finalized']
                if 'source' in t:
                    del t['source']
        return rd

    def expand_repo_definition(self, rd):
        """Expand a repository definition dictionary that was just
        loaded from YAML to the native form."""

        repo = rd.get('__repo__', None)
        if repo:
            repo = self.get_repository(repo)
        for pName, p in rd.iteritems():
            if pName == '__repo__':
                continue
            for tName, t in p.items():
                if not t:
                    t = p[tName] = {}
                    continue

                eDict = t.get('externals') or {}
                for eName, e in eDict.items():
                    if isinstance(e, str):
                        eDict[eName] = Description_External.parse_from(
                            eName, e, self, repo )
                t['externals'] = eDict

                eDict = t.get('retarget') or {}
                for eName, e in eDict.items():
                    if isinstance(e, str):
                        eDict[eName] = Description_Retarget.parse_from(eName, e)
                t['retarget'] = eDict

                inherit = t.get('inherit') or []
                for i in range(len(inherit)):
                    if inherit[i] and isinstance(inherit[i], str):
                        inherit[i] = Description_Inherit.parse_from(inherit[i])
                t['inherit'] = inherit

                branch = t.get('branched-from') or None
                if isinstance(branch, str):
                    if branch:
                        branch = Description_Inherit.parse_from(branch)
                    else:
                        branch = None
                t['branched-from'] = branch

        return rd

    def finalize_repo_definition(self, rd):
        def _finalize_external_list(projects, rd, ans):
            project = projects.pop()
            src = rd.get(project[0],{}).get(project[1], None)
            if src is None:
                # Target miss. Throw an exception?
                log.warning("Target miss! (%s %% %s)" % project)
                return
            dest = ans.setdefault(project[0],{}).setdefault(project[1], {})
            if dest.get('finalized', False):
                # Already processed
                return
            # Check to make sure the project(s) we inherit from are processed
            inherit = src.get('inherit', [])
            base = []
            for i in inherit:
                b = ans.get(i.project or project[0],{}).get(i.target,{})
                if not b.get('finalized', False):
                    projects.append(project)
                    projects.append((i.project or project[0], i.target))
                    return
                base.append(b)

            branch = src.get('branched-from',None)
            if len(inherit) and branch is not None:
                raise Exception("Cannot have both 'inherit' and "
                                "'branched-from' in target definition")

            dest['inherit'] = inherit
            if len(inherit):
                dest['source'] = inherit
            elif branch is not None:
                dest['source'] = [ branch ]
            else:
                dest['source'] = []
            dest['externals'] = {}
            dest['retarget'] = {}
            for b in base:
                dest['externals'].update( deepcopy(b.get('externals', {})) )
                dest['retarget'].update( deepcopy(b.get('retarget', {})) )
            for remove in src.get('remove', []):
                dest['externals'].pop(remove, 0)
            for path, external in src.get('externals', {}).iteritems():
                dest['externals'][path] = deepcopy(external)
                if not external.target:
                    dest['externals'][path].target = project[1]
            for path, retarget in src.get('retarget', {}).iteritems():
                dest['retarget'][path] = deepcopy(retarget)
            dest['finalized'] = True
        # END def _finalize_external_list

        ans = {}
        projects = []
        for pName, p in rd.iteritems():
            if pName == '__repo__':
                ans[pName] = p
                continue
            projects.extend([(pName, tName) for tName in p.iterkeys()])
        while projects:
            _finalize_external_list(projects, rd, ans)

        # Expand the retargeted externals
        for pName, p in ans.iteritems():
            if pName == '__repo__':
                continue
            for tName, t in p.iteritems():
                retarget = t.get('retarget', {})
                for eName, e in t.get('externals', {}).iteritems():
                    if e.link:
                        continue
                    if e.project:
                        rt = retarget.get(e.project, None)
                        if rt is not None:
                            e.target = rt.target
                            e.rev = rt.rev
                    if not e.target:
                        e.target = tName
        return ans


    def generate_changeset_from_definition(self, defn):
        repo = None
        for r in self.all_repos:
            if defn.get('__repo__') == r.url:
                repo = r
                break
        if repo is None:
            raise ExternalError("Cannot identify repository that "
                                "matches definition")

        changeset = { 'add' : [], 'del' : [], 'mod' : {}, 'repo' : repo }
        pNames = sorted(set(defn.iterkeys()).union(repo.projects.keys()))
        for pName in pNames:
            if pName == '__repo__':
                continue
            p = repo.projects.get(pName, None)
            dp = defn.get(pName, None)
            if p is None:
                # inserted
                changeset['add'].append((pName, None))
                continue
            if dp is None:
                # deleted
                changeset['del'].append((p, None))
                continue
            # validate each target
            tNames = sorted(set(dp.iterkeys()).union(p.targets.keys()))
            for tName in tNames:
                t = p.targets.get(tName, None)
                dt = dp.get(tName, None)
                if t is None:
                    # inserted
                    changeset['add'].append((p, tName))
                    continue
                if dt is None:
                    # deleted
                    changeset['del'].append((p, t))
                    continue
                # validate each external
                tPrinted = False
                eNames = sorted( set(t.externals.iterkeys()).union \
                                 ( dt.get('externals',{}).keys() ) )
                for eName in eNames:
                    e = t.externals.get(eName)
                    de = (dt.get('externals') or {}).get(eName)
                    if e is None:
                        # inserted
                        changeset['mod'].setdefault(t, []).append((None, de))
                    elif de is None:
                        # deleted
                        changeset['mod'].setdefault(t, []).append((e, None))
                    elif e.url != de.url(self, repo) or e.rev != de.rev:
                        # changed
                        changeset['mod'].setdefault(t, []).append((e, de))
        return changeset

    def print_changeset(self, changeset):
        repo = changeset['repo']
        for target in changeset['add']:
            if target[1] is None:
                print "A %s" % target[0]
            else:
                print "A %s %% %s" % (target[0].name, target[1])
        for target in changeset['del']:
            print "D %s" % ( target[1] and target[1] or target[0].name )
        for target in sorted( changeset['mod'].iteritems(),
                              cmp=lambda x,y: cmp(str(x[0]), str(y[0])) ):
            print "  %s" % target[0]
            for e in target[1]:
                if e[0] is not None:
                    print "-     %s: %s @ %s" % (e[0].path, e[0].url, e[0].rev)
                if e[1] is not None:
                    print "+     %s: %s @ %s" % \
                          (e[1].path, e[1].url(self, repo), e[1].rev)


    def implement_changeset(self, changeset, defn):
        if not VerifySvnVersion([1,5]):
            raise SvnError( "implementing a changeset requires svn version "
                            ">= 1.5, only found " + str(SvnVersion) )
        if len(changeset['add']) + len(changeset['del']) + \
               len(changeset['mod']) == 0:
            return

        allCheckouts = []
        repo = changeset.get('repo')
        if repo is None:
            raise ExternalError("changeset had unresolved repository")

        if os.path.exists( self.config['workingdir'] ):
            if os.path.isdir( self.config['workingdir'] ):
                log.warning( "working directory (%s) exists!" % \
                             self.config['workingdir'] )
            else:
                raise SvnError( "working directory (%s) exists " \
                                "(and is not a directory)!" % \
                                 self.config['workingdir'] )

        class externalFile(object):
            def __init__(self, dir):
                self.comments = []
                self.data = {}
                self.dir = dir
                self.name = 'Externals'
                self.svn15format = False

            def fileName(self):
                return os.path.join(self.dir, self.name)

        def _readExternalsFile(eInfo, target_wd):
            if isinstance(eInfo, str):
                e = eInfo
            else:
                e = eInfo[0]
                if e is None:
                    e = eInfo[1]
                e = e.path
            eDir, eName = os.path.split(e)
            ans = externalFile(os.path.join(target_wd, eDir))
            if not eName:
                raise ExternalError("external path ended with '/'")
            try:
                f = open(ans.fileName(), 'r')
                data1 = f.readlines()
                f.close()
                data2 = svn_propget('svn:externals', ans.dir)
                if data1 != data2:
                    log.warning("Externals file does not match "
                                "svn:externals property for (%s)!  "
                                "Deferring to the svn:externals property."
                                % ( ans.dir, ))
                data = data2
            except:
                try:
                    data = svn_propget('svn:externals', ans.dir)
                except Exception, e:
                    data = []

            # 2 passes: first guess the file format, then parse the file
            for line in data:
                line = line.strip()
                if line.startswith('#') or len(line) == 0:
                    continue
                if externals_14link_re.match(line):
                    continue
                if externals_15link_re.match(line):
                    ans.svn15format = True
                    break

            lNum = 0
            for line in data:
                line = line.strip()
                if line.startswith('#') or len(line) == 0:
                    ans.comments.append( (lNum, line+'\n') )
                    continue
                g = externals_14link_re.match(line)
                if g and not ans.svn15format:
                    lNum += 1
                    ans.data[g.group(1)] = [ [ g.group(3), g.group(2) ],
                                             lNum ]
                    continue
                g = externals_15link_re.match(line)
                if g:
                    lNum += 1
                    ans.svn15format = True
                    ans.data[g.group(4)] = [ [ g.group(2),
                                               g.group(3) or g.group(1) ],
                                             lNum ]
                    continue
                
            # Suppress trailing blank lines
            while len(ans.comments) and ans.comments[-1][0] == lNum and \
                      not ans.comments[-1][1].strip():
                ans.comments.pop()

            return (ans, eName);
        # end _readExternalsFile()

        def _writeExternalsFile(eFile):
            eList = sorted( eFile.data.keys(),
                            cmp=lambda x,y: cmp(x.lstrip('#'), y.lstrip('#')) )
            srcW = 0;
            targetW = 0;
            revW = 0;
            for e in eList:
                srcW = max(srcW, len(str(eFile.data[e][0][1])))
                targetW = max(targetW, len(e))
                if len(eFile.data[e][0]) > 1 and eFile.data[e][0][1] is not None:
                    revW = max(revW, len(str(eFile.data[e][0][1]))+3)
            if eFile.svn15format:
                field = "%%-%is%%-%is %%s\n" % ( revW, srcW )
            else:
                field = "%%-%is %%-%is%%s\n" % ( targetW, revW )

            lNum = 0;
            f = open(eFile.fileName(), 'w')
            while len(eList) > 0:
                while len(eFile.comments) and eFile.comments[0][0] <= lNum:
                    f.write(eFile.comments.pop(0)[1])

                e = eList.pop(0)
                uncommentedE = e.lstrip('#')
                if uncommentedE != e:
                    if uncommentedE in eFile.data.keys():
                        continue
                if len(eFile.data[e][0]) == 1 or eFile.data[e][0][1] is None:
                    tmp = (e, '', eFile.data[e][0][0]);
                else:
                    tmp = (e, '-r'+str(eFile.data[e][0][1]), eFile.data[e][0][0]);
                if eFile.svn15format:
                    tmp = (tmp[1], tmp[2], tmp[0])
                f.write( field % tmp )
                lNum = eFile.data[e][1]
            while len(eFile.comments) and not eFile.comments[-1][1].strip():
                eFile.comments.pop()
            while len(eFile.comments):
                f.write(eFile.comments.pop(0)[1])
            f.close()
            p = Popen( [ 'svn', 'propset', 'svn:externals', eFile.dir,
                         '-F', eFile.fileName() ],  stdout=PIPE, stderr=PIPE )
            stdout, stderr = p.communicate()
            if p.returncode:
                raise SvnError( "svn propset returned error %i:\n%s" %
                        (p.returncode, stderr) )
        # end _writeExternalsFile()

        def _checkoutTarget(item):
            if isinstance(item, ResolvedTarget):
                wd = os.path.join(self.config['workingdir'], item.project.name, item.name)
                url = item.url
            elif isinstance(item, ResolvedProject):
                wd = os.path.join(self.config['workingdir'], item.name)
                url = item.url
            else:
                log.warning("I cannot checkout a new project without " \
                            "checking out the WHOLE repository!")
                return

            if not url.startswith(repo.url):
                raise ExternalError("Target URL does not begin with Repo URL")

            wd = self.config['workingdir']
            url = repo.url
            for d in item.url[len(repo.url):].replace('\\','/').strip('/').split('/'):
                if len(d) == 0:
                    continue
                if not os.path.isdir(wd):
                    log.info("checking out " + url + " to " + wd + \
                             " (as empty directory)")
                    p = Popen( [ 'svn', 'co', '--depth=empty', url, wd ],
                               stdout=PIPE, stderr=PIPE )
                    stdout, stderr = p.communicate()
                    if p.returncode:
                        raise SvnError( "svn checkout returned error %i:\n%s" %
                                        (p.returncode, stderr) )
                wd = os.path.join(wd, d)
                url += '/' + d

            if os.path.isdir(wd):
                return wd
            log.info("checking out " + url)
            p = Popen( ['svn', 'co', '--ignore-externals', url, wd ],
                       stdout=PIPE, stderr=PIPE )
            stdout, stderr = p.communicate()
            if p.returncode:
                raise SvnError( "svn checkout returned error %i:\n%s" %
                        (p.returncode, stderr) )
            allCheckouts.append(wd)
            return wd
        # end _checkoutTarget()

        # First checkout anything where we need the whole project
        # (i.e. add / del)
        for target in changeset['del']:
            if target[1] is None:
                # Cannot automatically delete project
                continue
            _checkoutTarget(target[0])
        for target in changeset['add']:
            if target[1] is None:
                # Cannot automatically add new project
                continue
            _checkoutTarget(target[0])

        # Update any *changed* targets
        for t, eList in changeset['mod'].iteritems():
            log.info("Updating %s" % t)
            target_wd = _checkoutTarget(t)
            for e in eList:
                (eFile, eName) = _readExternalsFile(e, target_wd)

                if e[0] is None:
                    eFile.data[eName] = [[e[1].url(self, repo), e[1].rev], -1]
                elif e[1] is None and eName in eFile.data:
                    del eFile.data[eName]
                else:
                    eFile.data.setdefault(eName, [None, -1])[0] = \
                        [ e[1].url(self, repo), e[1].rev ]

                _writeExternalsFile(eFile)

        # Add any new targets
        for target in changeset['add']:
            if target[1] is None:
                log.warning("Cannot automatically add project '%s'" % \
                            target[0])
                continue
            target_def = defn[target[0].name].get(target[1], None)
            if target_def is None:
                log.error("Cannot create target '%s %% %s': no definition" % \
                          (target[0].name, target[1]))
                continue
            wd = os.path.join(
                self.config['workingdir'], target[0].name, target[1] )
            if not os.path.isdir(wd):
                inherit = target_def.get('source', [])
                if len(inherit) == 0:
                    log.error("Cannot create target '%s %% %s': %s" % (
                        target[0].name, target[1], "nothing to inherit from" ))
                    continue
                elif len(inherit) != 1:
                    log.error("Cannot create target '%s %% %s': %s" % 
                              ( target[0].name, target[1],
                                "no support for multiple inheritance" ))
                    continue

                src = repo.projects.get(inherit[0].project or target[0].name)
                if src is not None:
                    src = src.targets.get(inherit[0].target)
                if src is None:
                    log.error("Cannot create target '%s %% %s': %s" % \
                              ( target[0].name, target[1],
                                "base target is not in the repository?" ))
                    continue
                base = _checkoutTarget(src)

                log.info("Copying %s from %s" % ( target[1], base ))
                p = Popen( ['svn', 'cp', '--parents', base, wd],
                           stdout=PIPE, stderr=PIPE )
                stdout, stderr = p.communicate()
                if p.returncode:
                    raise SvnError( "svn cp returned error %i:\n%s" %
                                    (p.returncode, stderr) )
            log.info("Attempting to initialize externals for %s" % target[1])
            current_externals, svn15format = svn_externals(wd)
            print current_externals
            for e in current_externals:
                (eFile, eName) = _readExternalsFile(e.path, wd)
                try:
                    del eFile.data[eName]
                except KeyError:
                    pass
                _writeExternalsFile(eFile)
            for name, e in target_def.get('externals',{}).iteritems():
                (eFile, eName) = _readExternalsFile(name, wd)
                eFile.data[eName] = [ [ e.url(self, repo), e.rev ], -1 ]
                _writeExternalsFile(eFile)


        # Delete any old targets
        for target in changeset['del']:
            if target[1] is None:
                log.warning("Cannot automatically delete project '%s'" % \
                            target[0].name)
                continue
            log.info("Deleting %s" % target[1])
            target_wd = _checkoutTarget(target[1])
            p = Popen( ['svn', 'rm', target_wd],  stdout=PIPE, stderr=PIPE )
            stdout, stderr = p.communicate()
            if p.returncode:
                raise SvnError( "svn rm returned error %i:\n%s" %
                        (p.returncode, stderr) )

        # List changed locations
        log.info("The following directories need to be committed:\n" + \
                 ' '.join(allCheckouts))

    def branch_config(self, cfg):
        def _get_target(em, cfg, external):
            if type(external) is ResolvedProject:
                proj = external
                target = None
                current = ""
                msg = "Branch project from"
            else:
                target = external.target
                if target is None:
                    raise Exception( "External %s pointing to an unknown "
                                     "target, %s" %
                                     (external.path, external.url) )
                proj = target.project
                current = "current: %s, " % (external.target.name, )
                if proj in cfg['retargeted']:
                    target = cfg['retargeted'][proj]
                else:
                    target = external.target
                msg = "Target for external \"%s : %s\"" % (
                    external.path, proj.name )
                        
            i = -1;
            for t in proj.targets.itervalues():
                if t.rev > i:
                    i = t.rev
                    newest = t
            if target is None:
                target = newest
            newer = target is not newest and "*" or ""
            msg = "%s [%s%s] (%s? for list): " % \
                  (msg, target.name, newer, current)
            while True:
                sys.stdout.write(msg)
                ans = sys.stdin.readline().strip()
                if ans == "":
                    return target
                elif ans in proj.targets:
                    return proj.targets[ans]
                elif ans.isdigit():
                    num = int(ans)-1
                    if num >= 0 and num < len(proj.targets):
                        return proj.targets[sorted(proj.targets.keys())[num]]
                    log.error("Invalid target id)")
                elif ans == "?":
                    for idx, name in enumerate(sorted(proj.targets.keys())):
                        star = proj.targets[name] is newest and "*" or ""
                        print "   %2d: %s%s" % ( idx+1, name, star )
                else:
                    log.error("(Unrecognized target)")

        cfg.setdefault('retargeted', {})
        if cfg.get('project', None) is None:
            sys.stdout.write("Branch project name: ")
            cfg['project'] = sys.stdin.readline().strip()
        proj = cfg['project']
        if type(proj) is not ResolvedProject:
            cfg['project'] = proj = self.get_project(proj)
            if proj is None:
                raise ExternalError("branch_config(): bad project (%s)",
                                    (cfg['project'],) )
        
        if cfg.get('src', None) is None:
            cfg['src'] = _get_target(self, cfg, proj)
        elif type(cfg['src']) is str:
            cfg['src'] = proj.targets.get(cfg['src'], None)
        src = cfg['src']
        if type(src) is not ResolvedTarget:
            raise ExternalError("branch_config(): bad target (%s)", (src,))
        
        if cfg.get('target', None) is None:
            sys.stdout.write("Enter new target name: ")
            cfg['target'] = sys.stdin.readline().strip()
        if cfg['target'] in proj.targets:
            raise ExternalError("Cannot create new branch, %s: target "
                                "already exists" % ( cfg['target'], ))
        for c in illegal_characters:
            if c in cfg['target']:
                raise ExternalError("Illegal character (\"%s\") found in "
                                    "target name (\"%s\"", (c, cfg['target']))

        e_map = cfg.setdefault('externals',{})
        for e_path in sorted(src.externals.keys()):
            if e_path in e_map:
                continue
            t = _get_target(self, cfg, src.externals[e_path])
            if cfg['retargeted'].setdefault(t.project, t) is not t:
                orig = cfg['retargeted'][t.project]
                log.warning( "Externals pointing to multiple "
                             "targets (%s, %s) in project %s " %
                             ( orig is None and "*" or orig.name,
                               t.name, t.project.name ) )
                cfg['retargeted'][t.project] = None
            e_map[e_path] = t

        ans = { '__repo__' : proj.repo.url }
        defn = ans.setdefault(proj.name,{}).setdefault(cfg['target'], {})
        if cfg.get('peg', False):
            defn['branched-from'] = Description_Inherit(src.name)
            externals = defn.setdefault('externals', {})
            for e_path, old_e in src.externals.iteritems():
                target = e_map[e_path]
                new_e = externals[e_path] = Description_External(
                    e_path, project=target.project.name )
                new_e.target = target.name
                new_e.deep_ref = old_e.deep_ref
                if target is old_e.target and old_e.rev:
                    new_e.rev = old_e.rev
                else:
                    new_e.rev = target.project.repo.rev
                # Peg to a URL (and not a project / target reference)
                new_e.link = new_e.url(self, proj.repo)
                new_e.project = None
        else:
            defn['inherit'] = [ Description_Inherit(src.name) ]
            externals = defn.setdefault('externals', {})
            retarget = defn.setdefault('retarget', {})
            remove = defn.setdefault('remove', [])
            for e_path in sorted(src.externals):
                old_e = src.externals[e_path]
                target = e_map[e_path]
                retargeted = cfg['retargeted'].get(target.project, None)
                if target is retargeted:
                    if target is old_e.target:
                        continue
                    retarget[target.project.name] = Description_Retarget(
                        retargeted.name )
                else:
                    if retargeted is None and target is old_e.target:
                        continue
                    remove.append(e_path)
                    new_e = externals[e_path] = Description_External(
                        e_path, project=target.project.name )
                    new_e.target = target.name
                    new_e.deep_ref = old_e.deep_ref
            if len(externals) == 0:
                del defn['externals']
            if len(retarget) == 0:
                del defn['retarget']
            if len(remove) == 0:
                del defn['remove']
        return ans, proj.name

    def _resolve_external(self, e):
        # Did we resolve the external target?
        if e.target is not None:
            # But warn if the target was resolved through an alias
            if e.url != e.raw.url:
                return Status.aliased_url, e.target.rev
            return Status.ok, e.target.rev
        # Is the target outside our defined "scope"?
        url = e.url
        for ex in self.config['exclude']:
            if url.startswith(ex):
                return Status.excluded, None

        # Is the target a currently valid repo location?
        try:
            info = svn_info(url)
            if 'revision' in info:
                return Status.non_target, info['revision']
        except SvnError:
            pass
        # OK, we may have a problem... if the external pegged a
        # revision, did the target exist in that revision?
        if e.rev is not None:
            try:
                info = svn_info(url, e.rev)
                if 'revision' in info:
                    return Status.dne_in_head, info['revision']
            except SvnError:
                pass
        # This is definitely a broken external
        return Status.broken, None


if __name__ == "__main__":
    # Check for sane usage.
    em = ExternalManager()

    """
    # you can grow old and grey waiting for COIN-OR
    em.config['exclude'].append('https://projects.coin-or.org/')

    # Special cases:
    #   - EXACT is a pointer to FAST
    em.config['aliases'].append(( 'https://software.sandia.gov/svn/public/exact',
                        'https://software.sandia.gov/svn/public/fast' ))
    #   - software/svn/public is available via https
    em.config['aliases'].append(( 'svn+ssh://software.sandia.gov/svn/public',
                        'https://software.sandia.gov/svn/public' ))
    #   - DAKOTA used malformed URLs
    em.config['aliases'].append(( 'https://software.sandia.gov:/',
                        'https://software.sandia.gov/' ))

    # Unfortunately, the CxxTest repo and our mirror use the same name
    em.config['primary_projects']['cxxtest'] =  \
        'https://software.sandia.gov/svn/public/cxxtest:'
    em.config['primary_projects']['boost'] =  \
        'https://software.sandia.gov/svn/public/tpl:boost'

    print yaml.dump( em.config, default_flow_style=False,
                     explicit_start=True, explicit_end=True, width=160 ) \
                     .replace('{}','')
    """
    # The previous config translates to the following config.yaml:
    """
    ---
    aliases:
    - !!python/tuple
      - https://software.sandia.gov/svn/public/exact
      - https://software.sandia.gov/svn/public/fast
    - !!python/tuple
      - svn+ssh://software.sandia.gov/svn/public
      - https://software.sandia.gov/svn/public
    - !!python/tuple
      - https://software.sandia.gov:/
      - https://software.sandia.gov/
    exclude:
      - https://projects.coin-or.org/
    pegged_targets:
      - releases
      - tags
      - maintenance
    primary_projects:
      boost: https://software.sandia.gov/svn/public/tpl:boost
      cxxtest: 'https://software.sandia.gov/svn/public/cxxtest:'
    workingdir: svnpm-tmp
    ...
    """

    #em.update()
    em.resolve_targets()
    #em.check_integrity()
    #em.check_pegged()
    #em.check_pegged(repo=em.projects['autodock-th'].repo)

    #ref_map = em.reference_map()
    #for target in sorted(ref_map.keys(), key=lambda t : str(t)):
    #    print str(target)
    #    for r in ref_map[target]:
    #        print "   %s" % str(r)

    #descrip = em.generate_repo_definition(proj="acro-utilib")
    #descrip = em.generate_repo_definition(repo=em.projects["acro-utilib"].repo)
    #final = em.finalize_repo_definition(descrip)
    #em.collapse_repo_definition(descrip)
    #em.collapse_repo_definition(final)
    #print yaml.dump( descrip, default_flow_style=False,
    #                 explicit_start=True, explicit_end=True, width=160 ) \
    #                 .replace('{}','')

    FILE = open('acro.yaml')
    user_descrip = yaml.load(FILE)
    em.expand_repo_definition(user_descrip)
    FILE.close()
    descrip = em.finalize_repo_definition(user_descrip)
    changes = em.generate_changeset_from_definition(descrip)
    em.print_changeset(changes)
    #em.implement_changeset(changes, descrip, em.projects["acro"].repo)
