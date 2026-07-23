#!/bin/bash
# Ejemplo: Captura de dispositivos IoT, mandos de garaje y alarmas (Banda ISM 433 MHz)
../scripts/capture.sh --freq 433.92e6 --rate 1.953125e6 --gain 10 --duration 300 --chunk-duration 60 --antenna "Monopolo_UHF" --location "Exterior_Calle"
