from BotCore import *
import time
import re
from BotCore.BotEngine import BotEngine as bot


class FinanceMod(BotEngine.BotBaseMod, BotEngine.BotTimer):
    """
    This class provides finance information such as exchange rate ...
    """
    exchange_rates_TIMER = 'FinanceMod.ExchangeRateTimer'
    PREFS_NAME = 'finance_mod'
    MOD_NAME = 'finance_mod'
    MOD_DESC = 'This class provides finance information such as exchange rate ...'

    _check_interval = 5  # in seconds
    _time_frames = {}
    _prefs = []
    _channels = []
    _config = None
    _messages = None

    def __init__(self):
        pass

    def get_mod_name(self):
        return self.MOD_NAME

    def get_mod_desc(self):
        return self.MOD_DESC

    def on_timer(self, timer_id, bot_core):
        today = time.strftime('%Y/%m/%d', time.localtime())
        if 'working_day' not in self._prefs or today != self._prefs['working_day']:
            self._prefs['working_day'] = today
            self._prefs['processed_frames'] = {}
            bot_core.get_prefs().save_prefs(FinanceMod.PREFS_NAME, self._prefs)
        if timer_id == FinanceMod.exchange_rates_TIMER:
            self.__on_exchange_rates_timer(bot_core)

    def on_registered(self, bot_core):
        self.__parse_config(bot_core.get_config().get_path('finance_mod_config_file'))
        self._prefs = bot_core.get_prefs().load_prefs(FinanceMod.PREFS_NAME)
        if self._prefs is None:
            self._prefs = {}
        bot_core.register_timer(self, FinanceMod.exchange_rates_TIMER, self._check_interval)
        bot_core.get_logger().info('[%s] module initialized' % FinanceMod.MOD_NAME)

    def on_message(self, bot_core, msg):
        pass

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
            options = self._config['options']
            if 'check_interval' in options:
                self._check_interval = options['check_interval']
            if 'channels' in options:
                self._channels = options['channels']
        if 'time_frames' in self._config:
            self._time_frames = self._config['time_frames']
        if 'messages' in self._config:
            self._messages = self._config['messages']

    def __on_exchange_rates_timer(self, bot_core):
        if 'exchange_rates' not in self._time_frames:
            return
        time_frames = self._time_frames['exchange_rates']
        for time_frame in time_frames:
            self.__process_exchange_rates_time_frame(bot_core, time_frame)

    def __check_time_frame(self, time_frame):
        if 'id' in time_frame:
            time_id = time_frame['id']
        else:
            return False

        if 'start' in time_frame:
            start_time = time_frame['start']
        else:
            return False

        if 'end' in time_frame:
            end_time = time_frame['end']
        else:
            return False

        if 'disabled' in time_frame and time_frame['disabled']:
            return False

        if 'processed_frames' in self._prefs:
            # Skip already-processed frame
            if time_id in self._prefs['processed_frames'] and self._prefs['processed_frames'][time_id]:
                return False
        else:
            self._prefs['processed_frames'] = {}
        now = time.localtime()
        today = time.strftime('%Y/%m/%d', now)
        t_start = time.mktime(time.strptime(today + ' ' + start_time, '%Y/%m/%d %H:%M:%S'))
        t_end = time.mktime(time.strptime(today + ' ' + end_time, '%Y/%m/%d %H:%M:%S'))
        t_now = time.mktime(now)
        if t_start > t_now or t_end < t_now:
            # Not in this time frame
            return False
        return True

    def __process_exchange_rates_time_frame(self, bot_core, time_frame):
        if not self.__check_time_frame(time_frame):
            return False
        today = time.strftime('%Y/%m/%d ', time.localtime())
        if 'results' in self._prefs and today in self._prefs['results'][today]:
            result = self._pres['results'][today]
        else:
            result = FinanceMod.__query_exchange_rates()
            if result is not None and today == result['date']:
                if 'results' not in self._prefs:
                    self._prefs['results'] = {}
                self._prefs['results'][today] = result
                bot_core.get_prefs().save_prefs(FinanceMod.PREFS_NAME, self._prefs)
        if result is not None:
            self.__response_today_result(bot_core, result)
            # Mark this time frame as processed
            # self._prefs['processed_frames'][today] = True
            # bot_core.get_prefs().save_prefs(FinanceMod.PREFS_NAME, self._prefs)

    @staticmethod
    def __extract_rate_column_data(col):
        if 'data' in col:
            return col['data']
        if 'children' in col:
            for child in col['children']:
                data = FinanceMod.__extract_rate_column_data(child)
                if data is not None:
                    return data
        else:
            return None

    @staticmethod
    def __parse_exchange_rate_table(xchg_table):
        tbl = []
        column_cnt = 0
        for r in xchg_table:
            # Parsing row
            if r['tag'] != 'tr':
                continue
            row_item = []
            cols = r['children']
            for c in cols:
                # Parsing column
                if c['tag'] != 'td':
                    return
                data = FinanceMod.__extract_rate_column_data(c)
                if data is not None:
                    row_item.append(data)

            if len(row_item) != column_cnt and column_cnt != 0:
                continue
            if column_cnt == 0:
                column_cnt = len(row_item)
            tbl.append(row_item)
        return tbl

    @staticmethod
    def __downlooad_exchange_rates():
        # url = 'https://www.vietcombank.com.vn/exchangerates/ExrateXLS.aspx'
        # result = BotEngine.BotDownloader.download_to_string(url)
        try:
            with open('exrate.htm', 'rb') as f:
                result = f.read()
                f.close()
        except IOError:
            result = None
        if result is None:
            return None
        parser = BotUtils.HtmlSimpleParser(result)
        root = parser.get_root()
        if root is None:
            return None
        return root

    @staticmethod
    def __query_exchange_rates():
        raw_data = FinanceMod.__downlooad_exchange_rates()
        if raw_data is None:
            return
        children = raw_data['children']
        title = None
        table = None
        date = None
        for child in children:
            if re.match(r'h[1-9]', child['tag']) is not None:
                if re.match(r'.* [0-9]{2}/[0-9]{2}/[0-9]{4}$', child['data']) is not None:
                    date = time.strptime(child['data'][-10:], '%d/%m/%Y')
                    title = child['data']
            elif child['tag'] == 'table':
                table = FinanceMod.__parse_exchange_rate_table(child['children'])
        if title is None or table is None or date is None:
            return None
        date = time.strftime('%Y/%m/%d', date)
        return {'title': title, 'rates': table, 'date': date}

    def __response_today_result(self, bot_core, result):
        if 'exchange_rates' not in self._messages or 'info' not in self._messages['exchange_rates']:
            return
        if 'rates' not in result or 'title' not in result:
            return
        msg_list = self._messages['exchange_rates']['info']
        reply_text = BotUtils.RandomUtils.random_item_in_list(msg_list) + '\n>>>'
        reply_text += '*%s*\n\n' % result['title']
        rate_table = result['rates']
        rate_cnt = len(rate_table) - 1
        fields = rate_table[0]
        field_cnt = len(fields)
        for i in range(rate_cnt):
            rate = rate_table[i + 1]
            reply_text += '%s: *%s*, %s: *%s*\n' % (fields[0], rate[0], fields[1], rate[1])
            reply_text += ', '.join(['%s: *%s*' % (fields[j], rate[j]) for j in range(2, field_cnt)])
            if i < rate_cnt - 1:
                reply_text += '\n\n'
        bot_core.queue_response({bot.KEY_TEXT: reply_text, bot.KEY_CHANNEL_ID: channel_id})
