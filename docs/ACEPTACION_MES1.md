# Checklist de Aceptación — Mes 1 (Conciencia de Espectro)

| Día | Terminado cuando (oficial) | Estado real, con evidencia de esta conversación |
| --- | --- | --- |
| 7 | Interrupción no destruye datos, informa si pudo continuar | ✅ Desconexión física real ×2, bytes múltiplo de 4, try/finally verificado |
| 11 | Espectrograma reproducible, escala documentada | ✅ PNG bit-idéntico, normalización contra ground truth |
| 12 | Streaming sin discontinuidad, cero pérdida | ✅ Soak 37min, fs real 1,953,125 Hz confirmado por 2 vías |
| 13 | Features con tolerancia, reproducibles | ✅ 7 asserts, ground truth sintético |
| 14 | Misma captura → mismos eventos, sin avalancha | ✅ Determinismo confirmado, umbral global corregido (2.0→6.0dB) tras encontrar el bug en Synth_Burst/WiFi_2.4GHz |
| 15 | ID de evento → todo, hashes validan | ✅ Auditoría Nivel 3, Δ=0.000dB, core:datetime como fuente de timestamp confirmada |
| 16 | Cliente HTTP navega sesión → evidencia | ✅ Navegación completa, filtros con caso negativo, path traversal bloqueado |
| 17 | No técnico identifica estado, entiende evento | ✅ Piso de ruido real (no constante inventada), explicación humanizada verificada |
| 18 | Reporte coincide con sesión, verificable | ✅ Lint de lenguaje limpio, trazabilidad idéntica dashboard↔reporte |
| 19 | Demo ejecutable tras reiniciar, sin editar código | ✅ Purga masiva completada (86→14 eventos reales, sin fantasmas), golden dataset idempotente y verificado contra ground truth, guion con números reales confirmados |

## Nota Especial del Día 19
El Día 19 no cerró en su primer intento — encontramos y corregimos, en el camino, un bug de `session_id` que llevaba desde el Día 13 contaminando silenciosamente el índice, y un umbral de detección (2.0dB) que generaba falsos positivos crónicos en cualquier banda con estrategia temporal. 

Esto no es una debilidad a esconder — es evidencia de que el proceso de auditoría funcionó como debía: encontrar los bugs antes de la entrega, no durante la demo frente a la audiencia.
