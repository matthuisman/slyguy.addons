import os
import sys

path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(1, os.path.realpath(os.path.join(path, 'resources/modules')))

from resources.lib.plugin import plugin
plugin.dispatch()
