[CmdletBinding()]
param([string]$VcVars='D:\DevTools\VS2022BuildTools\VC\Auxiliary\Build\vcvars64.bat')
$ErrorActionPreference='Stop'
if(-not(Test-Path $VcVars)){throw "MSVC environment script missing: $VcVars"}
$repo=(Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$out=Join-Path $repo 'benchmark\local\capture\native'
New-Item -ItemType Directory -Force $out|Out-Null
$source=Join-Path $PSScriptRoot 'native\WindowCapture.cpp'
$exe=Join-Path $out 'KragKingsWindowCapture.exe'
$build=Join-Path $out 'build.cmd'
@"
@echo off
call "$VcVars"
if errorlevel 1 exit /b 1
cd /d "$out"
cl /nologo /std:c++17 /EHsc /O2 /W4 /DUNICODE /D_UNICODE "$source" /Fe:"$exe" /link d3d11.lib dxgi.lib windowsapp.lib runtimeobject.lib user32.lib
exit /b %errorlevel%
"@|Set-Content $build -Encoding ASCII
& $env:ComSpec /d /c $build 2>&1|Tee-Object (Join-Path $out 'build.log')
if($LASTEXITCODE -ne 0){throw "Window capture helper build failed: $LASTEXITCODE"}
Write-Output $exe
