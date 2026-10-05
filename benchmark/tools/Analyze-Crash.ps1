param([string]$DumpName='100526-21937-01.dmp')
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$local=Join-Path $repo 'benchmark\local\diagnostics'
$dump=Join-Path $local $DumpName
$debugger=Join-Path $local 'debugger\amd64\cdb.exe'
if(-not(Test-Path $dump)){throw 'Crash dump is not in the local diagnostics folder. Copy it with Windows administrator authorization first.'}
if(-not(Test-Path $debugger)){throw 'Microsoft debugger has not been extracted in local diagnostics.'}
$signature=Get-AuthenticodeSignature $debugger
if($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notlike '*Microsoft Corporation*'){throw 'Debugger signature validation failed.'}
$symbols=Join-Path $local 'symbols'
New-Item -ItemType Directory -Force $symbols | Out-Null
$log=Join-Path $local 'crash-analysis.txt'
& $debugger -z $dump -y ('srv*'+$symbols+'*https://msdl.microsoft.com/download/symbols') -logo $log -c '!analyze -v; !process 0 0; .bugcheck; q'
exit $LASTEXITCODE
