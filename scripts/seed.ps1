# Seed demo user + Reading/Listening content. API container must already be running.
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

docker compose exec -T api python -m app.seed
docker compose exec -T api python -m app.seed_content
