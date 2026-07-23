#!/bin/bash
# Ejemplo: Captura de banda de radio FM comercial (106.5 MHz)
# Archivos de salida en: rf-spectrum/data/samples/
../scripts/capture.sh --freq 106.5e6 --rate 1.953125e6 --gain 0 --duration 120 --chunk-duration 60 --antenna "Dipolo_Telescopica" --location "Laboratorio_Indoor"
