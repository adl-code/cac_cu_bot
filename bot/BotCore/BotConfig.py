import binascii
import ConfigParser
import json
import os


class JsonLoader:
    def __init__(self):
        pass

    @staticmethod
    def json_load_byteified(file_handle):
        return JsonLoader.byteify(
            json.load(file_handle, object_hook=JsonLoader.byteify),
            ignore_dicts=True
        )

    @staticmethod
    def json_loads_byteified(json_text):
        return JsonLoader.byteify(
            json.loads(json_text, object_hook=JsonLoader.byteify),
            ignore_dicts=True
        )

    @staticmethod
    def byteify(data, ignore_dicts=False):
        # if this is a unicode string, return its string representation
        if isinstance(data, unicode):
            return data.encode('utf-8')
        # if this is a list of values, return list of byteified values
        if isinstance(data, list):
            return [JsonLoader.byteify(item, ignore_dicts=True) for item in data]
        # if this is a dictionary, return dictionary of byteified keys and values
        # but only if we haven't already byteified it
        if isinstance(data, dict) and not ignore_dicts:
            return {
                JsonLoader.byteify(key, ignore_dicts=True): JsonLoader.byteify(value, ignore_dicts=True)
                for key, value in data.iteritems()
            }
        # if it's anything else, return it in its original form
        return data


class BotConfig(object):
    """  
    BotConfig class representing bot configuration
    """
    _api_token = None
    _paths = {}
    _disabled_modules = {}

    def __init__(self, config_file):
        self._config_file = config_file
        parser = ConfigParser.SafeConfigParser()
        parser.read(config_file)

        # Parse the API options
        self.__parse_api(parser)

        # Parse paths
        try:
            for name, value in parser.items('paths'):
                self._paths[name.lower()] = value
        except ConfigParser.NoSectionError:
            pass

        # Parse disabled modules
        self.__parse_disabled_modules(parser)

    def __parse_api(self, parser):
        """
        Parse API options
        :param parser: parser: the parser object
        :return: None
        """
        # API token
        try:
            token = parser.get('api', 'token')
        except ConfigParser.NoSectionError, ConfigParser.NoOptionError:
            token = None
        if token is not None:
            self.__parse_token(token)

    def __parse_disabled_modules(self, parser):
        """
        Parse the disabled module list options
        :param parser: the parser object
        :return: 
        """
        try:
            dsb_mod_list = parser.items('disabled_modules')
            for mod_name, _ in dsb_mod_list:
                try:
                    val = parser.getint('disabled_modules', mod_name)
                except ConfigParser.Error:
                    val = None
                if val is not None and isinstance(mod_name, (str, unicode)):
                    self._disabled_modules[mod_name.lower()] = val
        except ConfigParser.Error:
            return

    def __parse_token(self, token):
        """
        Parse the input token (in hex format) and extract the API token
        :param token: the input token in hex format
        :return: None 
        """
        hex_key = '4f6e652070726f626c656d206f662041524334206973207468617420697420646f6573206e6f742074616b652061206e'
        if len(hex_key) % 2:
            hex_key = '0' + hex_key
        if len(token) % 2:
            token = '0' + token
        key = binascii.unhexlify(hex_key)
        t = binascii.unhexlify(token)
        self._api_token = ""
        for (ch, k) in zip(t, key):
            self._api_token += chr(ord(ch) ^ ord(k))

    def get_path(self, path):
        """
        Get the specified path configuration
        :param path: path name to get
        :return: the specified path, None if error occurred 
        """
        if path is not None and path in self._paths:
            return self.make_full_path(self._paths[path])
        else:
            return None

    def get_api_token(self):
        """
        Get the API token
        :return: the API token, None if error occurred 
        """
        return self._api_token

    def is_module_disabled(self, mod_name):
        """
        Check whether the given module name has been disabled
        :param mod_name: module name to check
        :return: True if module has been disabled, False otherwise
        """
        if mod_name is None:
            return False
        name = mod_name.lower()
        if name in self._disabled_modules:
            return self._disabled_modules[name] == 1
        else:
            return None

    def make_full_path(self, file_name):
        if file_name is None or file_name == '' or self._config_file is None:
            return None
        parent_dir = os.path.dirname(os.path.abspath(self._config_file))
        if parent_dir is None or parent_dir == '':
            parent_dir = os.getcwd()
        return os.path.join(parent_dir, file_name)
