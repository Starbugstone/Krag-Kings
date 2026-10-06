$ErrorActionPreference='Stop'
$repo='D:\Dev\Krag-Kings'
$plan=Get-Content -Raw (Join-Path $PSScriptRoot 'plan.json')|ConvertFrom-Json
if(Test-Path (Join-Path $PSScriptRoot 'result.json')){throw 'Preserve the existing diagnostic build result.'}
foreach($file in $plan.sourceFiles.PSObject.Properties){
 if((Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $repo $file.Name)).Hash.ToLower() -ne $file.Value.sha256){throw ('Frozen source changed: '+$file.Name)}
}
$archive=Join-Path $repo $plan.archiveDirectory
New-Item -ItemType Directory -Force $archive|Out-Null
foreach($file in $plan.previousBuildFiles.PSObject.Properties){
 $source=Join-Path $repo $file.Name
 if((Get-FileHash -Algorithm SHA256 -LiteralPath $source).Hash.ToLower() -ne $file.Value.sha256){throw ('Previous package changed: '+$file.Name)}
 $relative=$file.Name.Substring('benchmark/builds/Unity/'.Length)
 $target=Join-Path $archive $relative
 New-Item -ItemType Directory -Force (Split-Path $target)|Out-Null
 if(-not(Test-Path $target)){Copy-Item -LiteralPath $source -Destination $target}
 if((Get-FileHash -Algorithm SHA256 -LiteralPath $target).Hash.ToLower() -ne $file.Value.sha256){throw ('Archive differs: '+$relative)}
}
$result=[ordered]@{scope=$plan.scope;startedUtc=[DateTime]::UtcNow.ToString('o');completed=$false;previousBuildGuid=$plan.previousBuildGuid;archiveVerifiedFiles=@($plan.previousBuildFiles.PSObject.Properties).Count;nativeWindowsInputSent=$false;artisticAcceptance=$false}
try {
 & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $repo 'benchmark\tools\Run-HeavyTask.ps1') -JobSpec (Join-Path $PSScriptRoot 'job.json') 2>&1|Tee-Object -FilePath (Join-Path $PSScriptRoot 'guard.log')
 $result.guardExitCode=$LASTEXITCODE
 if($LASTEXITCODE -ne 0){throw 'Diagnostic BuildPrepared failed; preserve all logs.'}
 $boot=Get-Content (Join-Path $repo 'benchmark\builds\Unity\KragKings-Unity_Data\boot.config')
 $result.buildGuid=($boot|Where-Object {$_ -like 'build-guid=*'}).Substring('build-guid='.Length)
 $result.gameplayAssemblySha256=(Get-FileHash -Algorithm SHA256 (Join-Path $repo 'benchmark\builds\Unity\KragKings-Unity_Data\Managed\Assembly-CSharp.dll')).Hash.ToLower()
 $result.completed=$true
} catch {$result.error=$_.Exception.Message;throw}
finally {
 $telemetry=Join-Path $repo 'benchmark\local\unity-native-event-diagnostics-build-memory.csv'
 if(Test-Path $telemetry){Copy-Item $telemetry (Join-Path $PSScriptRoot 'memory.csv')}
 $result.finishedUtc=[DateTime]::UtcNow.ToString('o')
 $result|ConvertTo-Json -Depth 6|Set-Content -Encoding UTF8 (Join-Path $PSScriptRoot 'result.json')
}
Write-Output 'UNITY_NATIVE_DIAGNOSTIC_BUILD_COMPLETE'
