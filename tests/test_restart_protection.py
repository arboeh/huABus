"""
Tests für Restart-Protection des TotalIncreasingFilters.

Szenario (HANT Issue):
- Add-on startet neu
- Home Assistant hat noch alte Werte im State
- Erster Read liefert gültige Counter-Werte
- Filter muss diese akzeptieren (nicht als Drop interpretieren)

Ohne Fix:
- Filter wird NACH erstem Publish initialisiert
- Kurzer ungeschützter Moment → Zero-Drops möglich

Mit Fix:
- Filter wird VOR erstem Cycle initialisiert
- Alle Werte von Anfang an geschützt
"""

from bridge.total_increasing_filter import (
    TotalIncreasingFilter,
    get_filter,
    reset_filter,
)


class TestRestartProtection:
    """Tests für Addon-Restart Szenarien."""

    def setup_method(self):
        """Reset Filter vor jedem Test."""
        reset_filter()

    def test_first_value_after_restart_accepted(self):
        """
        HANT Issue: Erster Wert nach Restart muss akzeptiert werden.

        Szenario:
        1. Add-on startet neu (Filter hat keine last_values)
        2. Modbus liest: energy_yield_accumulated = 12345.6 kWh
        3. Filter muss diesen Wert akzeptieren (Baseline etablieren)
        4. Kein Zero-Drop in Home Assistant!
        """
        filter_instance = TotalIncreasingFilter()

        # Erster Read nach Restart
        data = {
            "energy_yield_accumulated": 12345.6,
            "battery_charge_total": 5678.9,
            "other_sensor": 42,
        }

        result = filter_instance.filter(data)

        # Alle Werte müssen durchkommen (nichts gefiltert)
        assert result == data
        assert filter_instance.get_stats() == {}  # Keine Filterung!

    def test_multiple_restarts_establish_new_baseline(self):
        """
        Mehrere Restarts hintereinander - jeder etabliert neue Baseline.

        Szenario:
        1. Restart #1: Filter akzeptiert 12000 kWh
        2. Restart #2: Filter akzeptiert 12100 kWh (höher - OK)
        3. Restart #3: Filter akzeptiert 12050 kWh (niedriger - wäre normalerweise Drop!)

        Nach Restart muss IMMER der erste Wert akzeptiert werden,
        auch wenn er niedriger ist als vorher (z.B. nach Inverter-Werksreset).
        """
        # === Restart #1 ===
        filter1 = TotalIncreasingFilter()
        data1 = {"energy_yield_accumulated": 12000.0}
        result1 = filter1.filter(data1)
        assert result1["energy_yield_accumulated"] == 12000.0

        # === Restart #2 ===
        reset_filter()  # Simuliert Addon-Restart
        filter2 = get_filter()
        data2 = {"energy_yield_accumulated": 12100.0}
        result2 = filter2.filter(data2)
        assert result2["energy_yield_accumulated"] == 12100.0
        assert filter2.get_stats() == {}  # Nicht gefiltert!

        # === Restart #3 mit NIEDRIGEREM Wert ===
        reset_filter()
        filter3 = get_filter()
        data3 = {"energy_yield_accumulated": 12050.0}  # Niedriger als vorher!
        result3 = filter3.filter(data3)
        assert result3["energy_yield_accumulated"] == 12050.0
        assert filter3.get_stats() == {}  # Nicht gefiltert! (Nach Restart OK)

    def test_no_zero_drop_on_restart(self):
        """
        HANT's Grafana-Screenshot: Zero-Drops beim Restart verhindern.

        Szenario wie im Screenshot:
        - Vor Restart: 9799.5 kWh (in HA State)
        - Add-on startet neu
        - Erster Read: 9799.5 kWh (selber Wert!)
        - Ohne Fix: Kurzer Drop auf 0 sichtbar
        - Mit Fix: Kein Drop, durchgehend 9799.5 kWh
        """
        filter_instance = TotalIncreasingFilter()

        # Erster Cycle nach Restart - gleicher Wert wie vorher in HA
        data = {
            "energy_yield_accumulated": 9799.5,
            "battery_charge_total": 1234.5,
            "energy_grid_exported": 5678.9,
        }

        result = filter_instance.filter(data)

        # Alle Werte durchgekommen - kein Drop!
        assert result["energy_yield_accumulated"] == 9799.5
        assert result["battery_charge_total"] == 1234.5
        assert result["energy_grid_exported"] == 5678.9

        # Wichtig: KEINE Filterung passiert!
        stats = filter_instance.get_stats()
        assert stats == {}, f"Unexpected filtering on first cycle: {stats}"

    def test_subsequent_cycles_after_restart_protected(self):
        """
        Nach Restart: Zweiter und weitere Cycles sind geschützt.

        Szenario:
        1. Cycle #1 nach Restart: 12345.6 kWh → akzeptiert (Baseline)
        2. Cycle #2: 12346.2 kWh → akzeptiert (höher)
        3. Cycle #3: 12340.0 kWh → GEFILTERT (Drop!)
        """
        filter_instance = TotalIncreasingFilter()

        # Cycle #1 - Baseline
        data1 = {"energy_yield_accumulated": 12345.6}
        result1 = filter_instance.filter(data1)
        assert result1["energy_yield_accumulated"] == 12345.6

        # Cycle #2 - Höher OK
        data2 = {"energy_yield_accumulated": 12346.2}
        result2 = filter_instance.filter(data2)
        assert result2["energy_yield_accumulated"] == 12346.2

        # Cycle #3 - Drop → GEFILTERT!
        data3 = {"energy_yield_accumulated": 12340.0}
        result3 = filter_instance.filter(data3)
        assert result3["energy_yield_accumulated"] == 12346.2  # Last valid!
        assert filter_instance.get_stats() == {"energy_yield_accumulated": 1}

    def test_mixed_sensors_first_cycle(self):
        """
        Erster Cycle mit Mix aus total_increasing und anderen Sensoren.

        Nur total_increasing Keys werden vom Filter behandelt,
        andere Sensoren gehen unverändert durch.
        """
        filter_instance = TotalIncreasingFilter()

        data = {
            # total_increasing - Filter behandelt diese
            "energy_yield_accumulated": 12345.6,
            "battery_charge_total": 5678.9,
            # Andere Sensoren - Filter ignoriert diese
            "power_active": 4500,
            "battery_soc": 85.5,
            "voltage_PV1": 380.2,
        }

        result = filter_instance.filter(data)

        # Alle Werte unverändert
        assert result == data
        assert filter_instance.get_stats() == {}

    def test_zero_values_on_first_cycle(self):
        """
        Erster Cycle nach Restart mit 0-Werten.

        Szenario: Inverter war nachts aus, Counter stehen auf 0
        → Muss akzeptiert werden (ist valider Startzustand)
        """
        filter_instance = TotalIncreasingFilter()

        data = {
            "energy_yield_accumulated": 0.0,
            "battery_charge_total": 0.0,
            "energy_grid_exported": 0.0,
        }

        result = filter_instance.filter(data)

        # 0-Werte beim ersten Cycle sind OK (Baseline)
        assert result == data
        assert filter_instance.get_stats() == {}

    def test_negative_values_always_filtered(self):
        """
        Negative Werte werden IMMER gefiltert, auch beim ersten Cycle.

        Negative Werte bei Energy Countern sind physikalisch unmöglich
        → Modbus-Fehler, auch bei erster Messung
        """
        filter_instance = TotalIncreasingFilter()

        data = {
            "energy_yield_accumulated": -123.4,  # Unmöglich!
            "battery_charge_total": 5678.9,  # OK
        }

        result = filter_instance.filter(data)

        # Negativer Wert fehlt (gefiltert), positiver bleibt
        assert "energy_yield_accumulated" not in result
        assert result["battery_charge_total"] == 5678.9

        # Wurde als "gefiltert" gezählt (weil aktiv entfernt!)
        assert filter_instance.get_stats() == {"energy_yield_accumulated": 1}


class TestSingletonBehavior:
    """Tests für Singleton-Verhalten über Restart hinweg."""

    def test_get_filter_returns_same_instance(self):
        """get_filter() gibt immer dieselbe Instanz zurück."""
        reset_filter()

        filter1 = get_filter()
        filter2 = get_filter()

        assert filter1 is filter2  # Selbes Objekt!

    def test_reset_filter_clears_singleton(self):
        """reset_filter() löscht Singleton, nächster get_filter() erstellt neu."""
        reset_filter()

        filter1 = get_filter()
        filter1.filter({"energy_yield_accumulated": 12345.6})

        # Reset (löscht Singleton-Instanz komplett!)
        reset_filter()

        filter2 = get_filter()

        # Neues Objekt nach Reset (unterschiedliche Instanz!)
        assert filter2 is not filter1  # ← Sollte jetzt passen!
        # Keine last_values mehr
        assert filter2.get_stats() == {}


class TestEdgeCases:
    """Edge Cases rund um Restart-Szenario."""

    def test_very_small_increment_after_restart(self):
        """
        Sehr kleiner Increment nach Restart (< 0.1 kWh).

        Szenario: Zweiter Cycle kurz nach Restart, nur 0.001 kWh mehr
        → Muss akzeptiert werden (kein Filter-Threshold in v1.7.0!)
        """
        reset_filter()
        filter_instance = get_filter()

        # Cycle #1
        data1 = {"energy_yield_accumulated": 12345.678}
        filter_instance.filter(data1)

        # Cycle #2 - winziger Increment
        data2 = {"energy_yield_accumulated": 12345.679}  # +0.001 kWh
        result = filter_instance.filter(data2)

        assert result["energy_yield_accumulated"] == 12345.679
        assert filter_instance.get_stats() == {}  # Nicht gefiltert!

    def test_large_jump_after_restart(self):
        """
        Großer Sprung nach Restart (z.B. nach Firmware-Update).

        Szenario:
        - Vor Restart: 12000 kWh
        - Restart
        - Nach Restart: 15000 kWh (3000 kWh mehr - unrealistisch aber möglich)
        → Muss akzeptiert werden (erster Wert nach Restart)
        """
        reset_filter()
        filter_instance = get_filter()

        # Erster Wert nach Restart - sehr hoch
        data = {"energy_yield_accumulated": 15000.0}
        result = filter_instance.filter(data)

        assert result["energy_yield_accumulated"] == 15000.0
        assert filter_instance.get_stats() == {}

    def test_all_keys_missing_on_first_cycle(self):
        """
        Erster Cycle, aber keine total_increasing Keys vorhanden.

        Szenario: Nur andere Sensoren gelesen (power, voltage, etc.)
        → Filter macht nichts, gibt data unverändert zurück
        """
        reset_filter()
        filter_instance = get_filter()

        data = {
            "power_active": 4500,
            "battery_soc": 85,
            "voltage_PV1": 380,
        }

        result = filter_instance.filter(data)

        assert result == data
        assert filter_instance.get_stats() == {}
