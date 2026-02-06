# Security Policy

## Supported Versions

We actively support the following versions with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.7.x   | :white_check_mark: |
| 1.6.x   | :x:                |
| < 1.6   | :x:                |

## Security Considerations

### Read-Only by Design

huABus is **intentionally read-only** to minimize security risks:

- ✅ No write access to inverter (prevents accidental or malicious configuration changes)
- ✅ No control commands (eliminates risk of hardware damage)
- ✅ Monitoring only (attack surface limited to data exposure)

### Network Security

**Modbus TCP Connection:**
- Unencrypted protocol (Modbus limitation)
- Runs on local network only
- **Recommendation:** Isolate inverter on dedicated VLAN

**MQTT Connection:**
- Supports authentication (username/password)
- Runs on local network (typically `core-mosquitto`)
- **Recommendation:** Use strong passwords, enable MQTT ACLs

### Data Exposure

**Published Data (via MQTT):**
- Solar production values
- Battery state of charge
- Grid consumption/export
- Inverter serial number and model

**Risk:** Information disclosure if MQTT broker is exposed to internet.

**Mitigation:**
- Never expose MQTT broker to public internet
- Use Home Assistant's internal MQTT broker (`core-mosquitto`)
- Enable MQTT authentication
- Configure firewall rules appropriately

### Home Assistant Add-on Security

**AppArmor Profile:**
- Included since v1.7.3
- Restricts file system access
- Limits network capabilities

**Ingress:**
- Disabled (no web UI = no web-based attacks)

**Host Network:**
- Not required (add-on uses Docker networking)

## Reporting a Vulnerability

If you discover a security vulnerability, please follow these steps:

### DO NOT open a public GitHub issue

Instead, please report security issues privately:

**Email:** arend.boehmer@web.de

**Subject:** `[SECURITY] huABus Vulnerability Report`

**Include:**
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### What to expect

- **Acknowledgment:** Within 48 hours
- **Initial assessment:** Within 7 days
- **Fix timeline:** Depends on severity
  - Critical: Immediate hotfix
  - High: Within 2 weeks
  - Medium/Low: Next regular release

### Disclosure Policy

We follow **coordinated disclosure**:

1. You report the issue privately
2. We confirm and develop a fix
3. We release the patched version
4. We publish a security advisory (with credit to reporter, if desired)
5. You may disclose publicly after 90 days or after patch release (whichever comes first)

## Security Best Practices

### Installation

✅ **DO:**
- Download only from official sources (GitHub releases, HA Add-on Store)
- Verify add-on signature (HA does this automatically)
- Review configuration before enabling

❌ **DON'T:**
- Install from untrusted third-party repositories
- Expose Modbus TCP port (502) to internet
- Use default/weak MQTT passwords

### Network Configuration

**Recommended Setup:**

```
Internet ──┬─ Firewall ─┬─ Home Network (VLAN 1)
           │            │   └─ Home Assistant
           │            │
           │            └─ IoT Network (VLAN 2)
           │                └─ Huawei Inverter (isolated)
           │
           └─ DMZ (no access to internal networks)
```

**Firewall Rules:**
- Home Assistant → Inverter: TCP/502 (Modbus)
- Block: Internet → Inverter
- Block: IoT VLAN → Home Network (except HA)

### Configuration Security

**Example secure config:**

```yaml
modbus_host: 192.168.2.100  # Isolated VLAN
modbus_port: 502
slave_id: 1
mqtt_broker: core-mosquitto  # Internal only
mqtt_port: 1883
mqtt_user: "huabus_readonly"  # Dedicated user
mqtt_password: "!SecurePassword123!"  # Strong password
log_level: INFO  # Don't log sensitive data in production
```

**Avoid:**
```yaml
mqtt_broker: mqtt.example.com  # ❌ External broker
mqtt_user: ""  # ❌ No authentication
log_level: TRACE  # ❌ May log sensitive data
```

## Known Limitations

### Modbus TCP

**Issue:** Unencrypted, unauthenticated protocol
**Risk:** Man-in-the-middle attacks on local network
**Mitigation:** Physical network security (VLAN isolation)

### MQTT

**Issue:** Username/password transmitted in plaintext (unless TLS)
**Risk:** Credential sniffing on local network
**Mitigation:** Use Home Assistant's internal broker, isolated network

### Single Modbus Connection

**Issue:** Only ONE Modbus connection allowed by Huawei inverters
**Risk:** Denial of service if malicious client connects
**Mitigation:** Network isolation, firewall rules

## Security Audits

No formal security audit has been conducted. Contributions welcome!

**Interested in auditing?** Please contact: arend.boehmer@web.de

## Updates and Patches

**Stay informed:**
- Watch this repository for security advisories
- Enable GitHub notifications for releases
- Subscribe to [GitHub Security Advisories](https://github.com/arboeh/huABus/security/advisories)

**Update process:**
1. Backup your Home Assistant configuration
2. Update add-on via Home Assistant UI
3. Review changelog for breaking changes
4. Test in non-production environment first (if possible)

## Third-Party Dependencies

We use these libraries (security maintained by upstream):

- `huawei-solar` (wlcrs/huawei-solar-lib)
- `pymodbus` (Modbus TCP client)
- `paho-mqtt` (MQTT client)

**Dependency updates:** Monitored via Dependabot (automated PRs)

## Questions?

Security-related questions that are **not vulnerabilities** can be asked:

- [GitHub Discussions](https://github.com/arboeh/huABus/discussions) (public)
- Email: arend.boehmer@web.de (private)

---

**Last updated:** February 6, 2026
