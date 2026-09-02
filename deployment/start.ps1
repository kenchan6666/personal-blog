# One-command start for the portfolio stack (Windows PowerShell).
#   .\deployment\start.ps1          local: Redis + FastAPI + Next.js (Mongo if MONGO_URI is set)
#   .\deployment\start.ps1 --prod   single-VM compose (nginx :80)

function ShowUsage {
    Write-Host @"
Usage: .\deployment\start.ps1 [--prod] [--down]

  (default)  Start Redis, FastAPI, and Next.js. Mongo starts only if MONGO_URI is set.
  --prod     Build and start the nginx + containers stack on :80.
  --down     Stop the stack that matches the other flags (dev deps or prod).
"@
}

function RequireCmd([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "missing command: $Name"
    }
}

function EnsureProdEnv($Dir) {
    $envFile = Join-Path $Dir ".env"
    if (-not (Test-Path $envFile)) {
        Copy-Item (Join-Path $Dir "env.example") $envFile
        Write-Host "created $envFile from env.example -- edit secrets if you need SMTP or GitHub OAuth"
    }
}

function ComposeProd($Root, $Dir, [string[]]$ComposeArgs) {
    EnsureProdEnv $Dir
    $compose = Join-Path $Root "docker-compose.prod.yml"
    $envFile = Join-Path $Dir ".env"
    & docker compose -f $compose --env-file $envFile @ComposeArgs
    if ($LASTEXITCODE -ne 0) { throw "docker compose (prod) failed" }
}

function ComposeDeps($Root, [string[]]$ComposeArgs) {
    $compose = Join-Path $Root "docker-compose.yml"
    & docker compose -f $compose @ComposeArgs
    if ($LASTEXITCODE -ne 0) { throw "docker compose (deps) failed" }
}

function ReadDotEnvValue([string]$Path, [string]$Key) {
    if (-not (Test-Path $Path)) { return "" }
    foreach ($line in Get-Content -LiteralPath $Path) {
        if ($line -match "^\s*#") { continue }
        $escaped = [regex]::Escape($Key)
        if ($line -match "^\s*$escaped\s*=\s*(.*)$") {
            return $Matches[1].Trim().Trim('"').Trim("'")
        }
    }
    return ""
}

function VenvPython($Root) {
    $win = Join-Path $Root "backend\.venv\Scripts\python.exe"
    $nix = Join-Path $Root "backend\.venv\bin\python"
    if (Test-Path $win) { return $win }
    if (Test-Path $nix) { return $nix }
    return $null
}

function HostPython {
    foreach ($name in @("python", "python3")) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd) { return $cmd.Source }
    }
    throw "Python 3.12+ is required (python or python3)"
}

function WaitHttp([string]$Url, [int]$Tries = 60) {
    for ($i = 0; $i -lt $Tries; $i++) {
        try {
            Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2 | Out-Null
            return $true
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    return $false
}

function RunProdUp($Root, $Dir) {
    EnsureProdEnv $Dir
    $runtime = Join-Path $Dir "nginx-runtime"
    New-Item -ItemType Directory -Force -Path $runtime | Out-Null
    Copy-Item (Join-Path $Dir "nginx\http.conf") (Join-Path $runtime "default.conf") -Force

    Write-Host "starting production stack (nginx :80/:443)..."
    ComposeProd $Root $Dir @("up", "-d", "--build")
    if (WaitHttp "http://127.0.0.1/api/health" 45) {
        Write-Host "health: http://127.0.0.1/api/health"
        if (-not (IssueLetsEncrypt $Root $Dir)) {
            Write-Host "TLS skipped — site is on http until certbot succeeds (open GCP tcp:80 and tcp:443)."
        }
        Write-Host "ready: http://127.0.0.1/zh-Hant"
    } else {
        Write-Host "containers are up; health check timed out. logs:"
        ComposeProd $Root $Dir @("logs", "--tail", "40", "api", "web", "nginx")
    }
}

function HostFromOrigin([string]$Origin) {
    $hostName = $Origin.Trim()
    $hostName = $hostName -replace '^https?://', ''
    return $hostName.TrimEnd('/')
}

function IssueLetsEncrypt($Root, $Dir) {
    $envFile = Join-Path $Dir ".env"
    $origin = ReadDotEnvValue $envFile "PUBLIC_ORIGIN"
    $domain = HostFromOrigin $origin
    $email = ReadDotEnvValue $envFile "TLS_EMAIL"
    if (-not $email) { $email = ReadDotEnvValue $envFile "OWNER_EMAIL" }
    if (-not $domain -or $domain -eq "YOUR_PUBLIC_IP" -or $domain -match 'localhost' -or $domain -match '^\d+\.\d+\.\d+\.\d+$') {
        Write-Host "PUBLIC_ORIGIN=$origin is not a domain — skipping Let's Encrypt"
        return $false
    }
    if (-not $email) {
        Write-Host "TLS_EMAIL / OWNER_EMAIL empty — skipping Let's Encrypt"
        return $false
    }
    Write-Host "requesting Let's Encrypt cert for $domain ..."
    ComposeProd $Root $Dir @(
        "run", "--rm", "--no-deps", "--entrypoint", "certbot", "certbot", "certonly",
        "--webroot", "-w", "/var/www/certbot",
        "--cert-name", "site",
        "--agree-tos", "--non-interactive", "--keep-until-expiry",
        "--email", $email,
        "-d", $domain, "-d", "www.$domain"
    )
    if ($LASTEXITCODE -ne 0) {
        ComposeProd $Root $Dir @(
            "run", "--rm", "--no-deps", "--entrypoint", "certbot", "certbot", "certonly",
            "--webroot", "-w", "/var/www/certbot",
            "--cert-name", "site",
            "--agree-tos", "--non-interactive", "--keep-until-expiry",
            "--email", $email,
            "-d", $domain
        )
    }
    if ($LASTEXITCODE -ne 0) { return $false }
    Copy-Item (Join-Path $Dir "nginx\ssl.conf") (Join-Path $Dir "nginx-runtime\default.conf") -Force
    ComposeProd $Root $Dir @("exec", "-T", "nginx", "nginx", "-s", "reload")
    Write-Host "TLS ready: https://$domain"
    return $true
}

function RunProdDown($Root, $Dir) {
    ComposeProd $Root $Dir @("down")
    Write-Host "production stack stopped"
}

function RunDevUp($Root) {
    RequireCmd npm
    $backendEnv = Join-Path $Root "backend\.env"
    if (-not (Test-Path $backendEnv)) {
        Copy-Item (Join-Path $Root "backend\.env.example") $backendEnv
        Write-Host "created backend\.env from .env.example"
    }

    $mongoUri = $env:MONGO_URI
    if (-not $mongoUri) { $mongoUri = ReadDotEnvValue $backendEnv "MONGO_URI" }
    if ($mongoUri) {
        Write-Host "starting Mongo + Redis..."
        ComposeDeps $Root @("up", "-d")
    } else {
        Write-Host "MONGO_URI empty — starting Redis only; API stores data in backend\data\local"
        ComposeDeps $Root @("up", "-d", "redis")
    }

    $py = VenvPython $Root
    if (-not $py) {
        Write-Host "creating backend virtualenv..."
        & (HostPython) -m venv (Join-Path $Root "backend\.venv")
        $py = VenvPython $Root
        if (-not $py) { throw "failed to create backend\.venv" }
        & $py -m pip install -r (Join-Path $Root "backend\requirements.txt")
        if ($LASTEXITCODE -ne 0) { throw "pip install failed" }
    }

    $nodeModules = Join-Path $Root "frontend\node_modules"
    if (-not (Test-Path $nodeModules)) {
        Write-Host "installing frontend dependencies..."
        Push-Location (Join-Path $Root "frontend")
        try {
            npm install
            if ($LASTEXITCODE -ne 0) { throw "npm install failed" }
        } finally {
            Pop-Location
        }
    }

    Write-Host "API:  http://127.0.0.1:8000/api/health"
    Write-Host "site: http://127.0.0.1:3000/zh-Hant"
    Write-Host "Ctrl+C stops FastAPI and Next.js (Mongo/Redis keep running)."

    $api = Start-Process -FilePath $py -ArgumentList @(
        "-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"
    ) -WorkingDirectory (Join-Path $Root "backend") -NoNewWindow -PassThru

    $npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if (-not $npm) { $npm = Get-Command npm }
    $web = Start-Process -FilePath $npm.Source -ArgumentList @("run", "dev") `
        -WorkingDirectory (Join-Path $Root "frontend") -NoNewWindow -PassThru

    try {
        Wait-Process -Id @($api.Id, $web.Id)
    } finally {
        foreach ($proc in @($api, $web)) {
            if ($proc -and -not $proc.HasExited) {
                Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

function RunDevDown($Root) {
    ComposeDeps $Root @("stop")
    Write-Host "Mongo + Redis stopped (data volume kept)"
}

$ErrorActionPreference = "Stop"
$Dir = $PSScriptRoot
$Root = Split-Path -Parent $Dir
$Prod = $false
$Down = $false

foreach ($arg in $args) {
    switch -Regex ($arg) {
        "^(--prod|-Prod|-prod)$" { $Prod = $true }
        "^(--down|-Down|-down)$" { $Down = $true }
        "^(-h|--help|-Help)$" { ShowUsage; exit 0 }
        default { throw "unknown argument: $arg (try --help)" }
    }
}

if ($Prod -and $Down) { $Mode = "prod-down" }
elseif ($Prod) { $Mode = "prod" }
elseif ($Down) { $Mode = "dev-down" }
else { $Mode = "dev" }

RequireCmd docker
docker compose version | Out-Null
if ($LASTEXITCODE -ne 0) { throw "docker compose plugin is required" }

switch ($Mode) {
    "prod" { RunProdUp $Root $Dir }
    "prod-down" { RunProdDown $Root $Dir }
    "dev-down" { RunDevDown $Root }
    "dev" { RunDevUp $Root }
    default { throw "invalid mode: $Mode" }
}
