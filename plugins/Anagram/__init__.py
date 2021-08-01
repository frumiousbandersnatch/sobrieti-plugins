"""
Creates an anagram from a string of text.
"""

import supybot
import supybot.world as world
from . import config
from . import plugin
import importlib
importlib.reload(plugin) # In case we're being reloaded.

Class = plugin.Class
configure = config.configure
