#!/bin/bash
echo "🚀 Limpiando contenedores viejos..."
docker rm -f harogic_final test_sdr_raw test_rfswift_raw 2>/dev/null

echo "🚀 Iniciando contenedor maestro (bypasseando el bug de rfswift)..."
docker run -d -it --name harogic_final --privileged --network host --shm-size 1g \
    -v /home/diego/Desktop/harogic:/workspace \
    -v /dev/bus/usb:/dev/bus/usb \
    -w /workspace \
    penthertz/rfswift_noble:sdr_full /bin/zsh

echo "📦 Inyectando archivos de calibración obligatorios..."
docker exec harogic_final mkdir -p /usr/bin/CalFile
docker cp "SAStudio4(Ubuntu18.04 x86_64)_4.3.55.30/SAStudio4_4.3.55.30/bin/CalFile/." harogic_final:/usr/bin/CalFile/

echo "🔧 Instalando dependencias de Python (Numpy 2.x)..." 
docker exec harogic_final pip install -q -U "numpy>=2.0.0" --break-system-packages 

echo "🔍 Verificando detección del hardware Harogic..."
docker exec harogic_final SoapySDRUtil --find

echo "✅ ¡Listo! Puedes entrar a la terminal interactiva con:"
echo "docker exec -it harogic_final /bin/zsh"
