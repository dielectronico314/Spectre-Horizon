
CURDIR=`pwd`

A=`whoami`

if [ $A != 'root' ]; then
   echo "You have to be root to run this script"
   exit 1;
fi

file=$( ls htraapi/lib/x86_64/libhtraapi.so.* )
file=$( basename $file )
version=${file#*so.}
majornum=${version%%.*}

cp htraapi/configs/htrausb.conf /etc/
cp htraapi/configs/htra-cyusb.rules /etc/udev/rules.d/

rm -rf /opt/htraapi/
cp -r htraapi/ /opt/

#x86_64
ln -sf /opt/htraapi/lib/x86_64/libhtraapi.so.${version} /opt/htraapi/lib/x86_64/libhtraapi.so.${majornum}
ln -sf /opt/htraapi/lib/x86_64/libhtraapi.so.${majornum} /opt/htraapi/lib/x86_64/libhtraapi.so

ln -sf /opt/htraapi/lib/x86_64/libusb-1.0.so.0.2.0 /opt/htraapi/lib/x86_64/libusb-1.0.so.0
ln -sf /opt/htraapi/lib/x86_64/libusb-1.0.so.0 /opt/htraapi/lib/x86_64/libusb-1.0.so

ln -sf /opt/htraapi/lib/x86_64/libgomp.so.1.0.0 /opt/htraapi/lib/x86_64/libgomp.so.1
ln -sf /opt/htraapi/lib/x86_64/libgomp.so.1 /opt/htraapi/lib/x86_64/libgomp.so

#aarch64
ln -sf /opt/htraapi/lib/aarch64/libhtraapi.so.${version} /opt/htraapi/lib/aarch64/libhtraapi.so.${majornum}
ln -sf /opt/htraapi/lib/aarch64/libhtraapi.so.${majornum} /opt/htraapi/lib/aarch64/libhtraapi.so

ln -sf /opt/htraapi/lib/aarch64/libusb-1.0.so.0.2.0 /opt/htraapi/lib/aarch64/libusb-1.0.so.0
ln -sf /opt/htraapi/lib/aarch64/libusb-1.0.so.0 /opt/htraapi/lib/aarch64/libusb-1.0.so

ln -sf /opt/htraapi/lib/aarch64/libgomp.so.1.0.0 /opt/htraapi/lib/aarch64/libgomp.so.1
ln -sf /opt/htraapi/lib/aarch64/libgomp.so.1 /opt/htraapi/lib/aarch64/libgomp.so


#armv7
ln -sf /opt/htraapi/lib/armv7/libhtraapi.so.${version} /opt/htraapi/lib/armv7/libhtraapi.so.${majornum}
ln -sf /opt/htraapi/lib/armv7/libhtraapi.so.${majornum} /opt/htraapi/lib/armv7/libhtraapi.so

ln -sf /opt/htraapi/lib/armv7/libusb-1.0.so.0.2.0 /opt/htraapi/lib/armv7/libusb-1.0.so.0
ln -sf /opt/htraapi/lib/armv7/libusb-1.0.so.0 /opt/htraapi/lib/armv7/libusb-1.0.so

ln -sf /opt/htraapi/lib/armv7/libgomp.so.1.0.0 /opt/htraapi/lib/armv7/libgomp.so.1
ln -sf /opt/htraapi/lib/armv7/libgomp.so.1 /opt/htraapi/lib/armv7/libgomp.so

#aarch64_gcc7.5
ln -sf /opt/htraapi/lib/aarch64_gcc7.5/libhtraapi.so.${version} /opt/htraapi/lib/aarch64_gcc7.5/libhtraapi.so.${majornum}
ln -sf /opt/htraapi/lib/aarch64_gcc7.5/libhtraapi.so.${majornum} /opt/htraapi/lib/aarch64_gcc7.5/libhtraapi.so

ln -sf /opt/htraapi/lib/aarch64_gcc7.5/libusb-1.0.so.0.2.0 /opt/htraapi/lib/aarch64_gcc7.5/libusb-1.0.so.0
ln -sf /opt/htraapi/lib/aarch64_gcc7.5/libusb-1.0.so.0 /opt/htraapi/lib/aarch64_gcc7.5/libusb-1.0.so

ln -sf /opt/htraapi/lib/aarch64_gcc7.5/libgomp.so.1.0.0 /opt/htraapi/lib/aarch64_gcc7.5/libgomp.so.1
ln -sf /opt/htraapi/lib/aarch64_gcc7.5/libgomp.so.1 /opt/htraapi/lib/aarch64_gcc7.5/libgomp.so

#x86_64_gcc5.4
ln -sf /opt/htraapi/lib/x86_64_gcc5.4/libhtraapi.so.${version} /opt/htraapi/lib/x86_64_gcc5.4/libhtraapi.so.${majornum}
ln -sf /opt/htraapi/lib/x86_64_gcc5.4/libhtraapi.so.${majornum} /opt/htraapi/lib/x86_64_gcc5.4/libhtraapi.so

ln -sf /opt/htraapi/lib/x86_64_gcc5.4/libusb-1.0.so.0.2.0 /opt/htraapi/lib/x86_64_gcc5.4/libusb-1.0.so.0
ln -sf /opt/htraapi/lib/x86_64_gcc5.4/libusb-1.0.so.0 /opt/htraapi/lib/x86_64_gcc5.4/libusb-1.0.so

ln -sf /opt/htraapi/lib/x86_64_gcc5.4/libgomp.so.1.0.0 /opt/htraapi/lib/x86_64_gcc5.4/libgomp.so.1
ln -sf /opt/htraapi/lib/x86_64_gcc5.4/libgomp.so.1 /opt/htraapi/lib/x86_64_gcc5.4/libgomp.so
