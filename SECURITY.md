# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.8.x   | :white_check_mark: |

## Reporting a Vulnerability

### Private Disclosure (Recommended)

Use GitHub's [Private Vulnerability Reporting](https://github.com/arboeh/huABus/security/advisories/new):

- ✅ Confidential until fixed
- ✅ Tracked via Security Advisories
- ✅ CVE assignment if applicable

### Public Disclosure

For non-critical issues:

- Open a [GitHub Issue](https://github.com/arboeh/huABus/issues)
- Use the Security Issue template if available

### Response Time

- **Critical**: 24-48 hours
- **High**: 7 days
- **Medium/Low**: 14 days

---

## Security Features

### Automated Security

- **CodeQL Analysis**: Automatic code scanning for Python vulnerabilities
- **Dependabot**: Weekly dependency security updates
- **GitHub Actions Permissions**: Least-privilege (`contents: read`)

### Container Security

- **AppArmor Profile**: Container isolation with minimal file system access
- **Non-root Execution**: Runs with reduced privileges
- **Network Isolation**: No host network access required

### Development Security

- **Pre-commit Hooks**: Automatic code quality checks (ruff)
- **Test Coverage**: 86% code coverage with security-focused tests
- **Type Checking**: MyPy static analysis

---

## Known Limitations

### Modbus Security

⚠️ **Modbus TCP is unencrypted**:

- Use only on trusted networks (VLAN recommended)
- No authentication mechanism in Modbus protocol
- Consider firewall rules to restrict access

### MQTT Security

✅ **TLS/SSL supported** (configure via Home Assistant MQTT)  
⚠️ **Credentials in plain text** (stored in Home Assistant Supervisor)

### Auto-Detection Security

ℹ️ **Slave ID Auto-Detection**:

- Tries multiple Slave IDs (0, 1, 2, 100) on startup
- No security risk - only connects to configured inverter IP
- Can be disabled via `modbus_auto_detect_slave_id: false`

---

## Security Audit Log

| Date       | Change                              | Impact                       |
| ---------- | ----------------------------------- | ---------------------------- |
| 2026-02-10 | v1.8.0: Auto Slave ID detection     | No security impact           |
| 2026-02-10 | Enhanced MQTT auto-config           | Improved credential handling |
| 2026-02-06 | Added `permissions: contents: read` | Reduced GITHUB_TOKEN scope   |
| 2026-02-03 | Added AppArmor profile              | Container isolation          |
| 2026-02-03 | Disabled host network access        | Network isolation            |

---

## Dependencies

Monitored via Dependabot:

- `huawei-solar`
- `pymodbus`
- `paho-mqtt`

See [requirements.txt](requirements.txt) for full list.

---

## Best Practices

### Network Security

1. **VLAN Isolation**: Place inverter on separate VLAN
2. **Firewall Rules**: Restrict Modbus port 502 access
3. **MQTT TLS**: Enable TLS in Home Assistant MQTT broker

### Configuration Security

1. **Credentials**: Use Home Assistant MQTT Service (auto-config)
2. **Logging**: Avoid `TRACE` level in production (exposes raw data)
3. **Updates**: Enable Dependabot alerts

### Monitoring

1. **Check Logs**: Review for unusual connection attempts
2. **Status Sensor**: Monitor `binary_sensor.huawei_solar_status`
3. **Error Tracking**: Watch for repeated authentication failures

---

## Disclosure Policy

- Security vulnerabilities are disclosed after fix is available
- Credit given to researchers who report responsibly
- CVEs assigned for critical vulnerabilities
