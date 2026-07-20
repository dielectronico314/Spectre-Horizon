#!/bin/bash

A=`whoami`

if [ $A != 'root' ];then
    echo "You have to be root to run this script !"
    exit 1;
fi

chmod +x *
./htraapi.sh

SASPATH=/usr/local/bin/sastudio
APP=$SASPATH/.sastudio.sh
STARTAPP=$SASPATH/.desktoptool.sh
if [ ! -d $SASPATH ];then
    mkdir -p $SASPATH
fi

echo "#!/bin/bash

if [ -d `pwd` ];then
    cd `pwd`
    ./app.sh
fi
" > $APP

echo "#!/bin/bash

if [ -d `pwd` ];then
    cd `pwd`
    ./desktoptool.sh
fi
" > $STARTAPP

AUTODESKTOPTOOL=$HOME/.desktoptool.sh
echo "#!/bin/bash

sleep 5s

if [ -f $STARTAPP ];then
    $STARTAPP
fi

" > $AUTODESKTOPTOOL

AUTOSASTUDIO=$HOME/.sastudio.sh
echo "#!/bin/bash

sleep 5s

if [ -f $APP ];then
    $APP
fi
" > $AUTOSASTUDIO

FILE="$HOME/.profile"
#STR="$AUTODESKTOPTOOL"
#CONTENT="$STR &"
#if [ `grep -c "$STR" $FILE` -ne '0' ];then
#    LINE=`grep -n "$CONTENT" $FILE`
#    LINE=${LINE%:*}
#    sed -i "$LINE d" $FILE
#fi
#sed -i '$a\'"$CONTENT" $FILE

#STR="$AUTOSASTUDIO"
#CONTENT="$STR &"
#if [ `grep -c "$STR" $FILE` -ne '0' ];then
#    LINE=`grep -n "$CONTENT" $FILE`
#    LINE=${LINE%:*}
#    sed -i "$LINE d" $FILE
#fi
#sed -i '$a\'"$CONTENT" $FILE


ICONPATH=/usr/share/icons
ICON=$ICONPATH/shortcut.png
if [ ! -d $ICONPATH ];then
    mkdir -p $ICONPATH
fi


SAStudio4=SAStudio4.desktop
rm -rf $SAStudio4

echo "[Desktop Entry]
Version=1.0
Type=Application
Name=SAStudio4
Comment=function for SAStudio
Exec=$APP
Icon=$ICON
Terminal=false
StartupNotify=true
X-KeepTerminal=false
" > $SAStudio4

cp bin/shortcut.png $ICONPATH

chmod +x -R $PRO_NAME $STARTAPP $APP $SAStudio4 $AUTOSASTUDIO $AUTODESKTOPTOOL
chown $USER:$USER -R $PRO_NAME $STARTAPP $APP $SAStudio4 $AUTOSASTUDIO $AUTODESKTOPTOOL

actual_user=$(logname)
chown $actual_user $SAStudio4

echo "SAStudio4 installed successfully!"

# 复制快捷方式到桌面
cp -f $SAStudio4 /home/$SUDO_USER/Desktop/
chown $actual_user /home/$SUDO_USER/Desktop/$SAStudio4

#ps -ef | grep desktoptool | grep -v grep
#if [ $? -eq 0 ];then
#    killall -9 desktoptool
#fi

#./desktoptool.sh &


