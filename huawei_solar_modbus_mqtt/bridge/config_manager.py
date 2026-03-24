# huawei_solar_modbus_mqtt/bridge/config_manager.py

"""
Konfigurationsmanager für Huawei Solar Modbus MQTT Bridge.

Verwaltet das Laden der Konfiguration von:
  - Umgebungsvariablen (Docker/Add-on-Laufzeit)
  - /data/options.json (Home Assistant-Add-on)
  - Standardwerte (Entwicklung)

Verwendet eine flache Konfigurationsstruktur (keine Verschachtelung) für Home Assistant-Kompatibilität.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, cast

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manage add-on configuration with validation."""

    def __init__(self, config_path: Path | None = None):
        """
        Initialize ConfigManager.

        Args:
            config_path: Path to options.json (default: /data/options.json)
        """
        self.config_path = config_path or Path("/data/options.json")
        self._config: dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """
        Load configuration from file or environment variables.
        """
        if self.config_path.exists():
            logger.info(f"🚀 Loading configuration from {self.config_path}")
            with open(self.config_path) as f:
                self._config = json.load(f)
            logger.debug(f"✅ Loaded config keys: {list(self._config.keys())}")
        else:
            logger.info("🔍 No config file found, loading from environment variables")
            self._config = self._load_from_env()

    def _load_from_env(self) -> dict[str, Any]:
        """
        Load configuration from environment variables.

        Returns:
            Configuration dictionary with flat structure
        """
        return {
            # Modbus settings
            "modbus_host": os.getenv("HUAWEI_MODBUS_HOST", "192.168.1.100"),
            "modbus_port": self._parse_int_env("HUAWEI_MODBUS_PORT", default=502),
            "modbus_auto_detect_slave_id": self._parse_bool_env("HUAWEI_MODBUS_AUTO_DETECT_SLAVE_ID", default=True),
            "slave_id": self._parse_int_env("HUAWEI_SLAVE_ID", default=1),
            # MQTT settings
            "mqtt_host": os.getenv("HUAWEI_MQTT_HOST", "core-mosquitto"),
            "mqtt_port": self._parse_int_env("HUAWEI_MQTT_PORT", default=1883),
            "mqtt_user": os.getenv("HUAWEI_MQTT_USER", ""),
            "mqtt_password": os.getenv("HUAWEI_MQTT_PASSWORD", ""),
            "mqtt_topic": os.getenv("HUAWEI_MQTT_TOPIC", "huawei-solar"),
            # Advanced settings
            "log_level": os.getenv("HUAWEI_LOG_LEVEL", "INFO"),
            "status_timeout": self._parse_int_env("HUAWEI_STATUS_TIMEOUT", default=180),
            "poll_interval": self._parse_int_env("HUAWEI_POLL_INTERVAL", default=30),
        }

    @staticmethod
    def _parse_bool_env(key: str, default: bool = False) -> bool:
        """
        Parse boolean environment variable.

        Args:
            key: Environment variable name
            default: Default value if not set

        Returns:
            Boolean value
        """
        value = os.getenv(key)
        if value is None:
            return default
        return value.lower() in ("true", "1", "yes", "on")

    @staticmethod
    def _parse_int_env(key: str, default: int = 0) -> int:
        """
        Parse integer environment variable.

        Args:
            key: Environment variable name
            default: Default value if not set or invalid

        Returns:
            Integer value
        """
        value = os.getenv(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            logger.warning(f"❌ Invalid integer value for {key}: {value}, using default {default}")
            return default

    # === Modbus Configuration ===

    @property
    def modbus_host(self) -> str:
        """Get Modbus host IP address."""
        return cast(str, self._config.get("modbus_host", "192.168.1.100"))

    @property
    def modbus_port(self) -> int:
        """Get Modbus TCP port."""
        return cast(int, self._config.get("modbus_port", 502))

    @property
    def modbus_auto_detect_slave_id(self) -> bool:
        """Get auto-detect slave ID setting (new in 1.8.0)."""
        return cast(bool, self._config.get("modbus_auto_detect_slave_id", True))

    @property
    def slave_id(self) -> int:
        """Get Modbus slave ID."""
        return cast(int, self._config.get("slave_id", 1))

    # === MQTT Configuration ===

    @property
    def mqtt_host(self) -> str:
        """Get MQTT broker hostname."""
        return cast(str, self._config.get("mqtt_host", "core-mosquitto"))

    @property
    def mqtt_port(self) -> int:
        """Get MQTT broker port."""
        return cast(int, self._config.get("mqtt_port", 1883))

    @property
    def mqtt_user(self) -> str | None:
        """Get MQTT username (optional)."""
        user = self._config.get("mqtt_user", "")
        return user if user else None

    @property
    def mqtt_password(self) -> str | None:
        """Get MQTT password (optional)."""
        password = self._config.get("mqtt_password", "")
        return password if password else None

    @property
    def mqtt_topic(self) -> str:
        """Get MQTT topic prefix."""
        return cast(str, self._config.get("mqtt_topic", "huawei-solar"))

    # === Advanced Configuration ===

    @property
    def log_level(self) -> str:
        """Get log level (TRACE, DEBUG, INFO, WARNING, ERROR)."""
        return cast(str, self._config.get("log_level", "INFO")).upper()

    @property
    def status_timeout(self) -> int:
        """Get status timeout in seconds."""
        return cast(int, self._config.get("status_timeout", 180))

    @property
    def poll_interval(self) -> int:
        """Get poll interval in seconds."""
        return cast(int, self._config.get("poll_interval", 30))

    # === Validation ===

    def validate(self) -> list[str]:
        """Validate configuration.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Modbus validation
        if not self.modbus_host:
            errors.append("modbus_host is required")

        if not (1 <= self.modbus_port <= 65535):
            errors.append(f"modbus_port must be 1-65535, got {self.modbus_port}")

        if not self.modbus_auto_detect_slave_id:
            if not (0 <= self.slave_id <= 247):
                errors.append(f"slave_id must be 0-247, got {self.slave_id}")

        # MQTT validation
        if not self.mqtt_host:
            errors.append("mqtt_host is required")

        if not (1 <= self.mqtt_port <= 65535):
            errors.append(f"mqtt_port must be 1-65535, got {self.mqtt_port}")

        if not self.mqtt_topic:
            errors.append("mqtt_topic is required")

        # Advanced validation
        valid_log_levels = ["TRACE", "DEBUG", "INFO", "WARNING", "ERROR"]
        if self.log_level not in valid_log_levels:
            errors.append(f"log_level must be one of {valid_log_levels}, got {self.log_level}")

        if not (30 <= self.status_timeout <= 600):
            errors.append(f"status_timeout must be 30-600 seconds, got {self.status_timeout}")

        if not (10 <= self.poll_interval <= 300):
            errors.append(f"poll_interval must be 10-300 seconds, got {self.poll_interval}")

        return errors

    def __repr__(self) -> str:
        """String representation (without sensitive data)."""
        return (
            f"ConfigManager("
            f"modbus={self.modbus_host}:{self.modbus_port}, "
            f"mqtt={self.mqtt_host}:{self.mqtt_port}, "
            f"topic={self.mqtt_topic}, "
            f"log_level={self.log_level}, "
            f"poll={self.poll_interval}s)"
        )

    def log_config(self) -> None:
        """Log current configuration (for debugging)."""

        # Modbus
        logger.debug("Modbus:")
        logger.debug(f"  Host: {self.modbus_host}")
        logger.debug(f"  Port: {self.modbus_port}")
        logger.debug(f"  Auto-detect Slave ID: {self.modbus_auto_detect_slave_id}")
        if not self.modbus_auto_detect_slave_id:
            logger.debug(f"  Slave ID: {self.slave_id}")

        # MQTT
        logger.debug("MQTT:")
        logger.debug(f"  Host: {self.mqtt_host}")
        logger.debug(f"  Port: {self.mqtt_port}")

        if self.mqtt_user:
            logger.debug(f"  User: {self.mqtt_user}")
            if self.mqtt_password:
                # Always mask password in logs to prevent clear-text logging of sensitive data
                logger.debug("  Password: ***")
        else:
            logger.debug("  Auth: None")

        logger.debug(f"  Topic: {self.mqtt_topic}")

        # Advanced
        logger.debug("Advanced:")
        logger.debug(f"  Log Level: {self.log_level}")
        logger.debug(f"  Status Timeout: {self.status_timeout}s")
        logger.debug(f"  Poll Interval: {self.poll_interval}s")
