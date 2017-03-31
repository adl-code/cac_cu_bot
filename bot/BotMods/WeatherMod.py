from BotCore.BotEngine import *


class WeatherMod(BotBaseMod):
    _mod_name = 'weather_mode'

    def __init__(self):
        pass

    def get_mod_name(self):
        return self._mod_name

    def on_registered(self, bot_core):
        """        
        Initialized the module right after it has been registered with the core
        :param bot_core:
        :return: None      
        """
        bot_core.get_logger().debug("Module %s initialized" % self._mod_name)

    def on_mentioned(self, bot_core, msg):
        """
        Process message that mention bot name
        :param bot_core: the bot engine
        :param msg: the message
        :return: reply message
        """
        pass

    def on_not_mentioned(self, bot_core, msg):
        """
        Process messages that don't message bot name
        :param bot_core: the core engine 
        :param msg:  the message
        :return:  reply message
        """
        pass
