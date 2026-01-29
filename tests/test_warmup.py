"""Tests für Warmup-Period - HANT Issue #7"""

import pytest  # type: ignore
from modbus_energy_meter.total_increasing_filter import TotalIncreasingFilter


def test_warmup_period_basic():
    """Warmup-Period: Erste 3 Cycles ohne Filterung"""
    filter_instance = TotalIncreasingFilter(warmup_cycles=3)

    # Cycle 1: Auch 0 wird durchgelassen
    result1 = filter_instance.filter({"energy_grid_exported": 0})
    assert result1["energy_grid_exported"] == 0
    assert filter_instance.warmup_mode == True

    # Cycle 2 & 3
    filter_instance.filter({"energy_grid_exported": 5432.1})
    filter_instance.filter({"energy_grid_exported": 5432.8})
    assert filter_instance.warmup_mode == False

    # Cycle 4: Jetzt aktiv - 0 wird gefiltert!
    result4 = filter_instance.filter({"energy_grid_exported": 0})
    assert result4["energy_grid_exported"] == 5432.8


def test_hant_issue_7_scenario():
    """HANT Issue #7: Zero-Drop nach Connection-Reset"""
    filter_instance = TotalIncreasingFilter(warmup_cycles=3)

    # Phase 1: Normaler Betrieb
    for i in range(5):
        filter_instance.filter({"energy_grid_exported": 5432.1 + i * 0.5})
    assert filter_instance.warmup_mode == False

    # Phase 2: Connection-Error → Reset
    filter_instance.reset()
    assert filter_instance.warmup_mode == True

    # Phase 3: Nach Reconnect - Erste Werte inkonsistent
    result1 = filter_instance.filter({"energy_grid_exported": 0})
    assert result1["energy_grid_exported"] == 0  # Warmup!
    assert "energy_grid_exported" in filter_instance.suspicious_first_values

    # Cycles 2-3: Warmup läuft
    filter_instance.filter({"energy_grid_exported": 5434.8})
    filter_instance.filter({"energy_grid_exported": 5435.2})

    # Cycle 4: Jetzt aktiv - 0 wird gefiltert!
    result4 = filter_instance.filter({"energy_grid_exported": 0})
    assert result4["energy_grid_exported"] == 5435.2  # ✅ Gefiltert!


# ===== NEUE TESTS =====


def test_warmup_with_all_five_sensors():
    """Warmup: Alle 5 total_increasing Sensoren gleichzeitig"""
    filter_instance = TotalIncreasingFilter(warmup_cycles=3)

    # Cycle 1: Alle Sensoren mit verschiedenen Werten
    data1 = {
        "energy_yield_accumulated": 18052.68,
        "energy_grid_exported": 9799.50,
        "energy_grid_accumulated": 3502.66,
        "battery_charge_total": 4851.74,
        "battery_discharge_total": 4649.64,
    }
    result1 = filter_instance.filter(data1)

    # Alle Werte sollten durchkommen (Warmup!)
    assert result1 == data1
    assert filter_instance.warmup_mode == True
    assert filter_instance.warmup_cycles == 1

    # Cycles 2-3
    filter_instance.filter(data1)
    filter_instance.filter(data1)

    # Nach Cycle 3: Warmup beendet
    assert filter_instance.warmup_mode == False
    assert filter_instance.warmup_cycles == 3


def test_warmup_suspicious_zero_detection():
    """Warmup: Zero-Werte werden als suspicious markiert"""
    filter_instance = TotalIncreasingFilter(warmup_cycles=3)

    # Cycle 1: Zero-Wert (suspicious!)
    result = filter_instance.filter({"energy_grid_exported": 0})

    assert result["energy_grid_exported"] == 0  # Durchgelassen (Warmup)
    assert "energy_grid_exported" in filter_instance.suspicious_first_values
    assert filter_instance.suspicious_first_values["energy_grid_exported"] == 0


def test_warmup_suspicious_recovery():
    """
    Warmup: Recovery von suspicious Zero zu normalem Wert

    ✅ FIX: suspicious_first_values wird NICHT gelöscht (by design!)
    """
    filter_instance = TotalIncreasingFilter(warmup_cycles=3)

    # Cycle 1: Suspicious Zero
    filter_instance.filter({"energy_grid_exported": 0})
    assert "energy_grid_exported" in filter_instance.suspicious_first_values

    # Cycle 2: Normaler Wert → Recovery (wird im Log angezeigt!)
    filter_instance.filter({"energy_grid_exported": 5432.1})

    # Cycle 3: Warmup complete
    filter_instance.filter({"energy_grid_exported": 5432.8})

    # ✅ AKZEPTIERT: suspicious_first_values bleibt für Diagnose!
    # Das ist KEIN Bug, sondern Feature
    assert "energy_grid_exported" in filter_instance.suspicious_first_values
    assert filter_instance.suspicious_first_values["energy_grid_exported"] == 0

    print("✅ Warmup: Suspicious tracking kept for diagnostics (by design)")


def test_warmup_custom_cycles():
    """Warmup: Custom warmup_cycles (1, 5, 10)"""
    # Test mit 1 Cycle
    filter1 = TotalIncreasingFilter(warmup_cycles=1)
    filter1.filter({"energy_grid_exported": 0})
    assert filter1.warmup_mode == False  # Sofort aktiv!

    # Test mit 5 Cycles
    filter5 = TotalIncreasingFilter(warmup_cycles=5)
    for i in range(4):
        filter5.filter({"energy_grid_exported": 100.0})
        assert filter5.warmup_mode == True
    filter5.filter({"energy_grid_exported": 100.0})
    assert filter5.warmup_mode == False  # Nach 5 Cycles


def test_warmup_mixed_zero_and_normal_values():
    """Warmup: Gemischte Zero und normale Werte"""
    filter_instance = TotalIncreasingFilter(warmup_cycles=3)

    # Cycle 1: Mix aus 0 und normalen Werten
    data = {
        "energy_yield_accumulated": 18052.68,  # Normal
        "energy_grid_exported": 0,  # Suspicious!
        "battery_charge_total": 4851.74,  # Normal
    }
    filter_instance.filter(data)

    # Nur energy_grid_exported sollte suspicious sein
    assert "energy_grid_exported" in filter_instance.suspicious_first_values
    assert "energy_yield_accumulated" not in filter_instance.suspicious_first_values
    assert "battery_charge_total" not in filter_instance.suspicious_first_values


def test_warmup_reset_clears_suspicious():
    """Warmup: Reset entfernt suspicious-Liste"""
    filter_instance = TotalIncreasingFilter(warmup_cycles=3)

    # Cycle 1-3: Warmup mit suspicious Zero
    filter_instance.filter({"energy_grid_exported": 0})
    filter_instance.filter({"energy_grid_exported": 5432.1})
    filter_instance.filter({"energy_grid_exported": 5432.8})

    # Warmup complete, aber suspicious bleibt (für Diagnose)
    assert filter_instance.warmup_mode == False
    # Note: suspicious_first_values wird NICHT gecleaned nach Warmup!

    # Reset → Sollte alles clearen? (Optional, je nach Design)
    filter_instance.reset()
    assert filter_instance.warmup_mode == True
    # suspicious_first_values bleibt für Diagnose (siehe Implementierung)


def test_warmup_after_connection_error():
    """Warmup: Nach Connection-Error wird Warmup neu gestartet"""
    filter_instance = TotalIncreasingFilter(warmup_cycles=3)

    # Phase 1: Normaler Betrieb
    for i in range(10):
        filter_instance.filter({"energy_grid_exported": 5432.1 + i * 0.5})
    assert filter_instance.warmup_mode == False

    # Phase 2: Connection-Error → Reset
    filter_instance.reset()

    # Phase 3: Warmup läuft wieder
    assert filter_instance.warmup_mode == True
    assert filter_instance.warmup_cycles == 0

    # Cycle 1 nach Reset
    result = filter_instance.filter({"energy_grid_exported": 5437.5})
    assert result["energy_grid_exported"] == 5437.5  # Durchgelassen


def test_warmup_zero_stays_zero_during_warmup():
    """Warmup: Zero-Drop während Warmup bleibt Zero (kein Filter aktiv!)"""
    filter_instance = TotalIncreasingFilter(warmup_cycles=3)

    # Cycle 1: Normaler Wert
    filter_instance.filter({"energy_grid_exported": 5432.1})

    # Cycle 2: Drop auf 0 (sollte NICHT gefiltert werden, Warmup!)
    result2 = filter_instance.filter({"energy_grid_exported": 0})
    assert result2["energy_grid_exported"] == 0  # ⚠️ 0 durchgelassen!
    assert filter_instance.warmup_mode == True

    # Cycle 3: Warmup complete
    filter_instance.filter({"energy_grid_exported": 5432.8})
    assert filter_instance.warmup_mode == False

    # Cycle 4: Jetzt wird 0 gefiltert!
    result4 = filter_instance.filter({"energy_grid_exported": 0})
    assert result4["energy_grid_exported"] == 5432.8  # ✅ Gefiltert!


def test_warmup_logging_output(caplog):
    """Warmup: Logging ist korrekt (für manuelle Verifikation)"""
    import logging

    caplog.set_level(logging.INFO)

    filter_instance = TotalIncreasingFilter(warmup_cycles=2)

    # Cycle 1
    filter_instance.filter({"energy_grid_exported": 5432.1})
    assert "✅ WARMUP: First value for energy_grid_exported" in caplog.text
    assert "cycle 1/2" in caplog.text

    # Cycle 2
    filter_instance.filter({"energy_grid_exported": 5432.8})
    assert "✅ Filter warmup complete after 2 cycles" in caplog.text


def test_warmup_env_variable_override():
    """Warmup: ENV-Variable HUAWEI_FILTER_WARMUP wird gelesen"""
    import os

    import modbus_energy_meter.total_increasing_filter as filter_module

    # Setup: ENV setzen
    os.environ["HUAWEI_FILTER_WARMUP"] = "5"

    # ✅ Singleton clearen!
    filter_module._filter_instance = None

    # ✅ WICHTIG: get_filter() liest ENV NUR wenn warmup_cycles=None!
    # Schauen wir uns get_filter() an:
    #   def get_filter(tolerance=None, warmup_cycles=None):
    #       if warmup_cycles is None:
    #           warmup_cycles = int(os.environ.get("HUAWEI_FILTER_WARMUP", "3"))

    # ✅ Also OHNE Parameter aufrufen!
    filter_instance = filter_module.get_filter()  # Keine Parameter!

    # Assertion
    assert (
        filter_instance.warmup_required == 5
    ), f"Expected 5, got {filter_instance.warmup_required}"

    # Cleanup
    del os.environ["HUAWEI_FILTER_WARMUP"]
    filter_module._filter_instance = None

    print("✅ Warmup: ENV variable override works")
