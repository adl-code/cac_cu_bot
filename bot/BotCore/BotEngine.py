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
    PREFS_NAME = "bot_engine"
    REFRESH_CHANNEL_HISTORY_TIMEOUT = 10

    _member_list = {}
    _member_list_name = {}
    _channel_list = {}
    _channel_list_name = {}
    _bot_info = {}
    _timer_list = {}
    _slack_client = None
    _response_queue = []
    _channel_info = {}
    _channel_info_name = {}
    _bot_prefs = None
    _channel_history = {}
    _post_delay = 10
    _refresh_time = 5
    _prefs = {}

    def __init__(self, config_file):
        self._bot_config = BotConfig(config_file)
        self._bot_prefs = BotPrefs(os.path.join(os.getcwd(), '.prefs'))
        self._mod_list = []

        # Initialize logger
        self.__init_logger()

        self.__load_config()

        self.get_logger().info('================= STARTING BOT ===================')

        # Initialize user list
        self.__init_user_list()

        # Initialize member list, channel list ...
        self.__init_slack_client()
        self.refresh_member_list()
        self.refresh_channel_list()

        info = self.get_config().get_timeout('refresh_channel_history')
        if info is None:
            info = BotEngine.REFRESH_CHANNEL_HISTORY_TIMEOUT
        self._refresh_channel_history_timeout = info

    def __load_config(self):
        val = self.get_config().get_timeout('engine_post_delay')
        if val is not None:
            self._post_delay = int(val)
        val = self.get_config().get_timeout('engine_refresh_time')
        if val is not None:
            self._refresh_time = int(val)

        self._prefs = self.get_prefs().load_prefs(BotEngine.PREFS_NAME)
        if self._prefs is None:
            self._prefs = {'last_response': 0}

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

    def refresh_member_list(self):
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
                        self._bot_info['name'] = user_name.encode('utf-8')
                        self._bot_info['id'] = user_id.encode('utf-8')
                        self._bot_info['raw'] = user
                        self.get_logger().debug('Bot name = %s, ID = %s' % (user_name, user_id))
                    else:
                        member = {
                            'name': user_name.encode('utf-8'),
                            'id': user_id.encode('utf-8'),
                            'raw': user}
                        self._member_list[user_id] = member
                        self._member_list_name[user_name] = member
                        self.get_logger().debug('Member name = %s, ID = %s' % (user_name, user_id))

    def refresh_channel_list(self):
        if self._slack_client is None:
            return
        api_call = self._slack_client.api_call("channels.list")
        if api_call is not None and api_call.get('ok'):
            channels = api_call.get('channels')
            for channel in channels:
                if 'id' not in channel or 'name' not in channel:
                    continue
                chan = {
                    'name': channel['name'].encode('utf-8'),
                    'id': channel['id'].encode('utf-8'),
                    'raw': channel
                }
                self._channel_list[chan['id']] = chan
                self._channel_list_name[chan['name']] = chan
                self.get_logger().debug('Channel name = %s, ID = %s' % (chan['name'], chan['id']))
        api_call = self._slack_client.api_call("groups.list")
        if api_call is not None and api_call.get('ok'):
            channels = api_call.get('groups')
            for channel in channels:
                if 'id' not in channel or 'name' not in channel:
                    continue
                chan = {
                    'name': channel['name'].encode('utf-8'),
                    'id': channel['id'].encode('utf-8'),
                    'raw': channel
                }
                self._channel_list[chan['id']] = chan
                self._channel_list_name[chan['name']] = chan
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

    def get_prefs(self):
        return self._bot_prefs

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
        return self._bot_info

    def get_member_list(self):
        return self._member_list

    def get_member_by_id(self, member_id):
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

    def get_member_by_name(self, member_name):
        if member_name is None or member_name not in self._member_list_name:
            return None, None
        member = self._member_list_name[member_name]
        if self._user_list is not None and member_name in self._user_list:
            user = self._user_list[member_name]
        else:
            user = None
        return member, user

    def query_channel_info_by_id(self, channel_id, force=False):
        if channel_id is None:
            return None
        if channel_id in self._channel_info and not force:
            return self._channel_info[channel_id]

        if self._slack_client is None:
            return None
        is_group = False
        chan_info = self._slack_client.api_call("channels.info", channel=channel_id)
        if chan_info is None or not chan_info.get('ok'):
            chan_info = self._slack_client.api_call("groups.info", channel=channel_id)
            is_group = True
        if chan_info is not None and chan_info.get('ok'):
            the_channel = chan_info.get('group' if is_group else 'channel')
            self._channel_info[channel_id] = the_channel
            self._channel_info_name[the_channel['name']] = the_channel
            return self._channel_info[channel_id]
        else:
            return None

    def query_channel_info_by_name(self, channel_name, force=False):
        if channel_name is None:
            return None
        if channel_name in self._channel_info_name and not force:
            return self._channel_info_name[channel_name]
        if self._slack_client is None:
            return None
        if channel_name not in self._channel_list_name:
            return None
        channel_id = self._channel_list_name[channel_name]['id']

        is_group = False
        chan_info = self._slack_client.api_call("channels.info", channel=channel_id)
        if chan_info is None or not chan_info.get('ok'):
            chan_info = self._slack_client.api_call("groups.info", channel=channel_id)
            is_group = True
        if chan_info is not None and chan_info.get('ok'):
            the_channel = chan_info.get('group' if is_group else 'channel')
            self._channel_info[channel_id] = the_channel
            self._channel_info_name[the_channel['name']] = the_channel
            return self._channel_info[channel_id]
        else:
            return None

    def get_channel_by_id(self, channel_id):
        if channel_id is None or channel_id not in self._channel_list:
            return None
        return self._channel_list[channel_id]

    def get_channel_by_name(self, channel_name):
        if channel_name is None or channel_name not in self._channel_list_name:
            return None
        return self._channel_list_name[channel_name]

    def query_channel_history_by_name(self, channel_name, force=False, **kwargs):
        """
        Get channel message history by channel name
        :param channel_name: channel name to query information 
        :param force: force refresh channel history
        :return: channel history
        """
        need_refresh = False
        if channel_name is None or channel_name == '':
            return None

        if channel_name not in self._channel_list_name:
            return None
        channel_id = self._channel_info_name[channel_name]['id']

        if force:
            need_refresh = True
        else:
            if channel_id in self._channel_history:
                last_refresh = self._channel_history[channel_id]['last_refresh']
                if time.time() - last_refresh > self._refresh_channel_history_timeout:
                    need_refresh = True
            else:
                need_refresh = True
        if not need_refresh:
            return self._channel_history[channel_id]['history']

        if self._slack_client is None:
            return None
        result = self._slack_client.api_call('channels.history', channel=channel_id, **kwargs)
        if result is not None and result.get('ok'):
            self._channel_history[channel_id]['history'] = result
            self._channel_history[channel_id]['last_refresh'] = time.time()
            return result
        else:
            return None

    def register_timer(self, timer_obj, timer_id):
        if timer_id is None or timer_obj is None:
            return
        self._timer_list[timer_id] = timer_obj

    def queue_response(self, response):
        if response is not None:
            self._response_queue.append(response)

    def insert_top_response(self, response):
        if response is not None:
            self._response_queue.insert(0, response)

    def __preprocess_msg(self, msg):
        the_msg = {'raw': msg}
        # Try tokenizing the message
        if 'type' in msg and msg['type'] == 'message' and 'subtype' not in msg:
            the_msg['is_message'] = True
            bot_mentioned = False
            if 'text' in msg:
                the_msg['raw_words'] = [s.encode('utf-8') for s in msg['text'].split()]
                the_msg['standardized'] = ' '.join(the_msg['raw_words'])
                the_msg['words'] = map(str.lower, the_msg['raw_words'])
                for word in the_msg['words']:
                    if word == '<@' + self._bot_info['name'] + '>' or word == self._bot_info['name']:
                        bot_mentioned = True
                        break
                if not bot_mentioned:
                    for word in the_msg['raw_words']:
                        if word == '<@' + self._bot_info['id'] + '>':
                            bot_mentioned = True
                            break
            the_msg['is_bot_mentioned'] = bot_mentioned
        else:
            the_msg['is_message'] = False

        return the_msg

    def __response(self, response):
        if response is None or 'text' not in response or 'channel' not in response:
            return None
        text = response['text']
        channel = response['channel']
        if 'last_response' in self._prefs:
            last_response = self._prefs['last_response']
        else:
            last_response = 0
        if self._slack_client is None or time.time() - last_response < self._post_delay:
            return response
        self._slack_client.api_call('chat.postMessage',
                                    channel=channel,
                                    text=text,
                                    as_user=True,
                                    parse='full',
                                    link_names=True)
        self._prefs['last_response'] = time.time()
        return None

    def __process_msg(self, msg):
        the_msg = self.__preprocess_msg(msg)
        if the_msg is None:
            return
        for mod in self._mod_list:
            response = mod.on_message(self, the_msg)
            if response is not None:
                # One of the module has response
                self.insert_top_response(response)
                return

    def run(self):
        """
        Execute the main bot thread
        :return: None
        """
        is_offline_mode = self.get_config().should_be_offline()
        if is_offline_mode:
            self.get_logger().info('Slack Bot running in OFFLINE mode')
        else:
            if self._slack_client is None:
                self.get_logger().critical('Failed to interfacing with API server!')
                return
            if not self._slack_client.rtm_connect():
                self.get_logger().critical('Failed to start the bot client!')
                return
            self.get_logger().info('Slack Bot connected to server')
        while True:
            # Fire the timers
            for timer_id in self._timer_list:
                self._timer_list[timer_id].on_timer(timer_id, self)

            # Then process messages
            if not is_offline_mode:
                msg_list = self._slack_client.rtm_read()
                if msg_list is not None and len(msg_list) > 0:
                    for msg in msg_list:
                        self.__process_msg(msg)

            # Then send queued response
            if not is_offline_mode:
                not_processed_list = []
                for response in self._response_queue:
                    result = self.__response(response)
                    if result is not None:
                        not_processed_list.append(result)
                self._response_queue = not_processed_list
            time.sleep(self._refresh_time)
