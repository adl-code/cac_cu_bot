from BotConfig import *
from abc import ABCMeta, abstractmethod
import logging
import logging.config
from slackclient import SlackClient
import time


class User(object):
    """
    This class represents an user that Bot would interact with.
    Please notice that user is different than "slack member"
    """
    UNKNOWN_USER = 0
    BOSS_USER = 1
    NORMAL_USER = 10
    BAD_USER = 20

    def __init__(self):
        self._type = User.UNKNOWN_USER
        self._id = ""
        self._location = None
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
        user_list = {}
        for user_entry in input_data:
            user = User.parse_user_entry(user_entry)
            if user is not None:
                name_list = user.get_name_list()
                for name in name_list:
                    user_list[name] = user
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
        Get module name
        :return: unique name identified the module 
        """
        pass

    @abstractmethod
    def get_mod_desc(self):
        """
        Get module description
        :return: description string
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
    def on_message(self, bot_core, msg):
        """
        Process messages
        :param bot_core: the core engine 
        :param msg:  the message
        :return:  reply message, None to skip replying this message 
        """
        pass


class BotTimer:
    """
    This class provide simple method for timing bot tasks
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def on_timer(self, timer_id, bot_core):
        pass


class BotEngine:
    """
    This class represents the core bot engine
    """
    _logger_name = 'CacCuBot'
    BOT_NAME = "cac_cu"
    _member_list = {}
    _channel_list = {}
    _bot_info = {}
    _timer_list = {}
    _slack_client = None

    def __init__(self, config_file):
        self._bot_config = BotConfig(config_file)
        self._mod_list = []

        # Initialize logger
        self.__init_logger()

        # Initialize user list
        self.__init_user_list()

        # Initialize member list, channel list ...
        self.__init_slack_client()
        self.__init_member_list()
        self.__init_channel_list()

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
            self._user_list = None
        else:
            self._user_list = User.parse_user_list(user_config_path)

    def __init_slack_client(self):
        if self._slack_client is None and not self.get_config().should_be_offline():
            self._slack_client = SlackClient(self.get_config().get_api_token())

    def __init_member_list(self):
        if self._slack_client is None:
            return
        api_call = self._slack_client.api_call("users.list")
        if api_call is not None and api_call.get('ok'):
            # Retrieve all users so we can find our bot
            users = api_call.get('members')
            for user in users:
                if 'name' in user and 'id' in user:
                    user_id = user['id']
                    user_name = user['name']
                    if user_name == self.BOT_NAME:
                        self._bot_info['name'] = user_name
                        self._bot_info['id'] = user_id
                        self._bot_info['raw'] = user
                        self.get_logger().debug('Bot name = %s, ID = %s' % (user_name, user_id))
                    else:
                        member = {
                            'name': user_name,
                            'id': user_id,
                            'raw': user}
                        self._member_list[user_id] = member
                        self.get_logger().debug('Member name = %s, ID = %s' % (user_name, user_id))

    def __init_channel_list(self):
        if self._slack_client is None:
            return
        api_call = self._slack_client.api_call("channels.list")
        if api_call is not None and api_call.get('ok'):
            channels = api_call.get('channels')
            for channel in channels:
                if 'id' not in channel or 'name' not in channel:
                    continue
                chan = {
                    'name': channel['name'],
                    'id': channel['id'],
                    'raw': channel
                }
                self._channel_list[chan['id']] = chan
                self.get_logger().debug('Channel name = %s, ID = %s' % (chan['name'], chan['id']))

    def get_user_list(self):
        # Get user list
        # This list differs from "member list"
        # The first list contains pre-configured data for user information
        # The latter contains Slack user (member) list
        return self._user_list

    def get_config(self):
        # Get config object
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
        # Get logger object
        return self._logger

    def get_bot_info(self):
        # Get bot information
        return self._bot_config

    def get_member_list(self):
        return self._member_list

    def find_member(self, member_id):
        """
        Find member based on member id
        :param member_id: ID of member to check
        :return: a tuple of member object and user object representing the member
        """
        if member_id is None or member_id not in self._member_list:
            return None, None
        member = self._member_list[member_id]
        if self._user_list is not None and member['name'] in self._user_list:
            user = self._user_list[member['name']]
        else:
            user = None
        return member, user

    def register_timer(self, timer_obj, timer_id):
        if timer_id is None or timer_obj is None:
            return
        self._timer_list[timer_id] = timer_obj

    def __preprocess_msg(self, msg):
        the_msg = {'raw': msg}
        # Try tokenizing the message
        if 'type' in msg and msg['type'] == 'message':
            the_msg['is_message'] = True
            bot_mentioned = False
            if 'text' in msg:
                the_msg['raw_words'] = msg['text'].split()
                the_msg['words'] = map(str.lower, the_msg['raw_words'])
                for word in the_msg['words']:
                    if word == '@' + self._bot_info['name']:
                        bot_mentioned = True
                        break
            the_msg['is_bot_mentioned'] = bot_mentioned

        else:
            the_msg['is_message'] = False

        return the_msg

    def __response(self, msg, response):
        pass

    def __process_msg(self, msg):
        the_msg = self.__preprocess_msg(msg)
        if the_msg is None:
            return
        for mod in self._mod_list:
            response = mod.on_message(self, the_msg)
            if response is not None:
                # One of the module has response
                self.__response(the_msg, response)
                return

    def run(self):
        """
        Execute the main bot thread
        :return: None
        """
        is_offline_mode = self.get_config().should_be_offline()
        delay_time = 1   # 1 second
        if is_offline_mode:
            self.get_logger().info('=== Slack Bot running in OFFLINE mode ===')
        else:
            if self._slack_client is None:
                self.get_logger().critical('Failed to interfacing with API server!')
                return
            if not self._slack_client.rtm_connect():
                self.get_logger().critical('Failed to start the bot client!')
                return
            self.get_logger().info('==== Slack Bot connected to server ====')
        while True:
            # Fire the timers
            for timer_id in self._timer_list:
                self._timer_list[timer_id].on_timer(timer_id, self)

            # Then process messages
            if not is_offline_mode:
                msg_list = self._slack_client.rtm_read()
                if msg_list is not None:
                    for msg in msg_list:
                        self.__process_msg(msg)
            time.sleep(delay_time)
