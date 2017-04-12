#!/bin/bash
source `which virtualenvwrapper.sh`
workon slackbot
nohup python BotRunner.py --config=conf/bot.conf </dev/null >/dev/null 2>&1 &
