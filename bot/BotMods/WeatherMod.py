from BotCore import *


class WeatherMod(BotEngine.BotBaseMod):
    """
    This module provides weather information
    """
    _mod_name = 'weather_mod'
    _mod_desc = 'WeatherMod provides weather information for users'
    _locations = None

    def __init__(self):
        pass

    def get_mod_name(self):
        return self._mod_name

    def get_mod_desc(self):
        return self._mod_desc

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
        pass
