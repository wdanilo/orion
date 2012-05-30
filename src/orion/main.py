
import os, os.path, sys
from orion import confreader, manager
from orion.model.logger import Logger

def run():
    from optparse import OptionParser, OptionGroup
    
    l = Logger('orion', verbose=True)
    
    parser = OptionParser(version="%prog 0.4")
    parser.add_option(
                        "-c", "--config",
                        action="store", type="string",
                        default=None,
                        dest="configfile",
                        help='Use specified configuration file, "default" will load the system default config.'
                    )
    parser.add_option(
                        "-f", "--fallback",
                        action="store", type="string",
                        default=None,
                        dest="fallback",
                        help='Use specified fallback configuration file, "default" will load the system default config as fallback.'
                    )
    parser.add_option(
                        "-d", "--debug",
                        action="store_true", default=False,
                        dest="debug",
                        help='Print lots of debugging output.'
                    )
    parser.add_option(
                        "-s", "--socket",
                        action="store", type="string",
                        default=None,
                        dest="socket",
                        help='Path to Qtile comms socket.'
                    )
    options, args = parser.parse_args()
    try:
        c = confreader.File(options.configfile)
    except confreader.ConfigError, v:
        if options.fallback:
            print >> sys.stderr, "Config error: %s" % v.message
            print >> sys.stderr, "Falling back to config file: %s" % options.fallback
            c = confreader.File(options.fallback)
        else:
            raise
    q = manager.Qtile(c, fname=options.socket)
    q.debug = options.debug
    q.loop()


