[CmdletBinding()]
param([string]$EngineRoot='D:\Games\UE_5.8',[string]$ProofPath='',[string]$PromotionPath='',[string[]]$Variants=@('Krag_Natural','Krag_Crusher','Krag_IronJaw','Krag_Piston'),[switch]$SkipAssembly)
$ErrorActionPreference='Stop'
$benchmark=(Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
if(-not $ProofPath){$ProofPath=Join-Path $benchmark 'art\krag\weapon-aim-payload-validation-v7.json'}
if(-not $PromotionPath){$PromotionPath=Join-Path $benchmark 'evidence\shared\20261006-krag-aim-repair-promotion.json'}
if(-not(Test-Path -LiteralPath $ProofPath)){throw 'Completed raw FBX patch proof is required.'}
if(-not(Test-Path -LiteralPath $PromotionPath)){throw 'Completed root promotion receipt is required.'}
$project=Join-Path $benchmark 'unreal\KragKingsBenchmark\KragKingsBenchmark.uproject'
$evidence=Join-Path $benchmark 'unreal\evidence'
$local=Join-Path $benchmark 'local\unreal-clip-refresh'
$guard=Join-Path $benchmark 'tools\Run-HeavyTask.ps1'
foreach($name in $Variants){
 if($name -notin @('Krag_Natural','Krag_Crusher','Krag_IronJaw','Krag_Piston')){throw "Unsupported clip-only variant: $name"}
 $stage='unreal-refresh-'+$name
 $attempt=Join-Path $local ($stage+'-'+[DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fffffff'))
 New-Item -ItemType Directory -Force $attempt|Out-Null
 foreach($file in @('refresh_shoot.py','import_shared_assets.py')){Copy-Item -LiteralPath (Join-Path $PSScriptRoot $file) -Destination (Join-Path $attempt $file)}
 Copy-Item -LiteralPath $ProofPath -Destination (Join-Path $attempt 'raw-patch-proof.json')
 Copy-Item -LiteralPath $PromotionPath -Destination (Join-Path $attempt 'promotion.json')
 $log=Join-Path $evidence ($stage+'.log')
 $spec=[ordered]@{
  name=$stage;executable=(Join-Path $EngineRoot 'Engine\Binaries\Win64\UnrealEditor-Cmd.exe')
  arguments=@($project,('-ExecutePythonScript='+(Join-Path $attempt 'refresh_shoot.py')),'-NullRHI','-corelimit=2','-unattended','-nosplash','-stdout','-FullStdOutLogOutput','-NoSound','-KKReuseMaterials',('-abslog='+$log),('-KKRefreshVariant='+$name),('-KKRefreshProof='+(Join-Path $attempt 'raw-patch-proof.json')),('-KKRefreshPromotion='+(Join-Path $attempt 'promotion.json')))
  workingDirectory=(Split-Path $benchmark);stdout=(Join-Path $evidence ($stage+'-stdout.log'));stderr=(Join-Path $evidence ($stage+'-stderr.log'))
  minAvailableGB=10;maxPrivateGB=9;successLog=$log;successMarker=('KK_SHOOT_REFRESH_COMPLETE '+$name)
 }
 $specPath=Join-Path $attempt 'job.json';$spec|ConvertTo-Json -Depth 6|Set-Content -LiteralPath $specPath -Encoding UTF8
 & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $guard -JobSpec $specPath
 if($LASTEXITCODE -ne 0){throw "Shoot-only refresh failed for $name (guard $LASTEXITCODE). No later stage was launched."}
}
if(-not $SkipAssembly){
 & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'Invoke-IsolatedImport.ps1') -EngineRoot $EngineRoot -AssembleOnly
 if($LASTEXITCODE -ne 0){throw 'Final assembly after Shoot-only refresh failed.'}
}
