from BotCore import *
from BotCore.BotEngine import BotEngine as Bot


class UnhandledMsgMod(BotEngine.BotBaseMod):
    """
    This module handles unhandled messages (messages that are not handled by all other modules)
    """
    PREFS_NAME = 'unhandled_msg_mod'
    _mod_name = 'unhandled_msg_mod'
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
        if not msg[Bot.KEY_IS_MESSAGE] or Bot.KEY_RAW not in msg:
            return
        if 'channel' not in msg['raw']:
            return
        if 'user' not in msg['raw']:
            return
        user_id = msg['raw']['user'].encode('utf-8')
        if user_id == self._bot_info['id']:
            return
        user, _ = bot_core.get_member_by_id(user_id)
        if user is None or 'name' not in user:
            return
        user_name = user['name']

        channel_id = msg[Bot.KEY_RAW]['channel'].encode('utf-8')
        bot_mentioned = msg[Bot.KEY_IS_BOT_MENTIONED]

        if bot_mentioned and 'options' in self._rules and 'replay_percentage' in self._rules['options']:
            replay_percentage = int(self._rules['options']['replay_percentage'])
            if replay_percentage > 100:
                replay_percentage = 100
            if BotUtils.RandomUtils.random_int(0, 100) <= replay_percentage:
                response_text = msg['raw']['text'].encode('utf-8').replace(
                    '<@%s>' % self._bot_info['id'], '@%s' % user_name)
                response = {'text': response_text, 'channel': channel_id}
                bot_core.queue_response(response)
                return
        response_vars = {'$(user)': user_name}

        rule_name = 'mentioned' if bot_mentioned else 'not_mentioned'
        if rule_name not in self._rules:
            return
        msg_list = self._rules[rule_name]
        response_text = BotUtils.RandomUtils.random_item_in_list(msg_list)

        for var in response_vars:
            response_text = response_text.replace(var, response_vars[var])
        response = {Bot.KEY_TEXT: response_text, Bot.KEY_CHANNEL_ID: channel_id}
        bot_core.queue_response(response)
