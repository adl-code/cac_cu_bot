from BotCore import *
from BotCore.BotEngine import BotEngine as Bot
import time
import datetime


IDLE_TIMER = "IdleMode.timer"


class IdleMod(BotEngine.BotBaseMod, BotEngine.BotTimer):
    """
    This module allows bot to chit-chat when people are idle
    
    """
    PREFS_NAME = "idle_mod"

    _mod_name = 'idle_mod'
    _mod_desc = "IdleMod give comments to idle users"
    _time_frames = {}
    _messages = {}
    _active_channels = {}
    _active_users = {}
    _prefs = None
    _check_interval = 5  # seconds
    _max_time_diff = 10  # seconds
    _response_time_diff = 10  # seconds
    _bot_id = None
    _force_update_after = 3600  # 1 hour

    def __init__(self):
        self._last_idle_timer_fired = time.time()

    def get_mod_name(self):
        return self._mod_name

    def get_mod_desc(self):
        return self._mod_desc

    def __parse_config(self, config_file):
        if config_file is None:
            return
        try:
            f = open(config_file, "rt")
            data = BotConfig.JsonLoader.json_load_byteified(f)
            f.close()
        except IOError:
            data = None
        if data is None:
            return
        if 'time_frames' in data:
            self._time_frames = data['time_frames']

        if 'messages' in data:
            self._messages = data['messages']

        if 'active_channels' in data:
            for channel in data['active_channels']:
                self._active_channels[channel] = {}

        if 'active_users' in data:
            for user in data['active_users']:
                self._active_users[user] = {}

        if 'config' in data:
            if 'check_interval' in data['config']:
                self._check_interval = data['config']['check_interval']
            if 'max_time_diff' in data['config']:
                self._max_time_diff = data['config']['max_time_diff']
            if 'response_time_diff' in data['config']:
                self._response_time_diff = data['config']['response_time_diff']
            if 'force_update_after' in data['config']:
                self._force_update_after = data['config']['force_update_after']

    def on_registered(self, bot_core):
        """        
        Initialized the module right after it has been registered with the core
        :param bot_core:
        :return: None
        """
        self.__parse_config(bot_core.get_config().get_path('idle_mod_config_file'))
        self._prefs = bot_core.get_prefs().load_prefs(IdleMod.PREFS_NAME)
        if self._prefs is None:
            self._prefs = {}
        bot = bot_core.get_bot_info()
        if bot is not None and Bot.KEY_ID in bot:
            self._bot_id = bot[Bot.KEY_ID]
        bot_core.register_timer(self, IDLE_TIMER, self._check_interval)
        bot_core.get_logger().debug('[%s] module initialized' % self._mod_name)

    def on_message(self, bot_core, msg):
        """
        Process messages
        :param bot_core: the core engine 
        :param msg:  the message
        :return:  reply message, None to skip replying this message 
        """
        if not msg[Bot.KEY_IS_MESSAGE]:
            return None
        raw_msg = msg[Bot.KEY_RAW]
        if 'channel' not in raw_msg or 'user' not in raw_msg or 'ts' not in raw_msg:
            return None
        channel = raw_msg['channel'].encode('utf-8')
        user = raw_msg['user'].encode('utf-8')
        if user == self._bot_id:
            return None
        t = time.mktime(time.localtime(float(raw_msg['ts'])))
        need_update_prefs = False
        if 'channel_latest_msg_ts' not in self._prefs:
            self._prefs['channel_latest_msg_ts'] = {}
            need_update_prefs = True
        if channel not in self._prefs['channel_latest_msg_ts']:
            self._prefs['channel_latest_msg_ts'][channel] = {'latest': t, 'users': {user: t}}
            need_update_prefs = True
        else:
            if self._prefs['channel_latest_msg_ts'][channel]['latest'] < t:
                self._prefs['channel_latest_msg_ts'][channel]['latest'] = t
                need_update_prefs = True

            if (user not in self._prefs['channel_latest_msg_ts'][channel]['users'] or
                    self._prefs['channel_latest_msg_ts'][channel]['users'][user] < t):
                self._prefs['channel_latest_msg_ts'][channel]['users'][user] = t
                need_update_prefs = True
        if need_update_prefs:
            bot_core.get_prefs().save_prefs(IdleMod.PREFS_NAME, self._prefs)
        return None

    def on_timer(self, timer_id, bot_core):
        if timer_id == IDLE_TIMER:
            self.__on_idle_timer(bot_core)

    def __check_time_frame(self, channel_info, tf, bot_core):
        now = datetime.datetime.now()

        # Validate frame
        if 'start' not in tf or 'end' not in tf or 'name' not in tf:
            return None

        # Skip disabled time frame
        if 'disabled' in tf and tf['disabled']:
            return None

        # Skip already processed frame
        if tf['name'] in self._prefs['processed_frames'] and self._prefs['processed_frames'][tf['name']]:
            return None

        start_time = now.strftime('%Y-%m-%d ') + tf['start']
        end_time = now.strftime('%Y-%m-%d ') + tf['end']
        now_time = now.strftime('%Y-%m-%d %H:%M:%S')

        t_start = time.mktime(time.strptime(start_time, '%Y-%m-%d %H:%M:%S'))
        t_end = time.mktime(time.strptime(end_time, '%Y-%m-%d %H:%M:%S'))
        t_now = time.mktime(time.strptime(now_time, '%Y-%m-%d %H:%M:%S'))

        t_latest = channel_info['latest']

        if 'no_msg' in tf and t_end < t_now <= (t_end + self._max_time_diff) and t_latest < t_start:
            # There is no log in this channel in this time frame
            return {'reply': tf['no_msg'], 'type': 'no_msg'}

        if 'has_msg' in tf:
            latest_user = None
            latest_t_user = -1
            for user in channel_info['users']:
                t_user = channel_info['users'][user]
                if t_start < t_user < t_end:
                    if t_user > latest_t_user:
                        latest_t_user = t_user
                        latest_user = user
            if latest_user is not None:
                user, _ = bot_core.get_member_by_id(latest_user)
                if user is not None and 'name' in user:
                    return {'reply': tf['has_msg'], 'vars': {'$(user)': user['name']}, 'type': 'has_msg'}
        return None

    def __process_time_frame_result(self, channel_id, tf, result, bot_core):
        if result is None or 'reply' not in result:
            bot_core.get_logger.warning('[%s] reply not found' % self._mod_name)
            return
        reply = result['reply']
        if 'message' not in reply or reply['message'] not in self._messages:
            bot_core.get_logger.warning('[%s] reply message not found' % self._mod_name)
            return

        msg_list = self._messages[reply['message']]
        reply_msg = BotUtils.RandomUtils.random_item_in_list(msg_list)

        if 'vars' in result:
            for var in result['vars']:
                reply_msg = reply_msg.replace(var, result['vars'][var].encode('utf-8'))
        allow_sending = False
        if 'last_post' not in self._prefs or (time.time() - self._prefs['last_post']) > self._response_time_diff:
            allow_sending = True
        if not allow_sending:
            return
        response = {Bot.KEY_TEXT: reply_msg, Bot.KEY_CHANNEL_ID: channel_id}
        bot_core.queue_response(response)
        self._prefs['last_post'] = time.time()
        self._prefs['processed_frames'][tf['name']] = True
        bot_core.get_prefs().save_prefs(IdleMod.PREFS_NAME, self._prefs)
        bot_core.get_logger().info('[%s] post reply to %s:%s' % (self._mod_name, tf['name'], result['type']))

    def __query_channel_info(self, channel_id, bot_core):
        if 'channel_latest_msg_ts' not in self._prefs:
            self._prefs['channel_latest_msg_ts'] = {}
        chan_info = bot_core.query_channel_info_by_id(channel_id)
        if chan_info is None or 'latest' not in chan_info:
            return
        latest = chan_info['latest']
        if 'user' not in latest or 'ts' not in latest:
            return
        user = latest['user'].encode('utf-8')
        ts = time.mktime(time.localtime(float(latest['ts'])))
        self._prefs['channel_latest_msg_ts'][channel_id] = {'latest': ts, 'users': {user: ts}}
        bot_core.get_prefs().save_prefs(IdleMod.PREFS_NAME, self._prefs)

    def __on_idle_timer(self, bot_core):
        if self._prefs is None:
            self._prefs = bot_core.get_prefs().load_prefs(IdleMod.PREFS_NAME)
            if self._prefs is None:
                self._prefs = {}
        if 'working_day' in self._prefs:
            working_day = self._prefs['working_day']
        else:
            working_day = ''

        today = datetime.date.today().strftime('%Y-%m-%d')
        if working_day != today:
            self._prefs['working_day'] = today
            self._prefs['processed_frames'] = {}
            bot_core.get_prefs().save_prefs(IdleMod.PREFS_NAME, self._prefs)

        if 'processed_frames' not in self._prefs:
            self._prefs['processed_frames'] = {}
            bot_core.get_prefs().save_prefs(IdleMod.PREFS_NAME, self._prefs)

        self._last_idle_timer_fired = time.time()
        # bot_core.get_logger().debug('[%s] Idle timer fired' % self._mod_name)
        for channel in self._time_frames:
            if channel not in self._active_channels:
                continue
            ch = bot_core.get_channel_by_name(channel)
            if ch is None or 'id' not in ch:
                continue
            channel_id = ch['id']
            force_update = False
            if ('channel_latest_msg_ts' in self._prefs and
                channel_id in self._prefs['channel_latest_msg_ts'] and
                    'latest' in self._prefs['channel_latest_msg_ts'][channel_id]):
                latest = self._prefs['channel_latest_msg_ts'][channel_id]['latest']
                if latest + self._force_update_after <= time.mktime(time.localtime()):
                    force_update = True
            else:
                force_update = True
            if force_update:
                self.__query_channel_info(channel_id, bot_core)
            if channel_id not in self._prefs['channel_latest_msg_ts']:
                continue
            channel_info = self._prefs['channel_latest_msg_ts'][channel_id]
            for tf in self._time_frames[channel]:
                result = self.__check_time_frame(channel_info, tf, bot_core)
                if result is not None:
                    self.__process_time_frame_result(channel_id, tf, result, bot_core)
                    break
