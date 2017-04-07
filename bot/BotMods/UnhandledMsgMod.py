from BotCore import *
import random


class UnhandledMsgMod(BotEngine.BotBaseMod):
    """
    This module handles unhandled messages (messages that are not handled by all other modules)
    """
    PREFS_NAME = 'UnhandledMsgMod'
    _mod_name = 'UnhandledMsgMod'
    _mod_desc = 'This module handles unhandled messages (messages that are not handled by all other modules)'
    _rules = {}
    _bot_info = None

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
        if data is not None:
            self._rules = data

    def on_registered(self, bot_core):
        self.__parse_config(bot_core.get_config().get_path('unhandled_msg_mod_config_file'))
        self._bot_info = bot_core.get_bot_info()
        bot_core.get_logger().info('[%s] module initialized' % self._mod_name)

    def on_message(self, bot_core, msg):
        if not msg['is_message'] or 'raw' not in msg:
            return
        if 'channel' not in msg['raw']:
            return
        if 'user' not in msg['raw'] or msg['raw']['user'] == self._bot_info['id']:
            return
        rule_name = 'mentioned' if msg['is_bot_mentioned'] else 'not_mentioned'
        if rule_name not in self._rules:
            return
        msg_list = self._rules[rule_name]
        response_text = msg_list[random.randrange(0, len(msg_list) - 1)]
        response = {'text': response_text, 'channel': msg['raw']['channel'].encode('utf-8')}
        bot_core.queue_response(response)
