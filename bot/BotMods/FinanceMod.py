from BotCore import *
import time
import re
from BotCore.BotEngine import BotEngine as Bot
from copy import copy


class FinanceMod(BotEngine.BotBaseMod, BotEngine.BotTimer):
    """
    This class provides finance information such as exchange rate ...
    """
    exchange_rates_TIMER = 'FinanceMod.ExchangeRateTimer'
    PREFS_NAME = 'finance_mod'
    MOD_NAME = 'finance_mod'
    MOD_DESC = 'This class provides finance information such as exchange rate ...'
    MAX_RESULTS = 3
    MAX_ATTACHMENTS = 5

    _check_interval = 5  # in seconds
    _time_frames = {}
    _prefs = []
    _channels = []
    _config = None
    _messages = None
    _bot_info = {}
    _min_check_diff = 10

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
            if 'result' in self._prefs:
                del self._prefs['result']
            bot_core.get_prefs().save_prefs(FinanceMod.PREFS_NAME, self._prefs)
        if timer_id == FinanceMod.exchange_rates_TIMER:
            self.__on_exchange_rates_timer(bot_core)

    def on_registered(self, bot_core):
        self.__parse_config(bot_core.get_config().get_path('finance_mod_config_file'))
        self._prefs = bot_core.get_prefs().load_prefs(FinanceMod.PREFS_NAME)
        if self._prefs is None:
            self._prefs = {}
        self._bot_info = bot_core.get_bot_info()
        bot_core.register_timer(self, FinanceMod.exchange_rates_TIMER, self._check_interval)
        ts = time.strftime('%H:%M:%S', time.localtime())
        bot_core.get_logger().info('[%s] module initialized at %s' % (FinanceMod.MOD_NAME, ts))

    def on_message(self, bot_core, msg):
        if not msg[Bot.KEY_IS_MESSAGE] or not msg[Bot.KEY_IS_BOT_MENTIONED]:
            return None
        channel_id = msg[Bot.KEY_CHANNEL_ID]
        if msg[Bot.KEY_FROM_USER_ID] == self._bot_info[Bot.KEY_ID]:
            return None
        subs_dict = {'$(user)': msg[Bot.KEY_FROM_USER_NAME]}

        if 'commands' not in self._config:
            return None

        commands = self._config['commands']

        if 'exchange_rates' in commands:
            xchg_cmds = commands['exchange_rates']
            return self.__on_exchange_commands(xchg_cmds, msg, channel_id, bot_core, subs_dict)

        return None

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
            if 'min_check_diff' in options:
                self._min_check_diff = options['min_check_diff']
        if 'time_frames' in self._config:
            self._time_frames = self._config['time_frames']
        if 'messages' in self._config:
            self._messages = self._config['messages']

    def __on_exchange_rates_timer(self, bot_core):
        if 'exchange_rates' not in self._time_frames or len(self._channels) == 0:
            return
        time_frames = self._time_frames['exchange_rates']
        filters = None
        for time_frame in time_frames:
            for ch in self._channels:
                channel = bot_core.get_channel_by_name(ch)
                if channel is not None and Bot.KEY_ID in channel:
                    channel_id = channel[Bot.KEY_ID]
                    if self.__check_time_frame(channel_id, time_frame):
                        response = self.__process_exchange_rates(bot_core, channel_id, filters)
                        if response is not None:
                            # Mark this time frame as processed
                            bot_core.get_logger().info('[%s] display exchange rates in %s to channel %s'
                                                       % (self.MOD_NAME, time_frame['id'], channel[Bot.KEY_NAME]))
                            self._prefs['processed_frames'][channel_id][time_frame['id']] = True
                            bot_core.get_prefs().save_prefs(FinanceMod.PREFS_NAME, self._prefs)
                            bot_core.queue_response(response)

    def __on_exchange_commands(self, xchg_cmds, msg, channel_id, bot_core, subs_dict):
        phrase = None
        for cmd in xchg_cmds:
            pos = msg[Bot.KEY_STANDARDIZED_LOWER_TEXT].find(cmd)
            if pos >= 0:
                if pos > 0:
                    phrase = msg[Bot.KEY_STANDARDIZED_LOWER_TEXT][:pos]
                else:
                    phrase = ''
                phrase += msg[Bot.KEY_STANDARDIZED_LOWER_TEXT][pos + len(cmd):]
                break
        if phrase is None:
            return None

        if 'last_check_exchange_rates' in self._prefs:
            last_check = self._prefs['last_check_exchange_rates']
        else:
            last_check = 0
        now = time.mktime(time.localtime())
        if last_check + self._min_check_diff > now:
            # User asks too much
            reply_text = None
            if 'exchange_rates' in self._messages and 'ask_too_much' in self._messages['exchange_rates']:
                reply_text = BotUtils.RandomUtils.random_item_in_list(self._messages['exchange_rates']['ask_too_much'])
            if reply_text is None:
                # Return an empty object to specify that this message has been handled
                return {}
            else:
                reply_text = Bot.replace_text(reply_text, subs_dict)
                return {Bot.KEY_TEXT: reply_text, Bot.KEY_CHANNEL_ID: channel_id}

        i_start = -1
        filters = []
        for i in range(len(phrase)):
            if phrase[i].isalpha():
                if i_start < 0:
                    i_start = i
            else:
                if i > i_start >= 0:
                    filters.append(phrase[i_start:i])
                i_start = -1
        if i_start >= 0:
            filters.append(phrase[i_start:])
        response = self.__process_exchange_rates(bot_core, channel_id, filters)
        if response is None:
            return None
        # Mark this time frame as processed
        chan = bot_core.get_channel_by_id(channel_id)
        if chan is not None and Bot.KEY_NAME in chan:
            channel_name = chan[Bot.KEY_NAME]
        else:
            channel_name = channel_id
        bot_core.get_logger().info(
            '[%s] response to exchange rates request to channel %s' % (self.MOD_NAME, channel_name))
        bot_core.queue_response(response)
        # Save preferences
        self._prefs['last_check_exchange_rates'] = now
        bot_core.get_prefs().save_prefs(FinanceMod.PREFS_NAME, self._prefs)

    def __check_time_frame(self, channel_id, time_frame):
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
            processed = self._prefs['processed_frames']
            if channel_id in processed:
                if time_id in processed[channel_id] and processed[channel_id][time_id]:
                    return False
            else:
                self._prefs['processed_frames'][channel_id] = {}
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

    def __process_exchange_rates(self, bot_core, channel_id, filters):
        today = time.strftime('%Y/%m/%d', time.localtime())
        result = None
        if 'result' in self._prefs:
            if self._prefs['result']['date'] == today:
                result = self._prefs['result']
            else:
                del self._prefs['result']
        if result is None:
            result = FinanceMod.__query_exchange_rates()
            if result is not None and today == result['date']:
                self._prefs['result'] = result
                bot_core.get_prefs().save_prefs(FinanceMod.PREFS_NAME, self._prefs)
            else:
                result = None
        if result is not None:
            return self.__response_today_exchange_rates(bot_core, result, channel_id, filters)
        return None

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
        url = 'https://www.vietcombank.com.vn/exchangerates/ExrateXLS.aspx'
        result = BotUtils.UrlUtils.download_to_string(url)
        """
        with open('test.htm', 'rb') as f:
            result = f.read()
            f.close()
        """
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
        if len(table) < 10:
            return None
        return {'title': title, 'rates': table, 'date': date}

    def __response_today_exchange_rates(self, bot_core, result, channel_id, filters):
        if 'rates' not in result or 'title' not in result:
            return None

        reply_text = ''
        filtered_reply = ''
        attachments = []
        rate_table = copy(result['rates'][1:])
        row_cnt = len(rate_table)
        origianl_headers = result['rates'][0]

        column_cnt = len(origianl_headers)
        max_widths = [0] * column_cnt
        for col in range(column_cnt):
            for i in range(row_cnt):
                ln = len(unicode(rate_table[i][col], 'utf-8'))
                if ln > max_widths[col]:
                    max_widths[col] = ln

        # Add table fake headers
        headers = [h.split() for h in origianl_headers]
        fake_header_line_cnt = max([len(h) for h in headers])
        for i in range(fake_header_line_cnt):
            fake_line = []
            for j in range(column_cnt):
                h = headers[j]
                fake_line.append(h[i] if i < len(h) else ' ')
            rate_table.insert(i, fake_line)
        row_cnt += fake_header_line_cnt

        is_filtered = False
        # Then display table
        for i in range(row_cnt):
            new_line = ''
            row = rate_table[i]
            filter_matches = False
            attach = {}
            fields = []
            for col in range(column_cnt):
                if col == 1:
                    attach['pretext'] = row[col]
                    continue
                elif col == 0:
                    if not filter_matches and filters is not None and row[col].lower() in filters:
                        filter_matches = True
                        is_filtered = True
                    attach['title'] = row[col]
                else:
                    fields.append({'title': origianl_headers[col], 'value': row[col], 'short': True})
                line = unicode(row[col], 'utf-8').ljust(max_widths[col])
                new_line += line.encode('utf-8')
                if col < column_cnt - 1:
                    new_line += '|'
                else:
                    new_line += '|\n'
            attach['fields'] = fields
            reply_text += new_line
            if filter_matches or i < fake_header_line_cnt:
                filtered_reply += new_line
            new_line = ''

            if i == fake_header_line_cnt - 1 or i == row_cnt - 1:
                separator = ['-' * max_widths[col] for col in range(column_cnt)]
                del separator[1]
                new_line += '|'.join(separator) + '|\n'

            reply_text += new_line
            filtered_reply += new_line
            if filter_matches and i >= fake_header_line_cnt:
                attachments.append(attach)

        title = result['title']
        for ch in self._channels:
            channel = bot_core.get_channel_by_name(ch)
            if channel is not None and Bot.KEY_ID in channel:
                attch_cnt = len(attachments)
                if 0 < attch_cnt <= FinanceMod.MAX_ATTACHMENTS:
                    return ({Bot.KEY_TEXT: title,
                             Bot.KEY_CHANNEL_ID: channel_id,
                             Bot.KEY_ATTACHMENTS: attachments})
                else:
                    file_name = time.strftime('exchange_rate_%Y%m%d.txt', time.localtime())
                    return ({Bot.KEY_TEXT: filtered_reply if is_filtered else reply_text,
                             Bot.KEY_CHANNEL_ID: channel_id,
                             Bot.KEY_RESPONSE_TYPE: Bot.KEY_UPLOAD_RESPONSE,
                             Bot.KEY_TITLE: title,
                             Bot.KEY_FILE_NAME: file_name})

        return None
