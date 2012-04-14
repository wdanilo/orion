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

import logging
import os
import re
import sys
import yaml
from optparse import OptionParser, IndentedHelpFormatter
from pyutilib.svn.core import log
from pyutilib.svn.database import RepositoryDatabase, DatabaseError
from pyutilib.svn.external_manager import ExternalManager

class CommandParserCommand(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg

class CommandParser(OptionParser):
    def error(self, what):
        g = re.match('no such option: (.+)', what)
        if g:
            raise CommandParserCommand(g.group(1))
        OptionParser.error(self, what)

class DescriptionFormatter(IndentedHelpFormatter):
    def format_description(self, description):
        parts = description.split("\n\n")
        ans = ""
        for part in parts:
            tmp = IndentedHelpFormatter.format_description(self, part)
            if tmp and tmp[0] != " " and len(ans):
                ans += "\n" + tmp
            else:
                ans += tmp
        return ans


class ScriptCommand(object):
    def help(self, pm):
        pass
    def register_options(self, parser):
        pass
    def process(self, pm, options, args):
        pass


class help_cmd(ScriptCommand):
    def help(self, pm):
        return """ \
%prog: a utility for managing externals-based projects within
Subversion.  Specific help for individual subcommands is available by
running '%prog help <subcommand>'.

Available subcommands:\n\n   """ + "\n\n   ".join(sorted(pm.commands.keys()))

    def process(self, pm, options, args):
        if len(args) > 1:
            cmd = args[1]
            if cmd not in pm.commands:
                print "Unknown command: " + cmd
                return 2
            info = cmd.upper() + ": " + ( pm.commands[cmd].help(pm) or
                                          "(no description provided)")
            parser = OptionParser(usage=pm.usage,
                                  description=info,
                                  formatter=DescriptionFormatter())
            pm.common_args(parser)
            pm.commands[cmd].register_options(parser)
            parser.print_help()
        else:
            self.process(pm, options, ['help', 'help'])


class CommandManager(object):
    def __init__(self):
        self.commands = {}
        self.register_command("help", help_cmd())
        self.usage = """usage: %prog subcommand [options] [args]
Type '%prog help <subcommand>' for help on a specific subcommand."""

    def register_command(self, name, cmd):
        if name in self.commands:
            raise ProjectManager_Error("duplicate command name: %s" % name)
        self.commands[name] = cmd

    def common_args(self, parser):
        parser.add_option('--verbose', '-v', action="count", dest='verbose',
                          default=CommandManager.default_verbosity(),
                          help="increase verbosity; "
                          "can be specified multiple times")
        parser.add_option('--quiet', '-q', action="store_true", dest='quiet',
                          help="silence all messages except for errors")

    @staticmethod
    def default_verbosity():
        return 1

    def process(self, args=None):
        if args is None:
            args = sys.argv[1:]
        else:
            args = args[:]

        # We need to preemptively parse the command line to try and
        # determine the command name
        parser = CommandParser(usage=self.usage)
        self.common_args(parser)
        try:
            options, largs = parser.parse_args(args[:])
        except CommandParserCommand, e:
            if len(parser.largs):
                largs = parser.largs
            else:
                largs = [e.msg]

        if len(largs) == 0:
            log.error("No subcommand specified")
            parser.print_usage()
            return 2

        command = largs[0]
        if command not in self.commands:
            log.error("Unknown subcommand: " + command)
            parser.print_usage()
            return 2

        # now that we know the command, pars the args for real
        parser = OptionParser(usage=self.usage)
        self.common_args(parser)
        self.commands[command].register_options(parser)
        options, largs = parser.parse_args(args[:])

        if not len(largs) or largs[0] != command:
            log.error( "My understanding of the subcommand changed between "
                       "preprocessing (%s) and runtime (%s)" %
                       ( command, len(largs) and "None" or largs[0] ) )
            return 1

        # process common options
        if options.quiet or options.verbose == 0:
            log.setLevel(logging.ERROR)
        elif options.verbose == 1:
            log.setLevel(logging.WARNING)
        elif options.verbose == 2:
            log.setLevel(logging.INFO)
        elif options.verbose >= 3:
            log.setLevel(logging.DEBUG)

        # run the command
        return self.commands[command].process(self, options, largs)



class db_cmd(ScriptCommand):
    def help(self, pm):
        return """
Perform administration on the cached database of Subversion
repository information."""

    def register_options(self, parser):
        parser.add_option('--add', '-a', action="append", dest='add',
                          default=[],
                          help="add a new repository to the database")
        parser.add_option('--remove', action="append", dest='remove',
                          default=[],
                          help="remove a repository from the database")
        parser.add_option('--update', '-u', action="store_true", dest="update",
                          help="update the repository database cache")
        parser.add_option('--rebuild', action="store_true", dest="rebuild",
                          help="rebuild the repository database cache")
        parser.add_option('--print', '-p', action="store_true", dest="printdb",
                          help="print the repository database")
        parser.add_option('--list', '-l', action="append", dest="list",
                          default=[],
                          help="list the specified database components "\
                              "[repos, projects, targets]")

    def process(self, pm, options, args):
        db = RepositoryDatabase(options.db)
        try:
            db.load()
        except DatabaseError:
            log.info("cache file DNE; initializing empty database")

        for url in options.add:
            db.add(url)
            db.save()
        for url in options.remove:
            db.remove(url)
            db.save()
        if options.rebuild:
            db.rescan()
            db.save()
        if options.update:
            if db.update():
                db.save()
        if options.printdb:
            print db
        for component in options.list:
            if component == 'repos':
                print "\n".join(sorted(db.repos.keys()))
            elif component == 'projects':
                for r in sorted(db.repos.keys()):
                    print "\n".join(sorted([ x.url for x in
                                             db.repos[r].projects.values() ]))
            elif component == 'targets':
                for r in sorted(db.repos.keys()):
                    for p in sorted(db.repos[r].projects.keys()):
                        print "\n".join(sorted([x.url for x in
                                   db.repos[r].projects[p].targets.values()]))
            else:
                log.error("Unknown component " + component)


class update_cmd(ScriptCommand):
    def help(self, pm):
        return """
Recursively update all repositories in the repository database cache.
This subcommand will update all repositories in the database and then
recursively parse all externals in each repository and add the
repositories that those externals point to to the repository database.
Pay special attention to the 'aliases; and 'exclude' sections of the
configuration file to prevent repositories from being included multiple
times through different URLs, or to exclude repositories completely."""

    def register_options(self, parser):
        parser.add_option('--config', '-c', action="store", dest='config',
                          help="the location of the configuration file "
                          "(default=%s)" % ExternalManager.default_config())

    def process(self, pm, options, args):
        em = ExternalManager(options.config)
        em.update()


class check_cmd(ScriptCommand):
    def help(self, pm):
        return """
Check the integrity of all externals in the repository database.  This
will identify issues with externals, including:

  - externals that point through an aliased URL.

  - externals that point to an excluded URL.

  - externals that point to a location other than a known project target.

  - pegged externals that work but point to locations that no longer
exist at the HEAD.

  - externals that are pegged to revisions older than HEAD for that location.

  - externals that should be pegged, but are not.
"""

    def register_options(self, parser):
        parser.add_option('--config', '-c', action="store", dest='config',
                          help="the location of the configuration file "
                          "(default=%s)" % ExternalManager.default_config())
        parser.add_option('--peg', action="store_true", dest='peg',
                          help="validate that all externals referenced "
                          "through pegged targets are also pegged")
        parser.add_option('--key', '-k', action="store_true", dest='key',
                          help="print a key to all the symbols used")
        parser.add_option('--project', '-p', action="store", dest='project',
                          help="only check specified project")
        parser.add_option('--repo', '-r', action="store", dest='repo',
                          help="only check specified repository")

    def process(self, pm, options, args):
        em = ExternalManager(options.config)
        em.resolve_targets()
        proj = None
        repo = None
        if options.project:
            proj = em.get_project(options.project)
            if proj is None:
                log.error( "Specified project (%s) does not exist" %
                           options.project )
                return 1
        if options.repo:
            repo = em.get_repository(options.repo)
            if repo is None:
                log.error( "Specified repository (%s) does not exist" %
                           options.repo )
                return 1
        if options.peg:
            em.check_pegged(project=proj, repo=repo, key=options.key)
        else:
            em.check_integrity(project=proj, repo=repo, key=options.key)


class status_cmd(ScriptCommand):
    def help(self, pm):
        return """
Print information on the status for projects in the repository database.
"""

    def register_options(self, parser):
        parser.add_option('--config', '-c', action="store", dest='config',
                          help="the location of the configuration file "
                          "(default=%s)" % ExternalManager.default_config())
        parser.add_option('--project', '-p', action="store", dest='project',
                          help="only check specified project")
        parser.add_option('--repo', '-r', action="store", dest='repo',
                          help="only check specified repository")

    def process(self, pm, options, args):
        em = ExternalManager(options.config)
        em.resolve_targets()
        proj = None
        repo = None
        if options.project:
            proj = em.get_project(options.project)
            if proj is None:
                log.error( "Specified project (%s) does not exist" %
                           options.project )
                return 1
        if options.repo:
            repo = em.get_repository(options.repo)
            if repo is None:
                log.error( "Specified repository (%s) does not exist" %
                           options.repo )
                return 1
        em.print_status(repo=repo, project=proj)


class diff_cmd(ScriptCommand):
    def help(self, pm):
        return """
Print a difference between the specified repository definition and the
current state of the repository (as stored in the repository database).

usage: %prog diff repo_defn [options] [args]

   repo_defn : the YAML repository definition file to compare against
"""

    def register_options(self, parser):
        parser.add_option('--config', '-c', action="store", dest='config',
                          help="the location of the configuration file "
                          "(default=%s)" % ExternalManager.default_config())

    def process(self, pm, options, args):
        fname = len(args) > 1 and args[1] or None
        if not fname or not os.path.exists( fname ):
            log.error("Definition file (%s) does not exist" % str(fname))
            return 1

        em = ExternalManager(options.config)
        em.resolve_targets()
        user_description = em.load_repo_definition(fname)
        description = em.finalize_repo_definition(user_description)
        changes = em.generate_changeset_from_definition(description)
        em.print_changeset(changes)


class inspect_cmd(ScriptCommand):
    def help(self, pm):
        return """
Generate the YAML repository definition for the specified Subversion
repository.  It is HIGHLY recommended that you
update your repository database cache BEFORE running this command.

usage: %prog inspect repo_defn [options]

   repo_defn : the YAML repository definition file to generate
"""

    def register_options(self, parser):
        parser.add_option('--config', '-c', action="store", dest='config',
                          help="the location of the configuration file "
                          "(default=%s)" % ExternalManager.default_config())
        parser.add_option('--project', '-p', action="store", dest='project',
                          help="generate description for the specified project")
        parser.add_option('--repo', '-r', action="store", dest='repo',
                          help="generate description for the specified repository")

    def process(self, pm, options, args):
        fname = len(args) > 1 and args[1] or None
        if not fname:
            log.error("Definition file was not specified.")
            return 1
        if os.path.exists( fname ):
            log.error("Definition file (%s) exists" % str(fname))
            return 1

        em = ExternalManager(options.config)
        em.resolve_targets()

        proj = None
        repo = None
        if options.project:
            proj = em.get_project(options.project)
            if proj is None:
                log.error( "Specified project (%s) does not exist" %
                           options.project )
                return 1
        if options.repo:
            repo = em.get_repository(options.repo)
            if repo is None:
                log.error( "Specified repository (%s) does not exist" %
                           options.repo )
                return 1

        descrip = em.generate_repo_definition(proj=proj, repo=repo)
        final = em.finalize_repo_definition(descrip)
        ans = em.collapse_repo_definition(final)
        log.info("Writing description to " + fname)
        FILE = open(fname, 'w')
        FILE.write( yaml.dump( ans, default_flow_style=False,
                               explicit_start=True, explicit_end=True,
                               width=160 ).replace('{}','') )
        FILE.close()


class apply_cmd(ScriptCommand):
    def help(self, pm):
        return """
Create a working copy and apply any changes necessary to match the
specified repository definition.  It is HIGHLY recommended that you
update your repository database cache BEFORE running this command.

usage: %prog apply repo_defn [options] [args]

   repo_defn : the YAML repository definition file to compare against
"""

    def register_options(self, parser):
        parser.add_option('--config', '-c', action="store", dest='config',
                          help="the location of the configuration file "
                          "(default=%s)" % ExternalManager.default_config())

    def process(self, pm, options, args):
        fname = len(args) > 1 and args[1] or None
        if not fname or not os.path.exists( fname ):
            log.error("Definition file (%s) does not exist" % str(fname))
            return 1

        em = ExternalManager(options.config)
        em.resolve_targets()
        user_description = em.load_repo_definition(fname)
        description = em.finalize_repo_definition(user_description)
        changes = em.generate_changeset_from_definition(description)
        em.implement_changeset(changes, description)



class branch_cmd(ScriptCommand):
    def help(self, pm):
        return """
Prepare a branch of an existing project.

usage: %prog branch repo_defn [options] [args]

   repo_defn : the YAML repository definition file to update with the
               branch configuration
"""

    def register_options(self, parser):
        parser.add_option('--config', '-c', action="store", dest='config',
                          help="the location of the configuration file "
                          "(default=%s)" % ExternalManager.default_config())
        parser.add_option('--project', '-p', action="store", dest='project',
                          help="project to branch")
        parser.add_option('--source', action="store", dest='source',
                          help="source target (target to be copied)")
        parser.add_option('--dest', action="store", dest='dest',
                          help="destination target (target to be created)")
        parser.add_option('--peg', action="store_true", dest='peg',
                          help="peg all externals to fixed revision numbers")
        parser.add_option('--dry-run', action="store_true", dest='dryrun',
                          help="configure branch, but do not add it to "
                          "the definition file")

    def process(self, pm, options, args):
        fname = len(args) > 1 and args[1] or None
        if not fname or not os.path.exists( fname ):
            log.error("Definition file (%s) does not exist" % str(fname))
            return 1

        em = ExternalManager(options.config)
        em.resolve_targets()

        branch_cfg = {'peg' : options.peg}
        if options.project:
            branch_cfg['project'] = options.project
        if options.source:
            branch_cfg['src'] = options.source
        if options.dest:
            branch_cfg['target'] = options.dest
        defn, proj_name = em.branch_config(branch_cfg)

        tmp = em.collapse_repo_definition(defn)
        log.info("Configured branch: \n" + yaml.dump(
            tmp, default_flow_style=False,
            explicit_start=True, explicit_end=True,
            width=160 ).replace('{}',''))

        if options.dryrun:
            return 0

        user_description = em.load_repo_definition(fname)
        if defn['__repo__'] != user_description['__repo__']:
            log.error("Definition file does not match branch repository")
            return 1
        user_description[proj_name].update(defn[proj_name])
        ans = em.collapse_repo_definition(user_description)
        log.info("Writing description to " + fname)
        FILE = open(fname, 'w')
        FILE.write( yaml.dump( ans, default_flow_style=False,
                               explicit_start=True, explicit_end=True,
                               width=160 ).replace('{}','') )
        FILE.close()

        #description = em.finalize_repo_definition(user_description)
        #changes = em.generate_changeset_from_definition(description)
        #em.print_changeset(changes)


class SVNPM_CommandManager(CommandManager):
    def __init__(self):
        CommandManager.__init__(self)
        self.register_command("db",      db_cmd())
        self.register_command("update",  update_cmd())
        self.register_command("check",   check_cmd())
        self.register_command("diff",    diff_cmd())
        self.register_command("inspect", inspect_cmd())
        self.register_command("apply",   apply_cmd())
        self.register_command("status",  status_cmd())
        self.register_command("branch",  branch_cmd())

    def common_args(self, parser):
        CommandManager.common_args(self, parser)
        parser.add_option('--database','-d', action="store", dest='db',
                          default=RepositoryDatabase.default_db(),
                          help="the repository database file "
                          "(default=%default)")


def main():
    pm = SVNPM_CommandManager()
    sys.exit(pm.process())

if __name__ == '__main__':
    main()
