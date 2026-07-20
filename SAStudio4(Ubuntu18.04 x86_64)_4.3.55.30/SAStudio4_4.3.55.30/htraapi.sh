#!/bin/bash

pwd=`pwd`
A=`whoami`

if [ $A != 'root' ];then
    echo "You have to be root to run this script !"
    exit 1;
fi

#delete usb
rm -f /etc/htrausb.conf
rm -f /etc/udev/rules.d/htra-cyusb.rules

#delete libusb link
rm -f $pwd/lib/libusb-1.0.so

#delete fftw link
rm -f $pwd/lib/libfftw3.so

#delete htra_api link
rm -f $pwd/lib/libhtraapi.so
rm -f $pwd/lib/libhtraapi.so.0

chmod 777 -R configs/

cp configs/htrausb.conf /etc/
cp configs/htra-cyusb.rules /etc/udev/rules.d/

ln -sf $pwd/lib/libhtraapi.so.0.55.63 $pwd/lib/libhtraapi.so.0
ln -sf $pwd/lib/libhtraapi.so.0 $pwd/lib/libhtraapi.so

ln -sf $pwd/lib/libfftw3.so.3.6.10 $pwd/lib/libfftw3.so.3
ln -sf $pwd/lib/libfftw3.so.3 $pwd/lib/libfftw3.so

ln -sf $pwd/lib/libusb-1.0.so.0.2.0 $pwd/lib/libusb-1.0.so.0
ln -sf $pwd/lib/libusb-1.0.so.0 $pwd/lib/libusb-1.0.so

if [ 0 -ne 0 ]; then
    htraapi installed failed!
    exit 1
fi

#echo htraapi installed successfully!


