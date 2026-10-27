$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    py -3 -m venv .venv
    if ($LASTEXITCODE) { throw 'venv failed' }
    & ./.venv/Scripts/python.exe -m pip install -r requirements.txt
    if ($LASTEXITCODE) { throw 'pip failed' }
    & ./.venv/Scripts/python.exe -m PyInstaller --noconfirm --onedir --console --name battery-reader --collect-all hid --distpath build/reader-dist --workpath build/reader-build --specpath build devices.py
    if ($LASTEXITCODE) { throw 'reader build failed' }
    Push-Location desktop
    try {
        npm.cmd ci
        if ($LASTEXITCODE) { throw 'npm ci failed' }
        npm.cmd run dist
        if ($LASTEXITCODE) { throw 'Electron build failed' }
    } finally { Pop-Location }
} finally { Pop-Location }
