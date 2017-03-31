from BotCore import *


class WeatherMod(BotEngine.BotBaseMod):
    _mod_name = 'weather_mod'
    _locations = None

    def __init__(self):
        pass

    def get_mod_name(self):
        return self._mod_name

    def __parse_config(self, config_file):
        try:
            f = open(config_file, "rt")
            data = BotConfig.JsonLoader.json_load_byteified(f)
            f.close()
        except IOError:
            data = None
        if data is None:
            return
        if 'locations' in data:
            self._locations = data['locations']
            for loc in self._locations:
                self._locations[loc]['user_list'] = []

    def on_registered(self, bot_core):
        """        
        Initialized the module right after it has been registered with the core
        :param bot_core:
        :return: None      
        """
        cfg_file = bot_core.get_config().get_path('weather_config_file')
        if cfg_file is not None:
            self.__parse_config(cfg_file)

        # Build location map
        if self._locations is not None:
            user_list = bot_core.get_user_list()
            if user_list is not None:
                for user in user_list:
                    location = user.get_location()
                    if location is not None and location in self._locations:
                        self._locations[location]['user_list'].append(user)

        bot_core.get_logger().debug('Module "%s" initialized' % self._mod_name)

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
