#!/usr/bin/python
import os
import sys

if __name__ == '__main__':
    # update environment variables
    env        = []
    installdir = os.path.dirname(__file__)
    plugdir    = os.path.join(installdir, 'plugins')
    homedir    = os.path.expanduser('~')
    env.append(plugdir)
    env.append(os.path.join(homedir,'.orion','plugins'))
    try:
        env.append(os.environ['ORION_PLUGIN_PATH'].split(os.pathsep))
    except:
        pass
    os.environ['ORION_PLUGIN_PATH'] = os.pathsep.join(env)
    paths=['/home/wdanilo/dev/python/orion/plugins']
    sys.path.append(os.path.join(installdir,'src'))
    
    # run orion
    import orion
    print orion
    orion.run()