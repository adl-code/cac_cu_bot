# coding=utf-8
from BotCore import *
from BotCore.BotEngine import BotEngine as Bot
import time
import urllib
from defusedxml.cElementTree import fromstring


class XSMB:
    """
    This class provide information of the "XSMB" lotto result
    """
    PREFS_NAME = 'xsmb'

    _start_check = None
    _end_check = None
    _check_interval = None
    _min_check_diff = 60
    _last_check = 0
    _results = {}
    _max_results = 5

    def __init__(self, config):
        self._config = config
        if 'check_time' in config:
            ct = config['check_time']
            if 'start' in ct:
                self._start_check = ct['start']
            if 'end' in ct:
                self._end_check = ct['end']
            if 'interval' in ct:
                self._check_interval = ct['interval']
        if 'min_check_diff' in config:
            self._min_check_diff = int(config['min_check_diff'])
        if 'max_results' in config:
            self._max_results = config['max_results']

    def _filter_result(self, result_list):
        """
        Filter the result list by keep the most recent items
        :param result_list: result list to filter
        :return: filtered list
        """
        if result_list is None:
            return None
        ln = len(result_list)
        if ln <= self._max_results:
            return result_list

        need_del = ln - self._max_results
        del_keys = []
        for key, _ in sorted(result_list.iteritems(), key=lambda (k, v): (k, v)):
            del_keys.append(key)
            if len(del_keys) == need_del:
                break
        for key_to_del in del_keys:
            result_list.pop(key_to_del, None)
        return result_list

    def get_results(self, bot_core, prefs):
        """
        Get the currently cached results.
        If today result not fetched yet and current time surpassed the check time frame then we should update the cache
        :param bot_core: the bot core object
        :param prefs: module preferences data
        :return: results, None if errors occurred
        """
        if self._results is None or len(self._results) == 0:
            if XSMB.PREFS_NAME in prefs and 'results' in prefs[XSMB.PREFS_NAME]:
                self._results = prefs[XSMB.PREFS_NAME]['results']
        now = time.localtime()
        today = time.strftime('%Y/%m/%d', now)

        if self._results is None or len(self._results) == 0:
            self.__query_results(bot_core, prefs)
        else:
            if today not in self._results:
                end_time = time.strftime('%Y/%m/%d ', now) + self._end_check
                t_end = time.strptime(end_time, '%Y/%m/%d %H:%M:%S')
                if now > t_end:
                    self.__query_results(bot_core, prefs)

        return self._results

    def __query_results(self, bot_core, prefs):
        """
        Download the RSS feed and update results to internal data structure and to module preferences data
        :param bot_core: the bot core object
        :param prefs: the module preferences data
        :return: results parsed from RSS feed, None if errors occurred
        """
        url = 'http://xskt.com.vn/rss-feed/mien-bac-xsmb.rss'
        result_list = self._filter_result(XSMB.__parse_rss_data(url))
        need_update_prefs = False

        if XSMB.PREFS_NAME not in prefs:
            need_update_prefs = True
            prefs[XSMB.PREFS_NAME] = {'results': {}, 'fired_timer': ''}

        if result_list is not None:
            # noinspection PyTypeChecker
            for date in result_list:
                if date not in prefs[XSMB.PREFS_NAME]:
                    # noinspection PyUnresolvedReferences
                    prefs[XSMB.PREFS_NAME]['results'][date] = result_list[date]
                    need_update_prefs = True
        if need_update_prefs:
            bot_core.get_prefs().save_prefs(LottoMod.PREFS_NAME, prefs)
        self._results = result_list

    def __query_today_result(self, bot_core, prefs):
        """
        Get today's result. If result already in cache then return it. Otherwise try to fetch results from Internet
        :param bot_core: the bot core object
        :param prefs: the module preferences data
        :return: today's result or None if errors occurred
        """
        today = time.strftime('%Y/%m/%d', time.localtime())
        # today = '2017/04/10'
        if today in self._results:
            return self._results[today]

        if XSMB.PREFS_NAME in prefs and 'results' in prefs[XSMB.PREFS_NAME]:
            self._results = prefs[XSMB.PREFS_NAME]['results']

        if today in self._results:
            return self._results[today]

        # Perform the query and then extract information
        self.__query_results(bot_core, prefs)

        if today in self._results:
            return self._results[today]
        return None

    @staticmethod
    def __parse_rss_data(url):
        """
        Parse the RSS data to get results
        :param url: url to RSS data to parse
        :return: parsed results
        """
        try:
            response = urllib.urlopen(url)
            data = response.read()
            response.close()
        except IOError:
            return None
        root = fromstring(data)
        result_list = {}
        if root.tag != 'rss':
            return None
        for child in root:
            if child.tag != 'channel':
                continue
            for item in child:
                if item.tag == 'item':
                    result = XSMB.__parse_rss_item(item)
                    if result is not None:
                        item_id = result['date']
                        result_list[item_id] = result
        return result_list

    @staticmethod
    def __parse_rss_item(item):
        """
        Parse a rss item describing a result
        :param item: item to parse
        :return: parsed result
        """
        title = None
        desc = None
        original_title = None
        for child in item:
            if child.tag == 'title':
                title = child.text.lower().encode('utf-8')
                original_title = child.text.encode('utf-8')
            elif child.tag == 'description':
                desc = child.text.lower().encode('utf-8')
        if title is None or desc is None or original_title is None:
            return None
        title_start = 'kết quả xổ số miền bắc ngày '
        pos = title.find(title_start)
        if pos != 0:
            return None
        date = title[len(title_start):len(title_start) + 5]
        if date[2] != '/':
            return None
        date = time.strftime('%Y/', time.localtime()) + date[3:] + '/' + date[:2]
        prizes = {}
        for line in desc.split('\n'):
            line = line.replace(' ', '')
            pos = line.find(':')
            if pos <= 0:
                continue
            p = line[:pos]
            if p == 'đb':
                p = "Giải đặc biệt"
                prize_id = '0'
            else:
                prize_id = p
                p = "Giải " + p
            val = line[pos + 1:].split('-')
            prizes[prize_id] = {'title': p, 'values': val}
        result = {'title': original_title, 'prizes': prizes, 'date': date}
        return result

    def on_timer(self, bot_core, prefs):
        """
        Handling timer event to periodically check for today's result
        Only perform check on a specific time frame
        :param bot_core: bot core engine
        :param prefs: module preferences data
        :return: today's result, None if errors occurred
        """
        today = time.strftime('%Y/%m/%d', time.localtime())
        if (XSMB.PREFS_NAME in prefs and 'fired_timer' in prefs[XSMB.PREFS_NAME]
                and prefs[XSMB.PREFS_NAME]['fired_timer'] == today):
                return None
        now = time.localtime()
        start_time = time.strftime('%Y/%m/%d ', now) + self._start_check
        end_time = time.strftime('%Y/%m/%d ', now) + self._end_check

        t_start = time.strptime(start_time, '%Y/%m/%d %H:%M:%S')
        t_end = time.strptime(end_time, '%Y/%m/%d %H:%M:%S')
        if t_start > now or t_end < now:
            return None
        if time.mktime(time.localtime()) - self._last_check < self._check_interval:
            return None
        result = self.__query_today_result(bot_core, prefs)
        if result is not None:
            prefs[XSMB.PREFS_NAME]['fired_timer'] = today
            bot_core.get_prefs().save_prefs(LottoMod.PREFS_NAME, prefs)

        return result


class LottoMod(BotEngine.BotBaseMod, BotEngine.BotTimer):
    """
    This module update lotto information and also provides user information when asked
    """
    PREFS_NAME = 'lotto_mod'
    LOTTO_TIMER = 'LottoMod.timer'
    _mod_name = 'lotto_mod'
    _mod_desc = 'This module update lotto information and also provides user information when asked'
    _min_check_diff = 5  # in second
    _bot_info = {}

    def __init__(self):
        self._prefs = None
        self._config = None
        self._lotto_list = []

    def __parse_config(self, config_file):
        if config_file is None:
            return
        try:
            f = open(config_file, "rt")
            data = BotConfig.JsonLoader.json_load_byteified(f)
            f.close()
        except IOError:
            return
        self._config = data
        if 'options' in self._config:
            if 'min_check_diff' in self._config['options']:
                self._min_check_diff = self._config['options']['min_check_diff']

    def __init_lotto_list(self):
        if 'lotto_items' not in self._config:
            return
        lotto_items = self._config['lotto_items']
        if 'xsmb' in lotto_items:
            xsmb = lotto_items['xsmb']
            if 'disabled' not in xsmb or not xsmb['disabled']:
                self._lotto_list.append(XSMB(xsmb))

    def __get_lotto_results(self, bot_core):
        """
        Return lotto results on demand
        :param bot_core: the bot core object
        :return: formatted message
        """
        result_list = []
        for lotto in self._lotto_list:
            result = lotto.get_results(bot_core, self._prefs)
            if result is not None:
                result_list.append(result)
        if len(result_list) == 0:
            return None
        if 'messages' not in self._config or 'on_demand' not in self._config['messages']:
            return None
        msg = Bot.random_item_in_list(self._config['messages']['on_demand'])
        msg += '\n>>>'
        for results in result_list:
            for date, result in sorted(results.iteritems(), reverse=True, key=lambda (k, v): (k, v)):
                msg += '*' + result['title'] + '*\n'
                for prize_id, prize in sorted(result['prizes'].iteritems(), key=lambda (k, v): (k, v)):
                    msg += '*' + prize['title'] + '*: '
                    msg += ' - '.join(prize['values']) + '\n'
                msg += '\n'
        return msg.strip()

    def get_mod_name(self):
        return self._mod_name

    def get_mod_desc(self):
        return self._mod_desc

    def on_registered(self, bot_core):
        config_file = bot_core.get_config().get_path('lotto_mod_config_file')
        self.__parse_config(config_file)
        self._prefs = bot_core.get_prefs().load_prefs(LottoMod.PREFS_NAME)
        if self._prefs is None:
            self._prefs = {}
        bot_core.register_timer(self, LottoMod.LOTTO_TIMER)
        self._bot_info = bot_core.get_bot_info()
        self.__init_lotto_list()
        bot_core.get_logger().debug('[%s] module initialized' % self._mod_name)

    def on_message(self, bot_core, msg):
        if not msg[Bot.KEY_IS_MESSAGE] or not msg[Bot.KEY_IS_BOT_MENTIONED]:
            return None
        channel_id = msg[Bot.KEY_CHANNEL_ID]
        if msg[Bot.KEY_FROM_USER_ID] == self._bot_info[Bot.KEY_ID]:
            return None
        subs_dict = {'$(user)': msg[Bot.KEY_FROM_USER_NAME]}

        if 'commands' not in self._config or 'result' not in self._config['commands']:
            return None
        cmd_list = self._config['commands']['result']
        cmd_found = False
        for cmd in cmd_list:
            if msg[Bot.KEY_STANDARDIZED_LOWER_TEXT].find(cmd) >= 0:
                cmd_found = True
                break
        if not cmd_found:
            return None
        if 'last_check' in self._prefs:
            last_check = self._prefs['last_check']
        else:
            last_check = 0
        now = time.mktime(time.localtime())
        if last_check + self._min_check_diff > now:
            # User asks too much
            reply_text = None
            if 'messages' in self._config and 'ask_too_much' in self._config['messages']:
                reply_text = Bot.random_item_in_list(self._config['messages']['ask_too_much'])
            if reply_text is None:
                # Return an empty object to specify that this message has been handled
                return {}
            else:
                reply_text = Bot.replace_text(reply_text, subs_dict)
                return {Bot.KEY_TEXT: reply_text, Bot.KEY_CHANNEL_ID: channel_id}

        reply = self.__get_lotto_results(bot_core)
        if reply is None:
            # Return an empty object to specify that this message has been handled
            return bot_core.queue_response({})
        reply_text = Bot.replace_text(reply, subs_dict)

        # Save preferences
        self._prefs['last_check'] = now
        bot_core.get_prefs().save_prefs(LottoMod.PREFS_NAME, self._prefs)

        # Then return response
        bot_core.get_logger().info('[%s] replying to user %s' % (self._mod_name, msg[Bot.KEY_FROM_USER_NAME]))
        return {Bot.KEY_TEXT: reply_text, Bot.KEY_CHANNEL_ID: channel_id}

    def on_timer(self, timer_id, bot_core):
        if timer_id == LottoMod.LOTTO_TIMER:
            self.__on_lotto_timer(bot_core)

    def __on_lotto_timer(self, bot_core):
        result_list = []
        for lotto in self._lotto_list:
            result = lotto.on_timer(bot_core, self._prefs)
            if result is not None:
                result_list.append(result)
        msg = self.__format_scheduled_message(result_list)
        if msg is None or 'channels' not in self._config:
            return
        for chan in self._config['channels']:
            channel = bot_core.get_channel_by_name(chan)
            if channel is None or Bot.KEY_ID not in channel:
                continue
            if 'text' in msg and 'attachments' in msg:
                response = {
                    Bot.KEY_TEXT: msg['text'],
                    Bot.KEY_CHANNEL_ID: channel[Bot.KEY_ID],
                    Bot.KEY_ATTACHMENTS: msg['attachments']}
            else:
                response = {
                    Bot.KEY_TEXT: msg,
                    Bot.KEY_CHANNEL_ID: channel[Bot.KEY_ID]}
            bot_core.get_logger().info('[%s] displaying results as scheduled' % self._mod_name)
            bot_core.queue_response(response)

    def __format_scheduled_message(self, result_list):
        """
        Format lotto result as scheduled
        :param result_list: result list
        :return: formatted message
        """
        if result_list is None or len(result_list) == 0:
            return None
        msg = {}
        if 'messages' in self._config and 'timer' in self._config['messages']:
            msg['text'] = Bot.random_item_in_list(self._config['messages']['timer'])
        attachments = []
        for result in result_list:
            attach = {'title': result['title'], 'text': result['date']}
            fields = []
            for prize_id, prize in sorted(result['prizes'].iteritems(), key=lambda (k, v): (k, v)):
                field = {
                    'title': prize['title'],
                    'value': ' - '.join(prize['values']),
                    'short': len(prize['values']) <= 3}
                fields.append(field)
            attach['fields'] = fields
            attachments.append(attach)
        msg['attachments'] = attachments
        return msg
