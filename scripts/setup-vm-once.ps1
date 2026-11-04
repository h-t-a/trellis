<#
.SYNOPSIS
    One-time bootstrap script executed on the Windows VM via RDP shared drive (\\tsclient\D).

.DESCRIPTION
    1. Creates C:\Trellis and copies trellis-mcp.pyz from \\tsclient\D\...\dist\trellis-mcp.pyz (or local path).
    2. Checks if TCP Port 8080 is already in use (e.g. by Apache Tomcat) and either stops the conflicting service
       (when -TakeOverPort is set) or binds the specified -Port.
    3. Opens Windows Firewall for TCP Port $Port and enables WinRM (TCP Port 5985) from any IP so future deployments
       run 100% directly from your local machine's terminal without RDP.
    4. Auto-generates your Administrator API Key (`trl_admin_...`) and initial Team Member Key (`trl_team_ibanking_...`).
    5. Registers and starts the `TrellisMCP` background Windows Scheduled Task (AtStartup as SYSTEM) and verifies /healthz.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$InstallDir = "C:\Trellis",

    [Parameter(Mandatory = $false)]
    [int]$Port = 8080,

    [Parameter(Mandatory = $false)]
    [string]$PyzSourcePath = "",

    [Parameter(Mandatory = $false)]
    [switch]$TakeOverPort
)

$ErrorActionPreference = "Stop"

# Auto-detect trellis-mcp.pyz from RDP mapped drive (\\tsclient\D) or current folder
if ([string]::IsNullOrWhiteSpace($PyzSourcePath)) {
    $Candidates = @(
        "\\tsclient\D\hta\M.C.Sc_Repo\trellis\dist\trellis-mcp.pyz",
        (Join-Path $PSScriptRoot "..\dist\trellis-mcp.pyz"),
        ".\trellis-mcp.pyz"
    )
    foreach ($c in $Candidates) {
        if (Test-Path $c) {
            $PyzSourcePath = $c
            break
        }
    }
}

Write-Host "==> [1/5] Preparing $InstallDir..." -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
$TargetPyz = Join-Path $InstallDir "trellis-mcp.pyz"
$KeysFile = Join-Path $InstallDir ".trellis_keys.json"

Stop-ScheduledTask -TaskName "TrellisMCP" -ErrorAction SilentlyContinue
if ((-not [string]::IsNullOrWhiteSpace($PyzSourcePath)) -and (Test-Path $PyzSourcePath)) {
    Copy-Item -Path $PyzSourcePath -Destination $TargetPyz -Force
    Write-Host "    Copied $PyzSourcePath -> $TargetPyz" -ForegroundColor Green
}
if (-not (Test-Path $TargetPyz)) {
    throw "trellis-mcp.pyz not found. Make sure RDP drive redirection (\\tsclient\D) is enabled or pass -PyzSourcePath."
}

# Check if another process (e.g., Apache Tomcat) is currently holding $Port
$ExistingConn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($null -ne $ExistingConn) {
    $Proc = Get-Process -Id $ExistingConn.OwningProcess -ErrorAction SilentlyContinue
    if ($null -ne $Proc -and $Proc.ProcessName -notmatch "python") {
        Write-Host "    [!] Port $Port is currently in use by process '$($Proc.ProcessName)' (PID $($Proc.Id))." -ForegroundColor Yellow
        if ($TakeOverPort) {
            Write-Host "    Stopping conflicting process/service on port $Port (-TakeOverPort)..." -ForegroundColor Yellow
            Stop-Process -Id $Proc.Id -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 2
        } else {
            $Port = 8081
            Write-Host "    Switching trellis-mcp to Port $Port (pass -TakeOverPort if you want to stop '$($Proc.ProcessName)' and use 8080)." -ForegroundColor Yellow
        }
    }
}

Write-Host "==> [2/5] Opening Firewall Port $Port and Enabling WinRM (Port 5985) for Direct Local Deploys..." -ForegroundColor Cyan
$RuleName = "Trellis MCP Server (TCP $Port)"
if (-not (Get-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName $RuleName -Direction Inbound -LocalPort $Port -Protocol TCP -Action Allow | Out-Null
}
Enable-PSRemoting -SkipNetworkProfileCheck -Force | Out-Null
if (-not (Get-NetFirewallRule -DisplayName "WinRM HTTP Remote Deploy (TCP 5985)" -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName "WinRM HTTP Remote Deploy (TCP 5985)" -Direction Inbound -LocalPort 5985 -Protocol TCP -Action Allow | Out-Null
}
Set-NetFirewallRule -Name "WINRM-HTTP-In-TCP", "WINRM-HTTP-In-TCP-NoScope" -RemoteAddress Any -Action Allow -ErrorAction SilentlyContinue

Write-Host "==> [3/5] Initializing Key Store & Generating Administrator + Team Keys..." -ForegroundColor Cyan
$PythonExe = (Get-Command python -ErrorAction Stop).Source
$AdminKeyJson = & $PythonExe $TargetPyz --generate-key admin --role admin --keys-file $KeysFile | Out-String
$TeamKeyJson  = & $PythonExe $TargetPyz --generate-key team-ibanking --role member --keys-file $KeysFile | Out-String

Write-Host "==> [4/5] Registering & Starting Background Windows Scheduled Task (TrellisMCP on Port $Port)..." -ForegroundColor Cyan
$Action = New-ScheduledTaskAction -Execute $PythonExe `
    -Argument "`"$TargetPyz`" --serve-http --auto-generate-key --host 0.0.0.0 --port $Port --keys-file `"$KeysFile`"" `
    -WorkingDirectory $InstallDir
$Trigger = New-ScheduledTaskTrigger -AtStartup
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask -TaskName "TrellisMCP" -Action $Action -Trigger $Trigger `
    -Settings $Settings -User "SYSTEM" -RunLevel Highest -Force | Out-Null
Start-ScheduledTask -TaskName "TrellisMCP"

Start-Sleep -Seconds 2
Write-Host "==> [5/5] Verifying Local Health Probe (http://127.0.0.1:${Port}/healthz)..." -ForegroundColor Cyan
$Health = Invoke-RestMethod -Uri "http://127.0.0.1:${Port}/healthz" -TimeoutSec 10
Write-Host "    Health Status: $($Health | ConvertTo-Json -Compress)" -ForegroundColor Green

Write-Host "`n==================================================================" -ForegroundColor Green
Write-Host "  TRELLIS MCP SERVER DEPLOYED ON WINDOWS VM (PORT $Port)" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green
Write-Host "1. Administrator Key (Keep secret; used for /admin/keys & /admin/deploy):" -ForegroundColor Yellow
Write-Host $AdminKeyJson
Write-Host "2. Initial Team Member Key (Share with team-ibanking):" -ForegroundColor Yellow
Write-Host $TeamKeyJson
