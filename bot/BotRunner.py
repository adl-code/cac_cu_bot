from BotCore.BotEngine import BotEngine
from BotCore.BotEngine import BotBaseMod
import BotMods
import sys
import os
import random
import datetime


def show_help():
    print 'Usage: BotRunner.py [Options]'
    print 'Options:'
    print '       --help: show this screen'
    print '       --config=<config_file>'


def parse_options():
    """
    Parse the command line arguments
    :return: dictionary object representing program options
    """
    options = {}
    for arg in sys.argv:
        pos = arg.find('--')
        if pos == 0:
            pos = arg[2:].find('=')
            if pos == 0:
                continue
            elif pos > 0:
                k = arg[2:pos + 2]
                val = arg[pos + 3:]
            else:
                k = arg[2:]
                val = ""
            options[k] = val
    return options


def init_bot(config_file_path):
    """
    Initialize the bot object
    :param config_file_path: path to the config file
    :return: object pointing to bot engine
    """
    bot = BotEngine(config_file_path)

    BotBaseMod.register(BotMods.WeatherMod.WeatherMod)
    mods = [
        BotMods.WeatherMod.WeatherMod(),
        BotMods.IdleMod.IdleMod(),
        BotMods.InsultMod.InsultMod(),
        BotMods.UnhandledMsgMod.UnhandledMsgMod()
    ]

    for mod in mods:
        mod_name = mod.get_mod_name()
        if mod_name is None or mod_name == '':
            bot.get_logger().warning('module class "%s" has no name!' % type(mod).__name__)
        if bot.get_config().is_module_disabled(mod_name):
            # Skip the disabled module
            bot.get_logger().info('Skip disabled module "%s"' % mod_name)
            continue

        bot.get_logger().info('Module "%s" loaded' % mod_name)
        bot.register_mod(mod)
        mod.on_registered(bot)

    return bot


def main():
    """
    The program entry point
    :return: 0 if success, non zero if errors occurred
    """
    options = parse_options()
    if 'help' in options:
        show_help()
        return 0

    if 'config' in options:
        config_file_path = options['config']
    else:
        config_file_path = None

    if config_file_path is None or config_file_path == '':
        config_file_path = 'bot.conf'

    if not os.path.exists(config_file_path):
        print("Config file not found!")
        return 1

    bot = init_bot(config_file_path)
    if bot is None:
        print("Failed to initialized bot object")
        return 1
    random.seed(datetime.datetime.now())
    bot.run()
    return 1

if __name__ == "__main__":
    main()
