param([Parameter(Mandatory=$true)][string]$OutputPath)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Windows.Forms
$machine=Get-CimInstance Win32_ComputerSystem
$os=Get-CimInstance Win32_OperatingSystem
$cpu=Get-CimInstance Win32_Processor | Select-Object -First 1
$power=[System.Windows.Forms.SystemInformation]::PowerStatus
$gpuTool=Get-Command nvidia-smi.exe -ErrorAction SilentlyContinue
$gpu=if($gpuTool){@(& $gpuTool.Source --query-gpu=name,driver_version,memory.total --format=csv,noheader,nounits)}else{@('Unavailable')}
$data=[ordered]@{
    timestampUtc=[DateTime]::UtcNow.ToString('o')
    machineModel=$machine.Model
    cpu=$cpu.Name
    memoryGiB=[Math]::Round($machine.TotalPhysicalMemory/1GB,2)
    windowsVersion=$os.Version
    windowsBuild=$os.BuildNumber
    acLineStatus=$power.PowerLineStatus.ToString()
    batteryChargeFraction=$power.BatteryLifePercent
    windowsPowerScheme=(& powercfg.exe /getactivescheme | Out-String).Trim()
    gpuNameDriverMemoryMiB=$gpu
    vendorPerformanceMode='Not queried; no power or vendor settings changed by this tool'
}
New-Item -ItemType Directory -Force (Split-Path $OutputPath) | Out-Null
$data | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 $OutputPath
Write-Output ('RUN_CONDITIONS_SAVED '+$OutputPath)
