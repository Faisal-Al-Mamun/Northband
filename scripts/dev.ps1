# Copy .env if missing, then start the full Docker Compose stack.
# Usage: .\scripts\dev.ps1
#        .\scripts\dev.ps1 -d
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item -LiteralPath ".env.example" -Destination ".env"
    Write-Host "Created .env from .env.example — add an LLM key for real scoring (optional)."
}

Write-Host @"
Northband
  Studio   http://localhost:3000
  API      http://localhost:8000/docs
  Health   http://localhost:8000/health
  Login    demo@northband.app / demo12345

First API image build pulls torch/faster-whisper (several minutes, CPU only, no GPU).
After the API is up:  .\scripts\seed.ps1
"@

docker compose up --build @args
