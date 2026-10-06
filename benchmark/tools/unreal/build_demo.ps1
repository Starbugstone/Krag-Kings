[CmdletBinding()]
param(
    [ValidateSet('Detect','BuildEditor','Probe','Import','Package','Launch','All')][string]$Stage='All',
    [string]$EngineRoot='',
    [switch]$Smoke,
    [switch]$InputProbe,
    [switch]$Perf,
    [switch]$PerfMoving,
    [switch]$Showcase,
    [switch]$ShowcaseWait
)
$ErrorActionPreference='Stop'
if($Perf -and $PerfMoving){throw 'Idle and moving performance passes must be separate launches.'}
if(($Perf -or $PerfMoving) -and ($Smoke -or $InputProbe)){throw 'Performance passes must run separately from smoke/input verification.'}
if($Showcase -and ($Perf -or $PerfMoving -or $Smoke -or $InputProbe)){throw 'Showcase recording must run separately from performance/smoke/input verification.'}
if($ShowcaseWait -and -not $Showcase){throw '-ShowcaseWait requires -Showcase.'}
$BenchmarkRoot=(Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$ProjectRoot=Join-Path $BenchmarkRoot 'unreal\KragKingsBenchmark'
$Project=Join-Path $ProjectRoot 'KragKingsBenchmark.uproject'
$Evidence=Join-Path $BenchmarkRoot 'unreal\evidence'
$PackageRoot=Join-Path $BenchmarkRoot 'builds\unreal'
New-Item -ItemType Directory -Force -Path $Evidence | Out-Null
if(-not $EngineRoot){
    $Installed='C:\ProgramData\Epic\UnrealEngineLauncher\LauncherInstalled.dat'
    if(Test-Path $Installed){
        $Engines=(Get-Content $Installed -Raw|ConvertFrom-Json).InstallationList | Where-Object {$_.AppName -like 'UE_5.*'} | Sort-Object AppName -Descending
        foreach($Engine in $Engines){
            if(Test-Path (Join-Path $Engine.InstallLocation 'Engine\Binaries\Win64\UnrealEditor-Cmd.exe')){$EngineRoot=$Engine.InstallLocation;break}
        }
    }
    # New Epic launchers store completed installations in EOS v4 .egi records.
    # Do not accept an Incomplete download merely because an editor file exists.
    if(-not $EngineRoot){
        $EOSRecords='C:\ProgramData\Epic\EpicOnlineServicesShared\InstallHelper\InstalledItems'
        if(Test-Path $EOSRecords){
            foreach($RecordFile in Get-ChildItem $EOSRecords -Filter '*.egi'){
                $Record=(Get-Content $RecordFile.FullName -Raw|ConvertFrom-Json).v4
                if($Record.state -eq 'Installed' -and $Record.artifactId -like 'UE_5.*'){
                    $Candidate=$Record.dir.Replace('\\','\')
                    if(Test-Path (Join-Path $Candidate 'Engine\Binaries\Win64\UnrealEditor-Cmd.exe')){$EngineRoot=$Candidate;break}
                }
            }
        }
    }
}
if(-not $EngineRoot){throw 'No installed Unreal 5 editor found. Finish Epic Launcher installation, then rerun or pass -EngineRoot.'}
$Editor=Join-Path $EngineRoot 'Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$BuildBat=Join-Path $EngineRoot 'Engine\Build\BatchFiles\Build.bat'
$UAT=Join-Path $EngineRoot 'Engine\Build\BatchFiles\RunUAT.bat'
foreach($File in @($Project,$Editor,$BuildBat,$UAT)){if(-not(Test-Path $File)){throw "Required file not found: $File"}}
$EngineVersion=Get-Content (Join-Path $EngineRoot 'Engine\Build\Build.version') -Raw|ConvertFrom-Json
$Manifest=[ordered]@{engineRoot=$EngineRoot;engineVersion="$($EngineVersion.MajorVersion).$($EngineVersion.MinorVersion).$($EngineVersion.PatchVersion)";project=$Project;stage=$Stage;startedUtc=[DateTime]::UtcNow.ToString('o')}
$Manifest|ConvertTo-Json|Set-Content (Join-Path $Evidence 'last-build-attempt.json') -Encoding UTF8
Write-Output ($Manifest|ConvertTo-Json)
if($Stage -eq 'Detect'){exit 0}
function Clear-CompletionLogs([string[]]$Paths){
    $history=Join-Path $BenchmarkRoot 'local\completion-log-history'
    foreach($path in $Paths){
        if(Test-Path $path){
            New-Item -ItemType Directory -Force $history|Out-Null
            $name=[IO.Path]::GetFileNameWithoutExtension($path)+'-'+[DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fffffff')+[IO.Path]::GetExtension($path)
            Copy-Item -LiteralPath $path -Destination (Join-Path $history $name)
            Remove-Item -LiteralPath $path
        }
    }
}
# Per-project compile limit preserves memory after the machine's earlier crash.
$UBTConfigDir=Join-Path $ProjectRoot 'Saved\UnrealBuildTool'
New-Item -ItemType Directory -Force -Path $UBTConfigDir | Out-Null
Copy-Item (Join-Path $PSScriptRoot 'BuildConfiguration.xml') (Join-Path $UBTConfigDir 'BuildConfiguration.xml') -Force
# Association follows the actual selected engine, not a guessed install path.
$Descriptor=Get-Content $Project -Raw|ConvertFrom-Json
$Association="$($EngineVersion.MajorVersion).$($EngineVersion.MinorVersion)"
if($Descriptor.EngineAssociation -ne $Association){
    $Descriptor.EngineAssociation=$Association
    $Descriptor|ConvertTo-Json -Depth 8|Set-Content $Project -Encoding UTF8
}
if($Stage -in @('BuildEditor','All')){
    & $BuildBat KragKingsBenchmarkEditor Win64 Development "-Project=$Project" -WaitMutex -NoHotReloadFromIDE 2>&1 | Tee-Object -FilePath (Join-Path $Evidence 'build-editor.log')
    if($LASTEXITCODE -ne 0){throw "Unreal editor module build failed: $LASTEXITCODE"}
}
if($Stage -eq 'Probe'){
    $ProbeScript=Join-Path $PSScriptRoot 'editor_probe.py'
    $Log=Join-Path $Evidence 'editor-probe.log'
    $ConsoleLog=Join-Path $Evidence 'editor-probe-console.log'
    Clear-CompletionLogs @($Log,$ConsoleLog)
    & $Editor $Project "-ExecutePythonScript=$ProbeScript" -NullRHI -unattended -nosplash -stdout -FullStdOutLogOutput "-abslog=$Log" -NoSound 2>&1 | Tee-Object -FilePath $ConsoleLog
    if($LASTEXITCODE -ne 0){throw "Unreal editor probe failed: $LASTEXITCODE"}
    $Logs=@($Log,$ConsoleLog)|Where-Object {Test-Path $_}
    if(-not(Select-String -Path $Logs -Pattern 'KK_EDITOR_PROBE_COMPLETE' | Select-Object -First 1)){throw 'Editor probe returned without completion marker.'}
}
if($Stage -in @('Import','All')){
    # The coordinator guards each fresh native editor separately. An outer guard
    # around Stage Import would conflict with its deliberate per-process mutex.
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'Invoke-IsolatedImport.ps1') -EngineRoot $EngineRoot
    if($LASTEXITCODE -ne 0){throw "Isolated Unreal shared asset import failed: $LASTEXITCODE"}
}
if($Stage -in @('Package','All')){
    & $UAT BuildCookRun "-project=$Project" -nop4 -unattended -platform=Win64 -clientconfig=Development -build -cook -stage -pak -archive "-archivedirectory=$PackageRoot" -utf8output 2>&1 | Tee-Object -FilePath (Join-Path $Evidence 'package.log')
    if($LASTEXITCODE -ne 0){throw "Unreal Windows package failed: $LASTEXITCODE"}
}
if($Stage -eq 'Launch'){
    # Own the real game process so the memory guard remains held through the sample.
    $Game=Join-Path $PackageRoot 'Windows\KragKingsBenchmark\Binaries\Win64\KragKingsBenchmark.exe'
    if(-not(Test-Path $Game)){throw "Packaged game not found: $Game"}
    & (Join-Path $PSScriptRoot '..\Write-RunConditions.ps1') -OutputPath (Join-Path $Evidence 'run-conditions.json')
    $Arguments=@('-ResX=1920','-ResY=1080','-NoVSync',"-abslog=$(Join-Path $Evidence 'runtime.log')")
    if($Smoke){$Arguments+='-KKSmoke'}
    if($InputProbe){$Arguments+='-KKInputState'}
    if($Perf){$Arguments+='-KKPerf'}
    if($PerfMoving){$Arguments+='-KKPerfMoving'}
    if($Showcase){$Arguments+='-KKShowcase'}
    if($ShowcaseWait){
        $Gate=Join-Path $Evidence 'showcase-start.flag'
        if(Test-Path $Gate){Remove-Item $Gate}
        $Arguments+=@('-KKShowcaseWait',"-KKShowcaseGate=$Gate")
    }
    $Process=Start-Process -FilePath $Game -ArgumentList $Arguments -WorkingDirectory (Split-Path $Game) -PassThru
    $null=$Process.Handle
    Write-Output ('KK_GAME_PROCESS pid='+$Process.Id)
    if($Perf -or $PerfMoving -or $Smoke -or $Showcase){$Process.WaitForExit();exit $Process.ExitCode}
}
