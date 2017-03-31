from BotConfig import *
from abc import ABCMeta, abstractmethod
import logging
import logging.config


class User(object):
    """
    This class represents an user that Bot would interact with    
    """
    UNKNOWN_USER = 0
    BOSS_USER = 1
    NORMAL_USER = 10
    BAD_USER = 20

    def __init__(self):
        self._type = User.UNKNOWN_USER
        self._id = ""
        self._name_list = []

    def get_type(self):
        return self._type

    def get_id(self):
        return self._id

    def get_name_list(self):
        return self._name_list

    def get_location(self):
        return self._location

    @staticmethod
    def parse_user_type(user_type):
        if user_type is None or not isinstance(user_type, (str, unicode)):
            return User.UNKNOWN_USER
        t = user_type.lower()
        if t == 'boss':
            return User.BOSS_USER
        elif t == "normal_user":
            return User.NORMAL_USER
        elif t == "bad_user":
            return User.BAD_USER
        else:
            return User.UNKNOWN_USER

    @staticmethod
    def parse_user_entry(user_entry):
        """
        Parse an user entry data and create a correspondent User object
        :return: User object, None if error 
        """
        if user_entry is None or not isinstance(user_entry, dict):
            return None
        # Name is required
        if 'id' in user_entry:
            user_id = user_entry['id']
        else:
            return None

        # Parse user type
        if 'type' in user_entry:
            user_type = User.parse_user_type(user_entry['type'])
            if user_type == User.UNKNOWN_USER:
                return None
        else:
            user_type = User.NORMAL_USER

        # Name list
        if 'names' in user_entry:
            name_list = user_entry['names']
            if name_list is None or not isinstance(name_list, list):
                return None
        else:
            return None

        # Location
        location = None
        if 'location' in user_entry:
            location = user_entry['location']

        user = User()
        user._name_list = name_list
        user._id = user_id
        user._type = user_type
        if location is not None:
            user._location = location
        return user

    @staticmethod
    def parse_user_list(input_file):
        """
        Parse user list from json-formatted file
        :param input_file: json input file to parse 
        :return: list of User object, None if error
        """
        try:
            f = open(input_file, "rb")
            input_data = JsonLoader.json_load_byteified(f)
            f.close()
        except IOError:
            return
        if input_data is None:
            return None
        if not isinstance(input_data, list):
            return None
        user_list = []
        for user_entry in input_data:
            user = User.parse_user_entry(user_entry)
            if user is not None:
                user_list.append(user)
        if len(user_list) == 0:
            return None
        return user_list


class BotBaseMod:
    """
    BotBaseMode class represents a base class for bot module
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def get_mod_name(self):
        """
        :return: unique name identified the module 
        """
        pass

    @abstractmethod
    def on_registered(self, bot_core):
        """
        Initialized the module right after it has been registered with the core
        :param bot_core: 
        :return: None        
        """
        pass

    @abstractmethod
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


class BotEngine:
    """
    This class represents the core bot engine
    """
    _logger_name = 'CacCuBot'

    def __init__(self, config_file):
        self._bot_config = BotConfig(config_file)
        self._mod_list = []

        # Initialize logger
        self.__init_logger()

        # Initialize user list
        self.__init_user_list()

    def __init_logger(self):
        logger_config_file = self.get_config().get_path('logger_config_file')
        parsed_from_file = False
        if logger_config_file is not None:
            try:
                logging.config.fileConfig(logger_config_file)
                parsed_from_file = True
            except ConfigParser.Error as err:
                print err.message
                parsed_from_file = False

        self._logger = logging.getLogger(self._logger_name)
        if not parsed_from_file:
            # No config file found, setup default logger config
            self._logger.setLevel(logging.DEBUG)

            # Configure console log handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            console_formatter = logging.Formatter("%(asctime)s - %(name)s - [%(levelname)-10s]: %(message)s")
            console_handler.setFormatter(console_formatter)

            # Add handlers to logger
            self._logger.addHandler(console_handler)

    def __init_user_list(self):
        user_config_path = self.get_config().get_path('user_config_file')
        if user_config_path is None:
            self.__user_list = None
        else:
            self.__user_list = User.parse_user_list(user_config_path)

    def get_user_list(self):
        return self.__user_list

    def get_config(self):
        return self._bot_config

    def register_mod(self, mod):
        """
        Register a bot module
        :param mod: mod: the module to register
        :return: True if successful, False otherwise
        """
        if mod is None or issubclass(mod, BotBaseMod):
            return False
        self._mod_list.append(mod)

    def get_logger(self):
        return self._logger

    def run(self):
        """
        Execute the main bot thread
        :return: None
        """
        pass
