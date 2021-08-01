"""
Consults http://www.etymonline.com/ for the meaning of words.
"""

import supybot
import supybot.world as world
from . import config
from . import plugin
import importlib
importlib.reload(plugin) # In case we're being reloaded.

Class = plugin.Class
configure = config.configure
