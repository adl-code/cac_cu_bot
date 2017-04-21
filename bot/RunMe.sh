#!/bin/bash
source `which virtualenvwrapper.sh`
workon slackbot
PID_FILE=cac_cu_bot.pid
if [ -f $PID_FILE ]; then
	kill -9 $(cat $PID_FILE)
fi
nohup python BotRunner.py --config=conf/bot.conf </dev/null >/dev/null 2>&1 &
