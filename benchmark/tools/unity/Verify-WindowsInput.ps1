param(
    [Parameter(Mandatory=$true)][int]$DemoProcessId,
    [Parameter(Mandatory=$true)][string]$EvidencePath
)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;using System.Runtime.InteropServices;
public static class DemoInput {
 [StructLayout(LayoutKind.Sequential)] public struct POINT { public int X,Y; }
 [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left,Top,Right,Bottom; }
 [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
 [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
 [DllImport("user32.dll")] public static extern bool ClientToScreen(IntPtr h,ref POINT p);
 [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h,out RECT r);
 [DllImport("user32.dll")] public static extern bool SetCursorPos(int x,int y);
 [DllImport("user32.dll")] public static extern void mouse_event(uint flags,uint x,uint y,uint data,UIntPtr extra);
 [DllImport("user32.dll")] public static extern void keybd_event(byte key,byte scan,uint flags,UIntPtr extra);
}
'@
$demo=Get-Process -Id $DemoProcessId
if($demo.ProcessName -ne 'KragKings-Unity') {throw 'Input verification only targets the packaged KragKings-Unity process.'}
$window=$demo.MainWindowHandle
if($window -eq [IntPtr]::Zero){throw 'Packaged demo has no visible window.'}
$probePath=Join-Path $EvidencePath 'input-probe.json'
function Read-Probe {
    for($attempt=0;$attempt -lt 5;$attempt++) {
        try {return Get-Content -Raw $probePath | ConvertFrom-Json} catch {Start-Sleep -Milliseconds 50}
    }
    throw 'Cannot read runtime input probe. Start the demo with -inputProbe -evidencePath <folder>.'
}
function Focus-Demo {
    [DemoInput]::SetForegroundWindow($window)|Out-Null
    Start-Sleep -Milliseconds 150
    if([DemoInput]::GetForegroundWindow() -ne $window){throw 'Demo did not receive focus; no input sent to another application.'}
}
function Click-World($ScreenPoint,[bool]$Right,[bool]$Walk=$false) {
    Focus-Demo
    $probe=Read-Probe
    $rect=New-Object DemoInput+RECT
    [DemoInput]::GetClientRect($window,[ref]$rect)|Out-Null
    $point=New-Object DemoInput+POINT
    $point.X=[int]($ScreenPoint.x*($rect.Right-$rect.Left)/$probe.width)
    $point.Y=[int](($probe.height-$ScreenPoint.y)*($rect.Bottom-$rect.Top)/$probe.height)
    if($ScreenPoint.z -le 0 -or $point.X -lt 0 -or $point.Y -lt 0 -or $point.X -ge $rect.Right -or $point.Y -ge $rect.Bottom){throw 'Projected click falls outside the game client.'}
    [DemoInput]::ClientToScreen($window,[ref]$point)|Out-Null
    [DemoInput]::SetCursorPos($point.X,$point.Y)|Out-Null
    $down=if($Right){8}else{2};$up=if($Right){16}else{4}
    if($Walk){[DemoInput]::keybd_event(0x10,0,0,[UIntPtr]::Zero)}
    try {
        [DemoInput]::mouse_event($down,0,0,0,[UIntPtr]::Zero)
        Start-Sleep -Milliseconds 100
        [DemoInput]::mouse_event($up,0,0,0,[UIntPtr]::Zero)
    } finally {
        if($Walk){[DemoInput]::keybd_event(0x10,0,2,[UIntPtr]::Zero)}
    }
}
function Press-Key([byte]$Key) {
    Focus-Demo
    [DemoInput]::keybd_event($Key,0,0,[UIntPtr]::Zero)
    Start-Sleep -Milliseconds 90
    [DemoInput]::keybd_event($Key,0,2,[UIntPtr]::Zero)
}
function Wait-Probe([scriptblock]$Predicate,[string]$Failure,[int]$Seconds=5) {
    $deadline=(Get-Date).AddSeconds($Seconds)
    do {
        $probe=Read-Probe
        if(& $Predicate $probe){return $probe}
        Start-Sleep -Milliseconds 80
    } while((Get-Date) -lt $deadline)
    throw $Failure
}
$checks=[System.Collections.Generic.List[string]]::new()
$failures=[System.Collections.Generic.List[string]]::new()
try {
    $initial=Read-Probe
    Press-Key 0x24
    Start-Sleep -Milliseconds 200
    $probe=Read-Probe
    Click-World ($probe.units | Where-Object species -eq 'Krag').screen $false
    Press-Key 0x41
    $probe=Read-Probe
    Click-World ($probe.units | Where-Object species -eq 'Nib').screen $false
    Press-Key 0x46
    $null=Wait-Probe {param($p) ($p.units | Where-Object species -eq 'Krag').action -eq 'Melee' -and ($p.units | Where-Object species -eq 'Nib').action -eq 'Shoot'} 'Selecting and commanding the second unit interrupted overlapping actions' 2
    $checks.Add('Native clicks and keys started Nib shooting while Krag melee continued')
    $null=Wait-Probe {param($p) @($p.units | Where-Object action -ne 'Idle').Count -eq 0} 'Overlapping actions did not finish' 8
    Press-Key 0x41
    Focus-Demo
    $beforeCamera=Read-Probe
    $rect=New-Object DemoInput+RECT
    [DemoInput]::GetClientRect($window,[ref]$rect)|Out-Null
    $point=New-Object DemoInput+POINT
    $point.X=[int]($rect.Right*.5);$point.Y=[int]($rect.Bottom*.5)
    [DemoInput]::ClientToScreen($window,[ref]$point)|Out-Null
    [DemoInput]::SetCursorPos($point.X,$point.Y)|Out-Null
    [DemoInput]::mouse_event(0x20,0,0,0,[UIntPtr]::Zero)
    try {
        Start-Sleep -Milliseconds 60
        [DemoInput]::SetCursorPos($point.X+70,$point.Y+25)|Out-Null
        Start-Sleep -Milliseconds 100
    } finally {[DemoInput]::mouse_event(0x40,0,0,0,[UIntPtr]::Zero)}
    [DemoInput]::mouse_event(0x800,0,0,120,[UIntPtr]::Zero)
    $null=Wait-Probe {param($p) [Math]::Abs($p.cameraYaw-$beforeCamera.cameraYaw) -gt 1 -and $p.cameraDistance -lt $beforeCamera.cameraDistance} 'Native orbit/zoom input did not change the camera'
    Press-Key 0x27 # Right arrow pans the camera independently of the action.
    $null=Wait-Probe {param($p) [Math]::Abs($p.cameraFocus.x-$beforeCamera.cameraFocus.x)+[Math]::Abs($p.cameraFocus.z-$beforeCamera.cameraFocus.z) -gt .02} 'Native pan input did not change camera focus'
    $checks.Add('Native middle-mouse orbit, wheel zoom and arrow pan remained available during animation')
    Press-Key 0x24
    $null=Wait-Probe {param($p) @($p.units | Where-Object action -ne 'Idle').Count -eq 0} 'Camera test action did not finish' 8
    foreach($species in @('Krag','Nib')) {
        Press-Key 0x24 # Home restores a known camera framing.
        Start-Sleep -Milliseconds 350
        $probe=Read-Probe
        $unit=$probe.units | Where-Object species -eq $species
        Click-World $unit.screen $false
        $null=Wait-Probe {param($p) $p.selected -eq $species} "$species left-click selection failed"
        $checks.Add("$species selected with native Windows left mouse input")
        Press-Key 0x43 # C selects the close portrait camera.
        $null=Wait-Probe {param($p) $p.cameraDistance -lt 2} "$species portrait camera did not activate"
        Press-Key 0x45 # E starts the independent facial layer.
        $null=Wait-Probe {param($p) $p.facePlaying} "$species facial performance keyboard input failed"
        $checks.Add("$species portrait and facial performance activated with C and E")
        Press-Key 0x24
        foreach($action in @(@('Melee',0x41),@('Shoot',0x46),@('Hit',0x48))) {
            $actionName=$action[0]
            Press-Key $action[1]
            $null=Wait-Probe {param($p) $p.action -eq $actionName} "$species $actionName keyboard input failed"
            $checks.Add("$species $actionName activated with native keyboard input")
            $null=Wait-Probe {param($p) $p.action -eq 'Idle'} "$species did not return to Idle" 8
        }
        $before=(Read-Probe).variant
        Press-Key 0x56
        $null=Wait-Probe {param($p) $p.variant -ne $before} "$species V variant switch failed"
        $checks.Add("$species variant changed with V")
        $probe=Read-Probe
        $origin=($probe.units | Where-Object species -eq $species).position
        Click-World $probe.moveScreen $true
        $null=Wait-Probe {param($p) $p.moving} "$species right-click movement failed"
        $null=Wait-Probe {param($p) -not $p.moving -and $p.action -eq 'Idle'} "$species movement did not finish" 10
        $position=((Read-Probe).units | Where-Object species -eq $species).position
        $distance=[Math]::Sqrt([Math]::Pow($position.x-$origin.x,2)+[Math]::Pow($position.z-$origin.z,2))
        if($distance -lt 1){throw "$species accepted movement without traveling at least one meter"}
        $checks.Add("$species moved $([Math]::Round($distance,2)) meters after native right mouse input")
        Press-Key 0x24
        Start-Sleep -Milliseconds 250
        $probe=Read-Probe
        Click-World $probe.moveScreen $true $true
        $null=Wait-Probe {param($p) $p.moving -and $p.walking -and $p.action -eq 'Walk'} "$species Shift + right-click walking failed"
        $null=Wait-Probe {param($p) -not $p.moving -and $p.action -eq 'Idle'} "$species walk did not finish" 12
        $checks.Add("$species walked after native Shift + right mouse input")
    }
    Press-Key 0x24
    Start-Sleep -Milliseconds 300
    Press-Key 0x7B # F12 is the game's own capture path.
    $checks.Add('F12 capture input sent; output image must be inspected separately')
} catch { $failures.Add($_.Exception.Message) }
@{timestamp=(Get-Date).ToString('o');processId=$DemoProcessId;checks=@($checks);failures=@($failures)} |
    ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 (Join-Path $EvidencePath 'windows-input-verification.json')
if($failures.Count){throw ($failures -join '; ')}
Write-Output 'WINDOWS_INPUT_VERIFICATION_PASS'
