#!/bin/bash

ps -ef | grep SAStudio4 | grep -v grep
if [ $? -eq 0 ];then
    killall -9 SAStudio4 2>/dev/null || pkexec killall -9 SAStudio4 2>/dev/null
fi

export LD_LIBRARY_PATH=`pwd`:`pwd`/lib:`pwd`/plugin:$LD_LIBRARY_PATH
cd ./bin
./SAStudio4 &


