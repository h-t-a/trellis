<#
.SYNOPSIS
    Automated Test -> Build Single-File .pyz -> Deploy to Windows VM pipeline for trellis-mcp ([REQ-MCP-09]).

.DESCRIPTION
    1. Runs the Trellis workspace doctor check (`python -m trellis_mcp --check`).
    2. Runs the full unit & HTTP integration test suite (`python -m unittest tests/test_trellis_mcp.py -v`).
    3. Builds the standalone 1-file bundle (`dist\trellis-mcp.pyz`, ~71 KB containing all 34 code/standard/skill files).
    4. Smoke-tests `dist\trellis-mcp.pyz --version`.
    5. Deploys `dist\trellis-mcp.pyz` to the Windows VM (`-VmHost`):
       - Mode A: HTTP Hot-Deploy via `POST /admin/deploy` when `-ApiKey` or `$env:TRELLIS_API_KEY` is provided.
       - Mode B: Direct WinRM (`New-PSSession`, auto-adds `$VmHost` to `TrustedHosts`).
       - Mode C (Fallback if VM WinRM 5985 is still closed by firewall): Automatically generates `dist\trellis-vm.rdp`
         with local drive `D:` mounted as `\\tsclient\D`, copies the 1-line bootstrap command to your Clipboard,
         and launches `mstsc.exe` so no manual file copy is ever needed!
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$VmHost = "",

    [Parameter(Mandatory = $false)]
    [string]$VmUser = "Administrator",

    [Parameter(Mandatory = $false)]
    [string]$RemoteDir = "C:\Trellis",

    [Parameter(Mandatory = $false)]
    [int]$Port = 8080,

    [Parameter(Mandatory = $false)]
    [string]$ApiKey = "",

    [Parameter(Mandatory = $false)]
    [PSCredential]$Credential = $null
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $RepoRoot

try {
    Write-Host "==> [Step 1/5] Running Trellis Workspace Doctor..." -ForegroundColor Cyan
    python -m trellis_mcp --check
    if ($LASTEXITCODE -ne 0) {
        throw "Workspace doctor check failed. Fix reported issues before building."
    }

    Write-Host "`n==> [Step 2/5] Running Automated Unit & Integration Tests ([REQ-MCP-01..09])..." -ForegroundColor Cyan
    python -m unittest tests/test_trellis_mcp.py -v
    if ($LASTEXITCODE -ne 0) {
        throw "Automated tests failed. Aborting build and deployment."
    }

    Write-Host "`n==> [Step 3/5] Building Standalone Single-File Bundle (dist\trellis-mcp.pyz)..." -ForegroundColor Cyan
    $PyzPath = Join-Path $RepoRoot "dist\trellis-mcp.pyz"
    python -m trellis_mcp --build-pyz $PyzPath
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $PyzPath)) {
        throw "Failed to build $PyzPath."
    }

    Write-Host "`n==> [Step 4/5] Smoke-Testing Standalone Bundle..." -ForegroundColor Cyan
    $VersionOut = python $PyzPath --version
    Write-Host "    Verified artifact: $VersionOut ($PyzPath)" -ForegroundColor Green

    if ([string]::IsNullOrWhiteSpace($VmHost)) {
        Write-Host "`n==> [Step 5/5] Local build complete (no -VmHost provided)." -ForegroundColor Green
        Write-Host "    Artifact ready at: $PyzPath"
        Write-Host "    To deploy to your Windows VM:"
        Write-Host "      Option A (HTTP Hot-Deploy): .\scripts\build-and-deploy.ps1 -VmHost <vm-ip> -ApiKey `"<ADMIN_KEY>`""
        Write-Host "      Option B (WinRM / RDP):     .\scripts\build-and-deploy.ps1 -VmHost <vm-ip> -VmUser `"$VmUser`""
        return
    }

    $ResolvedKey = if (-not [string]::IsNullOrWhiteSpace($ApiKey)) { $ApiKey.Trim() } elseif ($env:TRELLIS_API_KEY) { $env:TRELLIS_API_KEY.Trim() } else { "" }

    # Mode A: Zero-WinRM HTTP Hot-Deploy via POST /admin/deploy
    if (-not [string]::IsNullOrWhiteSpace($ResolvedKey)) {
        Write-Host "`n==> [Step 5/5] Deploying $PyzPath to http://${VmHost}:${Port}/admin/deploy via Admin Bearer Key..." -ForegroundColor Cyan
        $Headers = @{ Authorization = "Bearer $ResolvedKey" }
        $DeployResp = Invoke-RestMethod -Uri "http://${VmHost}:${Port}/admin/deploy" `
            -Method Post -InFile $PyzPath -ContentType "application/octet-stream" `
            -Headers $Headers -TimeoutSec 20
        Write-Host "    HTTP Hot-Deploy Result: $($DeployResp | ConvertTo-Json -Compress)" -ForegroundColor Green
        return
    }

    # Mode B: WinRM PowerShell Remoting Deploy
    Write-Host "`n==> [Step 5/5] Deploying $PyzPath to Windows VM ($VmHost)..." -ForegroundColor Cyan

    # Fast TCP probe on WinRM port 5985 before prompting for TrustedHosts/Credentials
    $WinRmReachable = $false
    $Tcp = New-Object System.Net.Sockets.TcpClient
    try {
        $Async = $Tcp.BeginConnect($VmHost, 5985, $null, $null)
        if ($Async.AsyncWaitHandle.WaitOne(2500, $false) -and $Tcp.Connected) {
            $Stream = $Tcp.GetStream()
            $Stream.ReadTimeout = 2000
            $ProbeBytes = [System.Text.Encoding]::ASCII.GetBytes("POST /wsman HTTP/1.1`r`nHost: ${VmHost}:5985`r`nContent-Length: 0`r`n`r`n")
            $Stream.Write($ProbeBytes, 0, $ProbeBytes.Length)
            $Buf = New-Object byte[] 16
            $Read = $Stream.Read($Buf, 0, 16)
            if ($Read -gt 0) { $WinRmReachable = $true }
        }
    } catch {
        $WinRmReachable = $false
    } finally {
        $Tcp.Close()
    }

    if (-not $WinRmReachable) {
        Write-Host "    [!] WinRM Port 5985 on $VmHost is currently closed by the VM firewall (only RDP 3389 is open)." -ForegroundColor Yellow
        Write-Host "    ==> Launching Automated RDP Drive-Mount Bootstrap to enable WinRM & deploy $PyzPath..." -ForegroundColor Cyan

        $RdpFile = Join-Path $RepoRoot "dist\trellis-vm.rdp"
        $RdpContent = @"
full address:s:${VmHost}:3389
username:s:${VmUser}
prompt for credentials:i:1
drivestoredirect:s:*
redirectclipboard:i:1
autoreconnection enabled:i:1
"@
        Set-Content -Path $RdpFile -Value $RdpContent -Encoding ASCII

        $BootstrapCmd = "powershell -ExecutionPolicy Bypass -File `"\\tsclient\D\hta\M.C.Sc_Repo\trellis\scripts\setup-vm-once.ps1`" -TakeOverPort"
        Set-Clipboard -Value $BootstrapCmd

        Write-Host "`n    1. Created RDP profile with Local Drive D: mounted as \\tsclient\D ($RdpFile)" -ForegroundColor Green
        Write-Host "    2. Copied the 1-line VM bootstrap command to your Clipboard:" -ForegroundColor Green
        Write-Host "       $BootstrapCmd" -ForegroundColor Yellow
        Write-Host "    3. Opening Remote Desktop (mstsc.exe) now - inside the VM, open PowerShell as Admin and press Ctrl+V!" -ForegroundColor Cyan
        Start-Process "mstsc.exe" -ArgumentList "`"$RdpFile`""
        return
    }

    # Ensure $VmHost is in WSMan TrustedHosts so New-PSSession by IP does not fail with ServerNotTrusted
    $CurrentTrusted = ""
    try {
        $CurrentTrusted = (Get-Item WSMan:\localhost\Client\TrustedHosts -ErrorAction Stop).Value
    } catch {
        $CurrentTrusted = ""
    }
    if ($CurrentTrusted -ne "*" -and ($CurrentTrusted -split "," | ForEach-Object { $_.Trim() }) -notcontains $VmHost) {
        Write-Host "    Adding $VmHost to local WinRM TrustedHosts (accept the UAC prompt if shown)..." -ForegroundColor Yellow
        $NewTrusted = if ([string]::IsNullOrWhiteSpace($CurrentTrusted)) { $VmHost } else { "$CurrentTrusted,$VmHost" }
        $AdminCmd = "Set-Item WSMan:\localhost\Client\TrustedHosts -Value '$NewTrusted' -Force"
        Start-Process powershell -Verb RunAs -ArgumentList "-NoProfile -Command $AdminCmd" -Wait
    }

    if ($null -eq $Credential) {
        $Credential = Get-Credential -UserName $VmUser -Message "Enter password for $VmUser on $VmHost"
    }

    $Session = New-PSSession -ComputerName $VmHost -Credential $Credential -ErrorAction Stop
    try {
        Invoke-Command -Session $Session -ScriptBlock {
            param($Dir)
            New-Item -ItemType Directory -Force -Path $Dir | Out-Null
            Stop-ScheduledTask -TaskName "TrellisMCP" -ErrorAction SilentlyContinue
        } -ArgumentList $RemoteDir

        $RemotePyz = "$RemoteDir\trellis-mcp.pyz"
        Copy-Item -Path $PyzPath -Destination $RemotePyz -ToSession $Session -Force

        Invoke-Command -Session $Session -ScriptBlock {
            param($Dir, $Pyz, $ListenPort)
            $KeysFile = "$Dir\.trellis_keys.json"
            $RuleName = "Trellis MCP Server (TCP $ListenPort)"
            if (-not (Get-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue)) {
                New-NetFirewallRule -DisplayName $RuleName -Direction Inbound -LocalPort $ListenPort -Protocol TCP -Action Allow | Out-Null
            }

            $PythonExe = (Get-Command python -ErrorAction Stop).Source
            $Action = New-ScheduledTaskAction -Execute $PythonExe `
                -Argument "`"$Pyz`" --serve-http --auto-generate-key --host 0.0.0.0 --port $ListenPort --keys-file `"$KeysFile`"" `
                -WorkingDirectory $Dir
            $Trigger = New-ScheduledTaskTrigger -AtStartup
            $Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
                -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

            Register-ScheduledTask -TaskName "TrellisMCP" -Action $Action -Trigger $Trigger `
                -Settings $Settings -User "SYSTEM" -RunLevel Highest -Force | Out-Null
            Start-ScheduledTask -TaskName "TrellisMCP"
        } -ArgumentList $RemoteDir, $RemotePyz, $Port

        Start-Sleep -Seconds 2
        $Health = Invoke-RestMethod -Uri "http://${VmHost}:${Port}/healthz" -TimeoutSec 10
        Write-Host "    VM Health Check: $($Health | ConvertTo-Json -Compress)" -ForegroundColor Green
    } finally {
        Remove-PSSession -Session $Session -ErrorAction SilentlyContinue
    }
} finally {
    Pop-Location
}
