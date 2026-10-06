[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path
$pilot=Join-Path $repo 'benchmark\local\trellis-original-pilot-v1'
$environment=Join-Path $pilot 'venv'
if(Test-Path -LiteralPath $environment){throw 'Preserve the existing isolated environment; inspect its installation record before retrying.'}
New-Item -ItemType Directory -Force $pilot|Out-Null
& 'C:\Python310\python.exe' -m venv $environment
if($LASTEXITCODE -ne 0){throw 'Isolated Python environment creation failed.'}
$python=Join-Path $environment 'Scripts\python.exe'
$env:PYTHONNOUSERSITE='1'
$env:PIP_DISABLE_PIP_VERSION_CHECK='1'
& $python -m pip install --only-binary=:all: 'pip==25.2' 'setuptools==75.6.0' 'wheel==0.45.1'
if($LASTEXITCODE -ne 0){throw 'Packaging dependency installation failed.'}
& $python -m pip install --only-binary=:all: 'torch==2.4.0+cu121' 'torchvision==0.19.0+cu121' 'xformers==0.0.27.post2' --index-url 'https://download.pytorch.org/whl/cu121'
if($LASTEXITCODE -ne 0){throw 'Matching Torch/vision/xformers installation failed.'}
& $python -m pip install --only-binary=:all: -r (Join-Path $PSScriptRoot 'requirements.txt')
if($LASTEXITCODE -ne 0){throw 'Pilot inference dependency installation failed.'}
& $python -m pip check
if($LASTEXITCODE -ne 0){throw 'Installed dependency consistency check failed.'}
& $python -m pip freeze | Set-Content -Encoding UTF8 (Join-Path $pilot 'installed-requirements.txt')
if($LASTEXITCODE -ne 0){throw 'Installed version manifest failed.'}
[ordered]@{status='Actual isolated environment installed; GPU/model/inference not yet tested';createdUtc=[DateTime]::UtcNow.ToString('o');python=$python;priorEnvironmentChanged=$false;modelWeightsDownloaded=$false;inferenceRan=$false}|ConvertTo-Json|Set-Content -Encoding UTF8 (Join-Path $pilot 'environment.json')
Write-Output 'TRELLIS_ORIGINAL_ENVIRONMENT_PREPARED'
