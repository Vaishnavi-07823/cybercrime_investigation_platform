$ErrorActionPreference = "Continue"

function Test-Tool {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Command,
        [Parameter(Mandatory = $true)][bool]$Required
    )

    $available = Get-Command $Command -ErrorAction SilentlyContinue
    if ($available) {
        Write-Host "[OK] $Name" -ForegroundColor Green
        return $true
    }

    if ($Required) {
        Write-Host "[MISSING - REQUIRED] $Name" -ForegroundColor Red
    } else {
        Write-Host "[MISSING - OPTIONAL] $Name" -ForegroundColor Yellow
    }
    return $false
}

Write-Host "Cybercrime Investigation Platform prerequisite check`n" -ForegroundColor Cyan

$requiredOk = $true
$requiredOk = (Test-Tool "Windows Subsystem for Linux" "wsl.exe" $true) -and $requiredOk
$requiredOk = (Test-Tool "Docker CLI / Docker Desktop" "docker.exe" $true) -and $requiredOk
$requiredOk = (Test-Tool "Git for Windows" "git.exe" $true) -and $requiredOk

Test-Tool "Visual Studio Code" "code.cmd" $false | Out-Null
Test-Tool "Python" "python.exe" $false | Out-Null
Test-Tool "Node.js" "node.exe" $false | Out-Null

if (Get-Command docker.exe -ErrorAction SilentlyContinue) {
    try {
        docker info *> $null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] Docker engine is running" -ForegroundColor Green
        } else {
            Write-Host "[ERROR] Docker is installed, but the engine is not running" -ForegroundColor Red
            $requiredOk = $false
        }
    } catch {
        Write-Host "[ERROR] Docker engine check failed" -ForegroundColor Red
        $requiredOk = $false
    }

    try {
        docker compose version *> $null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] Docker Compose plugin" -ForegroundColor Green
        } else {
            Write-Host "[MISSING - REQUIRED] Docker Compose plugin" -ForegroundColor Red
            $requiredOk = $false
        }
    } catch {
        Write-Host "[MISSING - REQUIRED] Docker Compose plugin" -ForegroundColor Red
        $requiredOk = $false
    }
}

$ports = 5173, 5432, 6379, 7474, 7687, 8000, 9000, 9001, 9200, 9600
Write-Host "`nPort availability:" -ForegroundColor Cyan
foreach ($port in $ports) {
    $listener = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($listener) {
        Write-Host "[IN USE] Port $port" -ForegroundColor Yellow
    } else {
        Write-Host "[FREE] Port $port" -ForegroundColor Green
    }
}

if ($requiredOk) {
    Write-Host "`nRequired prerequisites are available." -ForegroundColor Green
    exit 0
}

Write-Host "`nOne or more required prerequisites are missing." -ForegroundColor Red
exit 1
