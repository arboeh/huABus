# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.7.x   | :white_check_mark: |
| < 1.7   | :x:                |

## Reporting a Vulnerability

### Private Disclosure (Recommended)

Use GitHub's [Private Vulnerability Reporting](https://github.com/arboeh/huABus/security/advisories/new):

- ✅ Confidential until fixed
- ✅ Tracked via Security Advisories
- ✅ CVE assignment if applicable

### Public Disclosure

For non-critical issues:

- Open a [GitHub Issue](https://github.com/arboeh/huABus/issues)
- Email: [your-email]

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

---

## Security Audit Log

| Date       | Change                              | Impact                     |
| ---------- | ----------------------------------- | -------------------------- |
| 2026-02-06 | Added `permissions: contents: read` | Reduced GITHUB_TOKEN scope |
| 2026-02-03 | Added AppArmor profile              | Container isolation        |
| 2026-02-03 | Disabled host network access        | Network isolation          |

---

## Dependencies

Monitored via Dependabot:

- `huawei-solar` (2.5.0)
- `pymodbus` (3.11.4)
- `paho-mqtt` (2.1.0)

See [requirements.txt](huawei_solar_modbus_mqtt/requirements.txt) for full list.
