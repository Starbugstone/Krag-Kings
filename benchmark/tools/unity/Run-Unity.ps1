param(
    [string]$Method = '',
    [string]$LogName = 'unity-build.log',
    [switch]$Interactive
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$project = Join-Path $repo 'benchmark\unity'
$logDir = Join-Path $repo 'benchmark\local\logs'
New-Item -ItemType Directory -Force $logDir | Out-Null
$running = Get-CimInstance Win32_Process -Filter "Name='Unity.exe'" | Where-Object { $_.CommandLine -and $_.CommandLine.Replace('/','\').Contains($project) }
if ($running) { throw 'The benchmark Unity project is already open. Reuse or close that instance before a batch build.' }
$editor = 'D:\Unity\Hub\6000.4.4f1\Editor\Unity.exe'
$arguments = @('-projectPath',('"'+$project+'"'),'-logFile',('"'+(Join-Path $logDir $LogName)+'"'),'-accept-apiupdate')
if (-not $Interactive) { $arguments += @('-batchmode','-quit','-nographics','-job-worker-count','2') }
if ($Method) { $arguments += @('-executeMethod',$Method) }
if (-not $Interactive) {
    # The shared wrapper handles quoting; retain raw paths in the JSON specification.
    $rawArguments=@($arguments | ForEach-Object { $_.Trim('"') })
    $specPath=Join-Path $repo 'benchmark\local\unity-job.json'
    @{name='unity-batch';executable=$editor;arguments=$rawArguments;workingDirectory=$project;minAvailableGB=10;maxPrivateGB=8} | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 $specPath
    & (Join-Path $PSScriptRoot '..\Run-HeavyTask.ps1') -JobSpec $specPath
    exit $LASTEXITCODE
}
$process = Start-Process -FilePath $editor -ArgumentList $arguments -PassThru
Write-Output ('Unity interactive process: '+$process.Id)
