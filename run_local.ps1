# run_local.ps1 - Local development runner (PowerShell)

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "🚀 Huawei Solar MQTT - Local Development" -ForegroundColor Green
Write-Host "========================================================================" -ForegroundColor Cyan

# Load .env (besseres Parsing)
if (Test-Path .env) {
    Write-Host "📄 Loading .env" -ForegroundColor Blue
    Get-Content .env | ForEach-Object {
        $line = $_.Trim()
        # Skip comments and empty lines
        if ($line -and !$line.StartsWith('#')) {
            if ($line -match '^([^=]+)=(.*)$') {
                $key = $matches[1].Trim()
                $value = $matches[2].Trim()
                Set-Item -Path "env:$key" -Value $value
                Write-Host "  $key = $value" -ForegroundColor DarkGray
            }
        }
    }
} else {
    Write-Host "❌ No .env file!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ">> System Info:" -ForegroundColor Blue

# Python version
$pythonVersion = python --version 2>&1 | Select-String -Pattern "Python (\d+\.\d+\.\d+)" | ForEach-Object { $_.Matches.Groups[1].Value }
Write-Host "   - Python: $pythonVersion" -ForegroundColor White

# Package versions
try {
    $huaweiVersion = pip show huawei-solar 2>$null | Select-String "^Version:" | ForEach-Object { $_.ToString().Split(":")[1].Trim() }
    if (!$huaweiVersion) { $huaweiVersion = "unknown" }
} catch { $huaweiVersion = "unknown" }

try {
    $pymodbusVersion = pip show pymodbus 2>$null | Select-String "^Version:" | ForEach-Object { $_.ToString().Split(":")[1].Trim() }
    if (!$pymodbusVersion) { $pymodbusVersion = "unknown" }
} catch { $pymodbusVersion = "unknown" }

try {
    $pahoVersion = pip show paho-mqtt 2>$null | Select-String "^Version:" | ForEach-Object { $_.ToString().Split(":")[1].Trim() }
    if (!$pahoVersion) { $pahoVersion = "unknown" }
} catch { $pahoVersion = "unknown" }

Write-Host "   - huawei-solar: $huaweiVersion" -ForegroundColor White
Write-Host "   - pymodbus: $pymodbusVersion" -ForegroundColor White
Write-Host "   - paho-mqtt: $pahoVersion" -ForegroundColor White

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ">> Configuration:" -ForegroundColor Blue
Write-Host "   🔌 Inverter: $env:HUAWEI_MODBUS_HOST`:$env:HUAWEI_MODBUS_PORT (Slave ID: $env:HUAWEI_SLAVE_ID)" -ForegroundColor White
Write-Host "   📡 MQTT:     $env:HUAWEI_MODBUS_MQTT_BROKER`:$env:HUAWEI_MODBUS_MQTT_PORT" -ForegroundColor White
Write-Host "   📍 Topic:    $env:HUAWEI_MODBUS_MQTT_TOPIC" -ForegroundColor White
Write-Host "   ⏱️  Poll:     $env:HUAWEI_POLL_INTERVAL`s | Timeout: $env:HUAWEI_STATUS_TIMEOUT`s" -ForegroundColor White
Write-Host "   📍 Log:      $env:HUAWEI_LOG_LEVEL" -ForegroundColor White
Write-Host "========================================================================" -ForegroundColor Cyan

# Check if MQTT broker is reachable
$mqttHost = $env:HUAWEI_MODBUS_MQTT_BROKER
$mqttPort = $env:HUAWEI_MODBUS_MQTT_PORT
try {
    $connection = Test-NetConnection -ComputerName $mqttHost -Port $mqttPort -WarningAction SilentlyContinue
    if (!$connection.TcpTestSucceeded) {
        Write-Host "⚠️  MQTT Broker not reachable at ${mqttHost}:${mqttPort}" -ForegroundColor Yellow
        Write-Host "   Make sure Mosquitto is running!" -ForegroundColor Yellow
    } else {
        Write-Host "✅ MQTT Broker reachable" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠️  Cannot test MQTT connection" -ForegroundColor Yellow
}

Write-Host ""
Write-Host ">> Starting Python application..." -ForegroundColor Blue
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""

# Run
Set-Location huawei-solar-modbus-mqtt
python -m modbus_energy_meter.main
