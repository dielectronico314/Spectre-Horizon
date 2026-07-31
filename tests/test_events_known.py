#!/usr/bin/env python3
"""
tests/test_events_known.py — Escenarios de aceptación del motor de eventos (Día 14).

Alimenta app.events.engine.EventEngine directamente con tramas sintéticas
(t_s, snr_db, pico_dbfs, potencia_dbfs) — sin pasar por CSV ni espectrograma,
porque el motor es una máquina de estados pura (sin I/O). Cada escenario ataca
un riesgo explícito del plan del Día 14 (fragmentación, fusión incorrecta,
falsos positivos, pérdida silenciosa de eventos truncados).

Los eventos esperados se guardan la primera vez en tests/golden/*.json y se
comparan en cada corrida futura (misma filosofía de oráculo que el Día 11).
"""
import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.events.engine import EventEngine

GOLDEN_DIR = Path(__file__).parent / "golden"
DT = 0.1

DEFAULT_PARAMS = dict(
    margen_umbral_db=6.0,
    min_on_frames=3,
    min_off_frames=3,
    merge_gap_s=0.5,
    margen_severidad_medium_db=6.0,
    margen_severidad_high_db=12.0,
    confianza_escala_db=10.0,
)


def build_frames(segments, piso_dbfs=-40.0, pico_offset_db=2.0, dt=DT):
    """
    segments: lista de (duracion_s, snr_db). Genera tramas contiguas cada DT.
    potencia_dbfs y pico_dbfs se derivan de un piso de ruido fijo simulado,
    ya que el motor de eventos no vuelve a estimar el piso (lo hereda de Día 13).
    """
    frames = []
    t = 0.0
    for duration_s, snr_db in segments:
        n = max(1, round(duration_s / dt)) if duration_s > 0 else 0
        for _ in range(n):
            potencia_dbfs = piso_dbfs + snr_db
            pico_dbfs = potencia_dbfs + pico_offset_db
            frames.append((round(t, 6), snr_db, pico_dbfs, potencia_dbfs))
            t = round(t + dt, 6)
    return frames


def run_engine(segments, band_name="TestBand", session_id="test_session", dt=DT, **overrides):
    params = {**DEFAULT_PARAMS, **overrides}
    engine = EventEngine(
        band_name=band_name,
        session_id=session_id,
        capture_sha256="deadbeef",
        **params,
    )
    events = []
    for t_s, snr_db, pico_dbfs, potencia_dbfs in build_frames(segments, dt=dt):
        closed = engine.process_frame(t_s, snr_db, pico_dbfs, potencia_dbfs)
        if closed is not None:
            events.append(closed)
    closed = engine.flush()
    if closed is not None:
        events.append(closed)
    return events


def assert_close(a, b, tol, msg=""):
    assert abs(a - b) <= tol, f"{msg}: {a} vs {b} (tol={tol})"


def compare_or_create_golden(name, actual_events, t_tol=DT + 1e-9, val_tol=0.05):
    """
    Primera corrida: guarda actual_events como referencia en tests/golden/.
    Corridas siguientes: compara contra la referencia (con tolerancia de
    ±1 trama en tiempos, ±0.05 en valores en dB) para detectar regresiones
    sin exigir igualdad exacta de floats.
    """
    golden_path = GOLDEN_DIR / f"{name}.json"
    if not golden_path.exists():
        golden_path.parent.mkdir(parents=True, exist_ok=True)
        with open(golden_path, "w") as f:
            json.dump(actual_events, f, indent=2)
        return

    with open(golden_path) as f:
        expected_events = json.load(f)

    assert len(actual_events) == len(expected_events), (
        f"{name}: se esperaban {len(expected_events)} eventos, se obtuvieron {len(actual_events)}"
    )
    for i, (a, e) in enumerate(zip(actual_events, expected_events)):
        assert a["event_id"] == e["event_id"], f"{name}[{i}].event_id"
        assert a["band_name"] == e["band_name"], f"{name}[{i}].band_name"
        assert a["closed_reason"] == e["closed_reason"], f"{name}[{i}].closed_reason"
        assert a["n_fusiones"] == e["n_fusiones"], f"{name}[{i}].n_fusiones"
        assert a["severidad"] == e["severidad"], f"{name}[{i}].severidad"
        for key in ("start_t_s", "end_t_s", "duration_s"):
            assert_close(a[key], e[key], t_tol, f"{name}[{i}].{key}")
        for key in ("pico_dbfs", "potencia_media_activa_dbfs", "confianza"):
            assert_close(a[key], e[key], val_tol, f"{name}[{i}].{key}")


# --------------------------------------------------------------------------- #
# Escenario A — burst limpio: exactamente 1 evento
# --------------------------------------------------------------------------- #
def test_scenario_a_burst_limpio():
    segments = [(0.5, -5.0), (2.0, 15.0), (1.5, -5.0)]
    events = run_engine(segments)

    assert len(events) == 1, "un burst limpio debe producir exactamente 1 evento"
    ev = events[0]
    assert ev["closed_reason"] == "threshold_off"
    assert ev["n_fusiones"] == 0
    assert_close(ev["start_t_s"], 0.5, DT + 1e-9, "start_t_s")
    assert_close(ev["duration_s"], 2.0, DT + 1e-9, "duration_s")
    assert ev["severidad"] == "medium"  # margen_pico_snr = 15 - 6 = 9 dB

    compare_or_create_golden("scenario_a_burst_limpio", events)


# --------------------------------------------------------------------------- #
# Escenario B — burst con titileo: merge_gap_s debe fusionar, no fragmentar
# --------------------------------------------------------------------------- #
def test_scenario_b_burst_con_titileo():
    segments = [
        (0.5, -5.0),   # idle
        (0.5, 15.0),   # activo
        (0.3, -5.0),   # dip: exactamente min_off_frames -> entra a COOLDOWN
        (0.7, 15.0),   # recupera dentro de merge_gap_s -> fusiona
        (0.3, -5.0),   # segundo dip -> COOLDOWN de nuevo
        (1.3, -5.0),   # idle suficiente para superar merge_gap_s y cerrar
    ]
    events = run_engine(segments)

    assert len(events) == 1, "el titileo cerca del umbral no debe fragmentar en varios eventos"
    ev = events[0]
    assert ev["n_fusiones"] == 1
    assert ev["closed_reason"] == "threshold_off"

    compare_or_create_golden("scenario_b_burst_con_titileo", events)


# --------------------------------------------------------------------------- #
# Escenario C — dos bursts separados por > merge_gap_s: no deben fusionarse
# --------------------------------------------------------------------------- #
def test_scenario_c_dos_bursts_separados():
    segments = [
        (0.5, -5.0),
        (0.5, 15.0),
        (2.0, -5.0),   # gap >> merge_gap_s: deben quedar como eventos distintos
        (0.5, 15.0),
        (1.3, -5.0),
    ]
    events = run_engine(segments)

    assert len(events) == 2, "bursts separados por mas que merge_gap_s no deben fusionarse"
    assert events[0]["n_fusiones"] == 0
    assert events[1]["n_fusiones"] == 0
    assert events[0]["event_id"] != events[1]["event_id"]
    assert events[0]["end_t_s"] < events[1]["start_t_s"]

    compare_or_create_golden("scenario_c_dos_bursts_separados", events)


# --------------------------------------------------------------------------- #
# Escenario D — silencio puro: cero falsos positivos
# --------------------------------------------------------------------------- #
def test_scenario_d_silencio_puro():
    segments = [(2.0, -5.0)]
    events = run_engine(segments)
    assert len(events) == 0, "silencio puro no debe generar eventos"


# --------------------------------------------------------------------------- #
# Escenario E — corte a mitad de evento: nunca se pierde silenciosamente
# --------------------------------------------------------------------------- #
def test_scenario_e_corte_durante_activo():
    segments = [(0.5, -5.0), (1.0, 15.0)]  # la captura termina en pleno ACTIVO
    events = run_engine(segments)

    assert len(events) == 1, "un evento truncado en ACTIVO debe forzarse con flush()"
    ev = events[0]
    assert ev["closed_reason"] == "end_of_capture"
    assert_close(ev["start_t_s"], 0.5, DT + 1e-9)
    assert_close(ev["end_t_s"], 1.4, DT + 1e-9)

    compare_or_create_golden("scenario_e_corte_durante_activo", events)


def test_scenario_e_corte_durante_cooldown():
    segments = [(0.5, -5.0), (0.5, 15.0), (0.3, -5.0)]  # termina en pleno COOLDOWN
    events = run_engine(segments)

    assert len(events) == 1, "un evento truncado en COOLDOWN tambien debe forzarse con flush()"
    ev = events[0]
    assert ev["closed_reason"] == "end_of_capture"
    # end_t_s debe ser la ultima trama genuinamente activa (0.9), no el corte (1.2)
    assert_close(ev["end_t_s"], 0.9, DT + 1e-9)

    compare_or_create_golden("scenario_e_corte_durante_cooldown", events)


# --------------------------------------------------------------------------- #
# Escenario F — tráfico empaquetado (packet_traffic)
# --------------------------------------------------------------------------- #
def test_scenario_f_rafagas_cortas_separadas():
    # rafagas de 5ms, separadas por 10ms (< 0.015s gap) -> se fusionan
    segments_fusion = [
        (0.5, -5.0),
        (0.005, 15.0),
        (0.010, -5.0),
        (0.005, 15.0),
        (0.010, -5.0),
        (0.005, 15.0),
        (0.5, -5.0),
    ]
    events_fusion = run_engine(segments_fusion, dt=0.001, merge_gap_s=0.015, min_on_frames=1, min_off_frames=1)
    
    assert len(events_fusion) == 1, "Huecos de 10ms (< merge_gap_s) deben fusionar ráfagas WiFi/BT"
    assert events_fusion[0]["n_fusiones"] == 2
    compare_or_create_golden("scenario_f_rafagas_cortas_fusionadas", events_fusion)

    # rafagas de 5ms, separadas por 20ms (> 0.015s gap) -> no se fusionan
    segments_separados = [
        (0.5, -5.0),
        (0.005, 15.0),
        (0.020, -5.0),
        (0.005, 15.0),
        (0.020, -5.0),
        (0.005, 15.0),
        (0.5, -5.0),
    ]
    events_separados = run_engine(segments_separados, dt=0.001, merge_gap_s=0.015, min_on_frames=1, min_off_frames=1)
    
    assert len(events_separados) == 3, "Huecos de 20ms (> merge_gap_s) deben generar eventos distintos"
    assert events_separados[0]["n_fusiones"] == 0
    compare_or_create_golden("scenario_f_rafagas_cortas_separadas", events_separados)


# --------------------------------------------------------------------------- #
# Fórmulas explícitas de severidad y confianza (sección 3 del plan)
# --------------------------------------------------------------------------- #
def test_severidad_y_confianza_formulas_explicitas():
    # margen_pico_snr = 11.9 - 6 = 5.9 dB -> "low" (justo debajo del corte)
    ev_low = run_engine([(0.5, -5.0), (0.5, 11.9), (1.3, -5.0)])[0]
    assert ev_low["severidad"] == "low"

    # margen_pico_snr = 12.0 - 6 = 6.0 dB -> "medium" (limite inclusive)
    ev_medium = run_engine([(0.5, -5.0), (0.5, 12.0), (1.3, -5.0)])[0]
    assert ev_medium["severidad"] == "medium"

    # margen_pico_snr = 18.0 - 6 = 12.0 dB -> "high" (limite inclusive)
    ev_high = run_engine([(0.5, -5.0), (0.5, 18.0), (1.3, -5.0)])[0]
    assert ev_high["severidad"] == "high"

    # confianza: snr constante 16 dB -> margen_medio = 16 - 6 = 10 dB = escala completa -> confianza=1.0
    ev_conf = run_engine([(0.5, -5.0), (0.5, 16.0), (1.3, -5.0)])[0]
    assert_close(ev_conf["confianza"], 1.0, 1e-6)


if __name__ == "__main__":
    import traceback

    tests = [
        test_scenario_a_burst_limpio,
        test_scenario_b_burst_con_titileo,
        test_scenario_c_dos_bursts_separados,
        test_scenario_d_silencio_puro,
        test_scenario_e_corte_durante_activo,
        test_scenario_e_corte_durante_cooldown,
        test_scenario_f_rafagas_cortas_separadas,
        test_severidad_y_confianza_formulas_explicitas,
    ]
    fallos = 0
    for t in tests:
        try:
            t()
            print(f"✅ {t.__name__}")
        except AssertionError:
            fallos += 1
            print(f"❌ {t.__name__}")
            traceback.print_exc()
    if fallos:
        print(f"\n{fallos} test(s) fallaron.")
        sys.exit(1)
    print("\nTodos los tests pasaron.")
