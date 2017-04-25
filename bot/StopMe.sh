#!/bin/bash
PID_FILE=cac_cu_bot.pid
if [ -f $PID_FILE ]; then
	kill -9 $(cat $PID_FILE)
fi
