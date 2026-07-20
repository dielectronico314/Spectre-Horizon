#!/bin/bash

ps -ef | grep desktoptool | grep -v grep
if [ $? -eq 0 ];then
    killall -9 desktoptool
fi

export LD_LIBRARY_PATH=`pwd`:`pwd`/lib:`pwd`/plugin:$LD_LIBRARY_PATH
cd ./bin
./desktoptool &


