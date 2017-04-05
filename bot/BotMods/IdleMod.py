from BotCore import *
import time

IDLE_TIMER = "IdleMode.timer"
IDLE_TIMER_ELAPSE = 5  # seconds


class IdleMod(BotEngine.BotBaseMod, BotEngine.BotTimer):
    """
    This module allows bot to chit-chat when people are idle
    
    """
    _mod_name = 'idle_mod'
    _mod_desc = "IdleMod give comments to idle users"
    _time_frame = {}

    def __init__(self):
        self._last_idle_timer_fired = time.time()

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
        self._time_frame = {}

    def on_registered(self, bot_core):
        """        
        Initialized the module right after it has been registered with the core
        :param bot_core:
        :return: None      
        """
        bot_core.register_timer(self, IDLE_TIMER)
        self.__parse_config(bot_core.get_config().get_path('idle_mod_config_file'))
        bot_core.get_logger().debug('[%s] Module initialized' % self._mod_name)

    def on_message(self, bot_core, msg):
        """
        Process messages
        :param bot_core: the core engine 
        :param msg:  the message
        :return:  reply message, None to skip replying this message 
        """
        return None

    def on_timer(self, timer_id, bot_core):
        if timer_id == IDLE_TIMER:
            self.on_idle_timer(bot_core)

    def on_idle_timer(self, bot_core):
        elapsed = time.time() - self._last_idle_timer_fired
        if elapsed > IDLE_TIMER_ELAPSE:
            self._last_idle_timer_fired = time.time()
            bot_core.get_logger().debug('[%s] Idle timer fired' % self._mod_name)
