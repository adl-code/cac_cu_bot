from BotCore import *


class InsultMod(BotEngine.BotBaseMod):
    """
    This module logs insulting chat from people and behaves accordingly
    """
    PREFS_NAME = 'InsultMod'
    _mod_name = 'InsultMod'
    _mod_desc = 'This module logs insulting chat from people and behaves accordingly'

    def get_mod_name(self):
        return self._mod_name

    def get_mod_desc(self):
        return self._mod_desc

    def on_registered(self, bot_core):
        pass

    def on_message(self, bot_core, msg):
        pass
