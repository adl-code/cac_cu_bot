import random
import urllib
import threading
import time
import HTMLParser


g_random_lock = threading.RLock()
with g_random_lock:
    random.seed(time.mktime(time.localtime()))


class RandomUtils:
    def __init__(self):
        pass

    @staticmethod
    def random_int(a, b):
        with g_random_lock:
            val = random.randint(a, b)
        return val

    @staticmethod
    def random_item_in_list(item_list):
        """
        Randomly choose an item in a list
        :param item_list: the input list
        :return: item randomly chosen
        """
        if item_list is None:
            return None
        ln = len(item_list)
        if ln == 0:
            return None
        elif ln == 1:
            return item_list[0]

        with g_random_lock:
            val = item_list[random.randrange(0, ln - 1)]
        return val


class UrlUtils:
    def __init__(self):
        pass

    @staticmethod
    def download_to_string(url):
        try:
            response = urllib.urlopen(url)
            data = response.read()
            response.close()
        except IOError:
            return None
        return data


class HtmlSimpleParser(HTMLParser.HTMLParser):
    def __init__(self, html_content):
        HTMLParser.HTMLParser.__init__(self)
        self._root = {'children': [], 'parent': None}
        self._parent = self._root
        self._current = None
        self.feed(html_content)

    def handle_starttag(self, tag, attrs):
        if self._current is not None:
            self._parent = self._current
        self._current = {'tag': tag, 'attribs': {}, 'children': [], 'parent': self._parent}
        for k, v in attrs:
            self._current['attribs'][k] = v

    def handle_endtag(self, tag):
        if self._current is None or self._parent is None:
            return
        if self._current['tag'] == tag:
            self._parent['children'].append(self._current)
        self._current = self._current['parent']
        if self._parent['parent'] is not None:
            self._parent = self._parent['parent']

    def handle_data(self, data):
        if self._current is None:
            return
        self._current['data'] = data

    def get_root(self):
        return self._root
