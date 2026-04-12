# setup-dev.ps1
# Run from the project root: .\setup-dev.ps1
# Installs the shared package first, then both service requirements.

$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "==> Installing shared package..."
pip install -e "$root\shared"

Write-Host "==> Installing django-core requirements..."
pip install -r "$root\django-core\requirements.txt"

Write-Host "==> Installing fastapi-ingestion requirements..."
pip install -r "$root\fastapi-ingestion\requirements.txt"

Write-Host "==> Installing fastapi-ingestion test requirements..."
pip install -r "$root\fastapi-ingestion\tests\requirements-test.txt"

Write-Host "Done. Run 'python manage.py migrate' from django-core\ next."
