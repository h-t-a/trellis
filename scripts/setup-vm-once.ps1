<#
.SYNOPSIS
    Hardened one-time Windows host setup for Trellis MCP (trellis-mcp) ([REQ-TRL-24]).

.DESCRIPTION
    1. Copies trellis-mcp.pyz into $InstallDir (explicit -PyzSourcePath or local .\dist\trellis-mcp.pyz).
    2. Checks whether TCP $Port is free; exits cleanly on conflict without terminating any running service.
    3. Opens a scoped Windows Firewall inbound rule restricted to -AllowedRemoteAddress (defaults to loopback).
    4. Initializes hashed API keys (admin + optional read-only member key for team-alpha).
    5. Registers a least-privilege Windows Scheduled Task (never SYSTEM / Highest) serving loopback or TLS HTTPS.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$InstallDir = "C:\Trellis",

    [Parameter(Mandatory = $false)]
    [string]$BindHost = "127.0.0.1",

    [Parameter(Mandatory = $false)]
    [int]$Port = 8443,

    [Parameter(Mandatory = $false)]
    [string]$PyzSourcePath = "",

    [Parameter(Mandatory = $false)]
    [string]$TlsCert = "",

    [Parameter(Mandatory = $false)]
    [string]$TlsKey = "",

    [Parameter(Mandatory = $false)]
    [string]$PublicUrl = "",

    [Parameter(Mandatory = $false)]
    [string]$AllowedRemoteAddress = "127.0.0.1",

    [Parameter(Mandatory = $false)]
    [string]$ServiceAccount = "NT AUTHORITY\LocalService",

    [Parameter(Mandatory = $false)]
    [string]$InitialTeamLabel = "team-alpha"
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($PyzSourcePath)) {
    $Candidates = @(
        (Join-Path $PSScriptRoot "..\dist\trellis-mcp.pyz"),
        ".\trellis-mcp.pyz"
    )
    foreach ($c in $Candidates) {
        if (Test-Path $c) {
            $PyzSourcePath = (Resolve-Path $c).Path
            break
        }
    }
}

$IsLoopback = $BindHost -in @("127.0.0.1", "localhost", "::1")
if (-not $IsLoopback -and ([string]::IsNullOrWhiteSpace($TlsCert) -or [string]::IsNullOrWhiteSpace($TlsKey))) {
    throw "Non-loopback bind ($BindHost) requires -TlsCert and -TlsKey (or keep -BindHost 127.0.0.1 behind a TLS reverse proxy)."
}

Write-Host "==> [1/5] Preparing $InstallDir..." -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
$TargetPyz = Join-Path $InstallDir "trellis-mcp.pyz"
$KeysFile = Join-Path $InstallDir ".trellis_keys.json"
$AuditLog = Join-Path $InstallDir ".trellis-audit.jsonl"

Stop-ScheduledTask -TaskName "TrellisMCP" -ErrorAction SilentlyContinue
if ((-not [string]::IsNullOrWhiteSpace($PyzSourcePath)) -and (Test-Path $PyzSourcePath)) {
    Copy-Item -Path $PyzSourcePath -Destination $TargetPyz -Force
    Write-Host "    Copied $PyzSourcePath -> $TargetPyz" -ForegroundColor Green
}
if (-not (Test-Path $TargetPyz)) {
    throw "trellis-mcp.pyz not found. Build it with 'python -m trellis_mcp --build-pyz dist/trellis-mcp.pyz' or pass -PyzSourcePath."
}

$ExistingConn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($null -ne $ExistingConn) {
    $Proc = Get-Process -Id $ExistingConn.OwningProcess -ErrorAction SilentlyContinue
    $ProcDesc = if ($null -ne $Proc) { "$($Proc.ProcessName) (PID $($Proc.Id))" } else { "PID $($ExistingConn.OwningProcess)" }
    throw "Port $Port is already in use by $ProcDesc. Choose another -Port or stop that service manually before retrying."
}

Write-Host "==> [2/5] Configuring Scoped Firewall Rule (TCP $Port, RemoteAddress=$AllowedRemoteAddress)..." -ForegroundColor Cyan
$RuleName = "Trellis MCP Server (TCP $Port)"
if (-not (Get-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName $RuleName -Direction Inbound -LocalPort $Port -Protocol TCP -RemoteAddress $AllowedRemoteAddress -Action Allow | Out-Null
}

Write-Host "==> [3/5] Initializing Hashed Key Store & Generating Admin + Member Keys..." -ForegroundColor Cyan
$PythonExe = (Get-Command python -ErrorAction Stop).Source
$AdminKeyJson = & $PythonExe $TargetPyz --generate-key admin --role admin --keys-file $KeysFile | Out-String
$TeamKeyJson  = & $PythonExe $TargetPyz --generate-key $InitialTeamLabel --role member --keys-file $KeysFile | Out-String

Write-Host "==> [4/5] Registering Least-Privilege Scheduled Task (Account: $ServiceAccount)..." -ForegroundColor Cyan
$ServerArgs = "`"$TargetPyz`" --serve-http --host $BindHost --port $Port --keys-file `"$KeysFile`" --audit-log `"$AuditLog`""
if (-not [string]::IsNullOrWhiteSpace($TlsCert) -and -not [string]::IsNullOrWhiteSpace($TlsKey)) {
    $ServerArgs += " --tls-cert `"$TlsCert`" --tls-key `"$TlsKey`""
}
if (-not [string]::IsNullOrWhiteSpace($PublicUrl)) {
    $ServerArgs += " --public-url `"$PublicUrl`""
}

$Action = New-ScheduledTaskAction -Execute $PythonExe -Argument $ServerArgs -WorkingDirectory $InstallDir
$Trigger = New-ScheduledTaskTrigger -AtStartup
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
$Principal = New-ScheduledTaskPrincipal -UserId $ServiceAccount -LogonType ServiceAccount -RunLevel Limited

Register-ScheduledTask -TaskName "TrellisMCP" -Action $Action -Trigger $Trigger `
    -Settings $Settings -Principal $Principal -Force | Out-Null
Start-ScheduledTask -TaskName "TrellisMCP"

Start-Sleep -Seconds 2
$Scheme = if (-not [string]::IsNullOrWhiteSpace($TlsCert)) { "https" } else { "http" }
$HealthUrl = "${Scheme}://127.0.0.1:${Port}/healthz"
Write-Host "==> [5/5] Verifying Local Health Probe ($HealthUrl)..." -ForegroundColor Cyan
$Health = Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 10
Write-Host "    Health Status: $($Health | ConvertTo-Json -Compress)" -ForegroundColor Green

Write-Host "`n==================================================================" -ForegroundColor Green
Write-Host "  TRELLIS MCP SERVER DEPLOYED ($BindHost`:$Port)" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green
Write-Host "1. Administrator Key (Store securely in a secret manager):" -ForegroundColor Yellow
Write-Host $AdminKeyJson
Write-Host "2. Initial Read-Only Member Key ($InitialTeamLabel):" -ForegroundColor Yellow
Write-Host $TeamKeyJson
