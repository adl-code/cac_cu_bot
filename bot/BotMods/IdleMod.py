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

    def on_mentioned(self, bot_core, msg):
        """
        Process message that mention bot name
        :param bot_core: the bot engine
        :param msg: the message
        :return: reply message
        """
        return self.process_message(self)

    def on_not_mentioned(self, bot_core, msg):
        """
        Process messages that don't message bot name
        :param bot_core: the core engine 
        :param msg:  the message
        :return:  reply message
        """
        return self.process_message(self)

    def process_message(self, msg):
        pass
