from BotCore import *


class IdleMod(BotEngine.BotBaseMod):
    """
    This module allows bot to chit-chat when people are idle
    
    """
    _mod_name = 'idle_mod'
    _mod_desc = "IdleMod give comments to idle users"

    def __init__(self):
        pass

    def get_mod_name(self):
        return self._mod_name

    def get_mod_desc(self):
        return self._mod_desc

    def __parse_config(self, config_file):
        try:
            f = open(config_file, "rt")
            data = BotConfig.JsonLoader.json_load_byteified(f)
            f.close()
        except IOError:
            data = None
        if data is None:
            return

    def on_registered(self, bot_core):
        """        
        Initialized the module right after it has been registered with the core
        :param bot_core:
        :return: None      
        """
        bot_core.get_logger().debug('Module "%s" initialized' % self._mod_name)

    def on_message(self, bot_core, msg):
        """
        Process messages
        :param bot_core: the core engine 
        :param msg:  the message
        :return:  reply message, None to skip replying this message 
        """
        return None
