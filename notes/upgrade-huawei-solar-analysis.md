# Upgrade Analysis: huawei-solar 2.5.0 → 3.0.7

## 1. Current State

| Item | Value |
|------|-------|
| **Pinned version** | `huawei-solar==2.5.0` (in `requirements.txt`) |
| **pyproject.toml range** | `huawei-solar>=2.5,<2.6` |
| **Add-on version** | `1.10.4` (in `config.yaml`) |
| **Python requirement** | `>=3.11` (pyproject.toml), `pythonVersion: 3.11` (pyrightconfig.json) |
| **Direct deps** | `huawei-solar`, `pymodbus>=3.9,<4`, `paho-mqtt>=2.1,<2.2` |

## 2. Target Version

| Item | Value |
|------|-------|
| **Latest stable on PyPI** | `3.0.7` (released 2026-08-11 via GitHub Actions) |
| **Latest tag on GitHub** | `v3.0.7` |
| **Library repo** | https://github.com/wlcrs/huawei-solar-lib |

Available pre-release/alpha versions observed on PyPI: `3.0.0a1`–`3.0.0a6`.
Stable releases on GitHub/PyPI: `v3.0.0`, `v3.0.1`–`v3.0.7`.

## 3. Breaking Changes (2.5.0 → 3.0.7)

### 3.1 Class rename: `AsyncHuaweiSolar` → `AsyncHuaweiSolarClient`

- **Old:** `from huawei_solar import AsyncHuaweiSolar`
- **New:** `from huawei_solar import AsyncHuaweiSolarClient, create_tcp_client`
- `AsyncHuaweiSolar` is **completely removed** (no longer exported).
- `HuaweiSolarBridge` is also **removed** (not used by this add-on).

### 3.2 Client creation: `AsyncHuaweiSolar.create()` → `create_tcp_client()` + `connect()`

- **Old (async, connect-and-create):**
  ```python
  client = await AsyncHuaweiSolar.create(host, port, slave_id)
  ```
- **New (sync factory + async connect):**
  ```python
  client = create_tcp_client(host, port, unit_id=slave_id)
  await client.connect()
  ```
- `create_tcp_client` is a **synchronous** factory function that returns an
  `AsyncHuaweiSolarClient` instance. It does **not** connect.
- Connection is established by calling `await client.connect()`.
- `create_tcp_client` signature:
  ```
  create_tcp_client(host, port=502, *, unit_id=0, timeout=10,
                   wait_after_connect=1.0, wait_between_requests=0.05,
                   consecutive_timeouts_before_reconnect=5) -> AsyncHuaweiSolarClient
  ```
- The old `slave_id` parameter is now `unit_id` (keyword-only).

### 3.3 Cleanup: `client.stop()` → `client.disconnect()`

- **Old:** `await client.stop()`
- **New:** `await client.disconnect()`
- Both are async methods that close the transport.
- `connected` is now a **property** (not a method).

### 3.4 Exception hierarchy: `pymodbus` removed entirely

- **`pymodbus` is no longer a dependency** of the library (replaced by `tmodbus`).
- `pymodbus.exceptions.ModbusException` and `pymodbus.pdu.ExceptionResponse`
  are **no longer importable** in a 3.0.7 environment.
- Library now exposes its own exceptions in `huawei_solar.exceptions`:
  | Old (pymodbus) | New (huawei_solar.exceptions) |
  |---|---|
  | `ModbusException` (base) | `ReadException` (read/protocol errors) |
  | `ExceptionResponse` | `DecodeError(ReadException)` (protocol error responses) |
  | `ModbusIOException` | `ReadException` |
  | `ConnectionException` (pymodbus) | `ConnectionException` (library) |
  | *(asyncio timeout)* | `ConnectionInterruptedException` (library) |
  | `TimeoutError` / `asyncio.TimeoutError` | Still raised (Python built-in) |

  Exception hierarchy:
  ```
  BaseException
  └── Exception
      └── HuaweiSolarException          (base for all library exceptions)
          ├── ConnectionException        (connection-level)
          ├── ConnectionInterruptedException (connection interrupted/timeouts)
          ├── ReadException              (read/protocol-level)
          │   └── DecodeError            (decode failures)
          ├── WriteException
          ├── EncodeError
          ├── DecodeError
          ├── DeviceDetectionError
          ├── InvalidCredentials
          ├── PeakPeriodsValidationError
          ├── TimeOfUsePeriodsException
          └── UnexpectedResponseContent
  ```

- `ConnectionInterruptedException` is **NOT** a subclass of `TimeoutError`.
- `ConnectionException` is **NOT** a subclass of `ConnectionRefusedError`.

### 3.5 `register_names` / `rn.*` changes

- The `huawei_solar.register_names` module **still exists** in v3.0.7.
- `RegisterName` is `NewType('RegisterName', str)` — plain strings still work at runtime.
- **Register name format changed:** v2 used lowercase names accessible as `rn.active_power`; v3 uses UPPER_CASE constants like `rn.ACTIVE_POWER`.
- **However**, the `REGISTERS` dict keys remain lowercase strings
  (e.g., `'active_power'`), which is what this add-on uses via
  `batch_builder.py` (`_get_huawei_registers()`).
- Impact: **None** — the add-on uses lowercase string keys, not `rn.*` constants.

### 3.6 `get_multiple()` and `get()` API

- **Signature change (type annotation only, runtime-compatible):**
  - v2: `get_multiple(names: list[str]) -> list[RegisterValue]`
  - v3: `get_multiple(names: list[RegisterName]) -> list[Result]`
  - `get(name: str) -> Result` / `get(name: RegisterName) -> Result`
- `Result` dataclass: `Result(value: T, unit: str | None)` — same `.value` and `.unit` attributes as v2 `RegisterValue`.
- **Runtime compatible:** Plain string register names still work (NewType at runtime).

### 3.7 `REGISTERS` and `RegisterDefinition`

- `huawei_solar.registers.REGISTERS` — **still exists**, now has 744 entries (was 100+).
- `huawei_solar.registers.RegisterDefinition` — **still exists**, now a class hierarchy
  (e.g., `I32Register`, `U32Register`, `StringRegister`).
- Same attributes: `.register`, `.length`, `.unit`, `.readable`, `.writeable`, etc.
- **Impact: None** — `batch_builder.py` uses `reg.register` and `reg.length`, which still exist.

### 3.8 Python version requirement

- **v3.0.0+ requires Python >=3.12** (was >=3.11 in v2.5.0).
- `pip3 show huawei-solar` metadata: `Requires-Python: >=3.12`

### 3.9 Dependency changes

| Dependency | v2.5.0 | v3.0.7 |
|---|---|---|
| `pymodbus` | `>=3.9,<4` (direct + transitive) | **Removed** |
| `pyserial-asyncio` | 0.6 (transitive) | **Removed** |
| `backoff` | 2.2.1 (transitive) | **Removed** |
| `pytz` | 2026.3.post1 (transitive) | **Removed** |
| `tmodbus[async-serial]` | — | **New** (transitive) |
| `serialx` | — | **New** (transitive) |
| `tenacity` | — | **New** (transitive) |
| `pywin32` | — | New (transitive, Windows only) |

### 3.10 Release notes summary (v3.0.0 → v3.0.7)

- **v3.0.0** — Replace pyModbus with tModbus; Add SDongle and SmartLogger support. **MAJOR** breaking change.
- **v3.0.1** — Add 'scan' clients with stricter timeouts/retries for slave-id probing; Replace asserts with proper exceptions.
- **v3.0.2** — Don't crash on unexpected error during permission-probing.
- **v3.0.3** — Properly encode values when setting a single register.
- **v3.0.4** — Add EMMA 31002/31003 register support.
- **v3.0.5** — Add power meter via SmartLogger support; Fix SmartLogger device detection.
- **v3.0.6** — Properly wrap tmodbus exceptions in all functions.
- **v3.0.7** — Fix gain of external power meter voltage and current registers.

## 4. Impact Analysis on huABus Add-on

### 4.1 Source files requiring changes

| File | Change |
|---|---|
| `bridge/main.py` | Import: `AsyncHuaweiSolar` → `AsyncHuaweiSolarClient` + `create_tcp_client`. Client creation: `AsyncHuaweiSolar.create()` → `create_tcp_client()` + `await client.connect()`. Exception imports: `pymodbus` → `huawei_solar.exceptions`. Type hints updated. |
| `bridge/slave_detector.py` | Same import + creation changes. `client.stop()` → `client.disconnect()`. |
| `bridge/batch_builder.py` | No changes needed — `REGISTERS` and `RegisterDefinition` still exist with same attributes. |
| `bridge/transform.py` | No changes needed — `Result.value` / `Result.unit` compatible with existing `RegisterValue.value` / `.unit` access. |
| `bridge/error_tracker.py` | `ErrorType` Literal may be extended (new exception types mapped to existing categories). |
| `pyproject.toml` | Version range `2.5,<2.6` → `3.0,<3.1`. Remove `pymodbus>=3.9,<4`. `requires-python` → `>=3.12`. |
| `run.sh` | Update pymodbus version display → tmodbus (cosmetic, line 180). |

### 4.2 Test files requiring changes

| File | Change |
|---|---|
| `tests/test_main.py` | Replace `AsyncHuaweiSolar.create` patches → `create_tcp_client` patches. Replace `from pymodbus.exceptions import ModbusException` → `huawei_solar.exceptions.ReadException`. |
| `tests/test_slave_detector.py` | Same patch replacements. `mock_client.stop` → `mock_client.disconnect`. Timeout/error simulation moves from `create` to `connect`. |
| `tests/test_logging.py` | Replace `patch("bridge.slave_detector.AsyncHuaweiSolar")` → `patch("bridge.slave_detector.create_tcp_client")`. |
| `tests/test_error_tracker.py` | Replace `from pymodbus.exceptions import ModbusException` → library exception. |
| `tests/fixtures/mock_inverter.py` | Update comment referencing pymodbus (class itself is standalone, no import change needed). |

### 4.3 Backward compatibility verification

- **Config options** (`config.yaml`): **No changes** — `modbus_host`, `slave_id`, `enable_batching`, etc. remain the same.
- **MQTT topics** and **payload structure**: **No changes** — register names, mappings, sensor definitions, and `examples/mqtt_payload.json` remain unchanged.
- **ESSENTIAL_REGISTERS**: **No changes** — all existing register names are still valid keys in the new `REGISTERS` dict (744 entries vs ~100+ before; existing names are a subset).
- **`is_modbus_exception()` behavior**: Mapped to new library's `ReadException` instead of pymodbus's `ModbusException`. Functionally equivalent (identifies protocol-level errors).

## 5. Weitere Dependencies (Ergänzungsauftrag)

### Task A — pymodbus-Direktdependency auflösen

- **Status**: Vollständig gelöst.
- Es existieren keine `import pymodbus`-Anweisungen mehr in `bridge/*.py` oder `tests/*.py` (geprüft via `Select-String`).
- Der einzige verbleibende `pymodbus`-Referenz ist ein veralteter Kommentar in `tests/fixtures/mock_inverter.py` (Zeile 21), der auf `pymodbus-Exception` verwiesen hat. Dieser wurde aktualisiert auf `huawei_solar.exceptions.ReadException`.
- `pymodbus>=3.9,<4` wurde bere bereits in `pyproject.toml` aus `[project.dependencies]` entfernt (Task 2 des Haupt-Upgrade-Auftrags).
- **Ergebnis**: Keine weiteren Maßnahmen erforderlich. pymodbus ist vollständig aus dem Abhängigkeitsbaum entfernt.

### Task B — mypy-Override anpassen

- **Status**: Erledigt.
- Der `[[tool.mypy.overrides]]` Block für `module = ["pymodbus.*"]` wurde aus `pyproject.toml` entfernt (war noch vorhanden, obwohl pymodbus bereits entfernt war).
- `uv run mypy` wurde ausgeführt; mypy meldete `unused section(s): module = ['pymodbus.*']` — bestätigt, dass der Override entbehrlich war.
- **Testweise tmodbus-Override**: Nicht erforderlich. mypy meldete keine fehlenden Type Stubs für `tmodbus` (keine `Cannot find implementation or library stub for module named "tmodbus"` Fehler). Es wurden lediglich 7 vorhandene Type-Annotation-Fehler gemeldet (siehe unten).
- **Offener Punkt — mypy-Fehler nach v3-API-Wechsel**: 7 mypy-Fehler betreffen `RegisterName`-Type-Mismatches (`str` vs `RegisterName` in `client.get()`/`client.get_multiple()`-Aufrufen in `bridge/main.py:330,356,363,403` und `bridge/slave_detector.py:90`) und `ErrorType`-Literal-Mismatches in `bridge/main.py:694,703`. Diese sind Laufzeit-kompatibel (NewType ist zur Laufzeit ein `str`), aber mypy ist strikter. Diese sollten in einem Folge-Schritt mit `# type: ignore[arg-type]` oder `cast(RegisterName, ...)` kommentiert werden.

### Task C — Lockfile-Diff verifizieren

- **Status**: Bestätigt.
- `git diff --cached -- huawei_solar_modbus_mqtt/requirements.txt` zeigt:
  - **Entfernt**: `backoff==2.2.1`, `pymodbus==3.15.0`, `pyserial==3.5`, `pyserial-asyncio==0.6`, `pytz==2026.3.post1`
  - **Neu**: `tmodbus==0.5.1` (via huawei-solar), `serialx==1.8.2` (via tmodbus), `tenacity==9.1.4` (via tmodbus)
  - **Aktualisiert**: `huawei-solar==2.5.0` → `huawei-solar==3.0.7`
- **pywin32**: Nicht in `requirements.txt` vorhanden. `uv export` hat die Windows-only-Transitive-Dependency korrekt ausgeschlossen (plattform-abhängiger Marker oder `--no-dev`-Export auf Linux/Windows-Build-Maschine hat sie weggefiltert). **Kein Docker-Build-Risiko.**

### Task D — paho-mqtt separat bewerten

- **Status**: Keine Änderung erforderlich.
- `paho-mqtt` aktuell und neueste stabile Version auf PyPI: **2.1.0** (identisch mit gepinntem Bereich `>=2.1,<2.2`).
- Verfügbare Versionen: 2.1.0, 2.0.0, 1.6.1, 1.6.0, 1.5.1, 1.5.0, 1.4.0, 1.3.1, 1.3.0, 1.2.3, 1.2.2, 1.2.1, 1.2, 1.1, 1.0, 0.9.1, 0.9, 0.4.94, 0.4.92, 0.4.91, 0.4.90.
- Keine neuere Minor- oder Major-Version mit Breaking Changes. paho-mqtt ist unabhängig vom huawei-solar-Upgrade und bleibt unverändert im gleichen Branch/Commit.

### Task E — Dev-Dependency-Gruppe separat behandeln

- **Status**: Keine Änderungen vorgenommen.
- Dev-Dependencies (`pytest`, `pytest-asyncio`, `pytest-cov`, `pytest-mock`, `mypy`, `pyyaml`, `ruff`, `pre-commit`) werden NICHT im Rahmen dieses huawei-solar-Upgrades aktualisiert.
- Ein pauschales Dev-Dependency-Update (`uv lock --upgrade`) ist als separater Folge-Task/Branch nach expliziter Freigabe durch den Nutzer geplant.

## 6. Task 4 — Dockerfile/build.yaml Python 3.12 Kompatibilität

- **Status**: Kompatibel, keine Änderungen erforderlich.
- **Base Image**: `build.yaml` verwendet `ghcr.io/home-assistant/<arch>-base:latest`. Laut HA docker-base Repository (https://github.com/home-assistant/docker-base) handelt es sich um Alpine-basierte Images (aktuelle `:latest` = Alpine 3.24).
- **Python-Version**: Alpine 3.24 shippt Python 3.12+ in den Standard-Repos. Der Dockerfile-Befehl `apk add --no-cache python3 py3-pip bash` installiert somit Python >= 3.12, was `requires-python = ">=3.12"` erfüllt.
- **Dockerfile**: Keine Python-Versions-Pinning — verwendet `python3` aus dem Base-Image. Kompatibel mit `huawei-solar>=3.0,<3.1` (erfordert Python >=3.12).
- **build.yaml**: Verwendet `:latest`-Tags für alle 5 Architekturen (`aarch64`, `amd64`, `armhf`, `armv7`, `i386`). Diese sind zwar als "deprecated" in Bezug auf multi-arch Images markiert, aber weiterhin verfügbar und funktionieren. Ein Wechsel zu multi-arch Images (`ghcr.io/home-assistant/base:latest`) ist ein separater Optimierungsvorschlag, nicht Teil dieses Upgrades.
- **run.sh**: Zeigt zur Laufzeit die Python-Version an (Zeile 176: `python3 --version`). Zeigt außerdem `tmodbus` und `paho-mqtt` Versionen an (Zeilen 180-190). Keine Anpassung erforderlich.
- **requirements.txt**: Alle Pakete (`huawei-solar`, `paho-mqtt`, `tmodbus`, `serialx`, `tenacity`) sind reine Python-Pakete (keine C-Extension-Abhängigkeiten) und kompatibel mit allen unterstützten Architekturen.

## 7. SECURITY.md — Puffer dependency cleanup

- **Status**: Aktualisiert.
- `SECURITY.md` Zeile 98 listete `pymodbus` als überwachte Dependency. Da pymodbus vollständig entfernt wurde, wurde der Eintrag auf `tmodbus` aktualisiert (Zeile 98). `paho-mqtt` bleibt unverändert.
