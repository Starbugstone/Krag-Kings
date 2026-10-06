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
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h,out uint processId);
 [DllImport("user32.dll")] public static extern IntPtr GetKeyboardLayout(uint threadId);
 [DllImport("user32.dll",EntryPoint="MapVirtualKeyExW",ExactSpelling=true)] public static extern uint MapVirtualKeyEx(uint code,uint type,IntPtr layout);
 [StructLayout(LayoutKind.Sequential)] public struct KEYBDINPUT {public ushort vk,scan;public uint flags,time;public UIntPtr extra;}
 [StructLayout(LayoutKind.Sequential)] public struct MOUSEINPUT {public int dx,dy;public uint data,flags,time;public UIntPtr extra;}
 [StructLayout(LayoutKind.Explicit)] public struct INPUTUNION {[FieldOffset(0)]public KEYBDINPUT key;[FieldOffset(0)]public MOUSEINPUT mouse;}
 [StructLayout(LayoutKind.Sequential)] public struct INPUT {public uint type;public INPUTUNION value;}
 [DllImport("user32.dll",SetLastError=true)] static extern uint SendInput(uint count,INPUT[] inputs,int size);
 public static void SendScan(uint scan,bool up) {
  uint flags=8u | ((scan & 0xFF00u)!=0?1u:0u) | (up?2u:0u);
  var input=new INPUT {type=1,value=new INPUTUNION {key=new KEYBDINPUT {scan=(ushort)(scan & 0xFFu),flags=flags}}};
  if(SendInput(1,new[]{input},Marshal.SizeOf(typeof(INPUT)))!=1)throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error());
 }
}
'@
$demo=Get-Process -Id $DemoProcessId
if($demo.ProcessName -ne 'KragKings-Unity') {throw 'Input verification only targets the packaged KragKings-Unity process.'}
$window=$demo.MainWindowHandle
if($window -eq [IntPtr]::Zero){throw 'Packaged demo has no visible window.'}
$probePath=Join-Path $EvidencePath 'input-probe.json'
function Read-Probe {
    $lastError='No probe yet'
    for($attempt=0;$attempt -lt 20;$attempt++) {
        $reader=$null
        try {
            $stream=[IO.File]::Open($probePath,[IO.FileMode]::Open,[IO.FileAccess]::Read,([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete))
            $reader=[IO.StreamReader]::new($stream)
            return $reader.ReadToEnd() | ConvertFrom-Json
        } catch {$lastError=$_.Exception.Message;Start-Sleep -Milliseconds 50}
        finally {if($reader){$reader.Dispose()}}
    }
    throw "Cannot read runtime input probe at $probePath : $lastError"
}
function Focus-Demo {
    [DemoInput]::SetForegroundWindow($window)|Out-Null
    Start-Sleep -Milliseconds 150
    if([DemoInput]::GetForegroundWindow() -ne $window){throw 'Demo did not receive focus; no input sent to another application.'}
}
function Send-Key([byte]$Key,[bool]$Up=$false) {
    # Raw-input consumers need a real scan code, including the extended flag
    # for Home and arrows. Resolve against the target window's keyboard layout.
    $owner=[uint32]0
    $thread=[DemoInput]::GetWindowThreadProcessId($window,[ref]$owner)
    $layout=[DemoInput]::GetKeyboardLayout($thread)
    $scan=[DemoInput]::MapVirtualKeyEx($Key,4,$layout)
    if($scan -eq 0){throw "No scan code for virtual key $Key on the game's keyboard layout."}
    # This host's French layout returns 0x47/0x4D without E0 even for type 4.
    # Navigation keys must remain distinct from the numeric keypad.
    if(($Key -ge 0x21 -and $Key -le 0x28) -or $Key -eq 0x2D -or $Key -eq 0x2E){$scan=$scan -bor 0xE000}
    [DemoInput]::SendScan($scan,$Up)
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
    if($Walk){Send-Key 0xA0}
    try {
        [DemoInput]::mouse_event($down,0,0,0,[UIntPtr]::Zero)
        Start-Sleep -Milliseconds 100
        [DemoInput]::mouse_event($up,0,0,0,[UIntPtr]::Zero)
    } finally {
        if($Walk){Send-Key 0xA0 $true}
    }
}
function Press-Key([byte]$Key) {
    Focus-Demo
    Send-Key $Key
    Start-Sleep -Milliseconds 90
    Send-Key $Key $true
}
function Zoom-ForMove {
    # Frame a visible sand destination above the bottom controls before clicking.
    Focus-Demo
    $before=(Read-Probe).cameraDistance
    for($notch=0;$notch -lt 4;$notch++){
        [DemoInput]::mouse_event(0x800,0,0,4294967176,[UIntPtr]::Zero) # signed -120
        Start-Sleep -Milliseconds 60
    }
    $null=Wait-Probe {param($p) $p.cameraDistance -gt $before+1} 'Zoom-out did not reveal a movement destination'
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
    $null=Wait-Probe {param($p) ($p.units | Where-Object species -eq 'Krag').action -eq 'Melee' -and ($p.units | Where-Object species -eq 'Nib').action -eq 'Shoot'} 'Native clicks/keys did not produce concurrent Krag melee and Nib shooting' 2
    $checks.Add('Native clicks and keys started Nib shooting while Krag melee continued')
    $null=Wait-Probe {param($p) @($p.units | Where-Object action -ne 'Idle').Count -eq 0} 'Overlapping actions did not finish' 8
    Press-Key 0x41
    Focus-Demo
    $beforeCamera=Read-Probe
    if($beforeCamera.action -ne 'Melee'){throw 'Camera overlap check did not start its action.'}
    $rect=New-Object DemoInput+RECT
    [DemoInput]::GetClientRect($window,[ref]$rect)|Out-Null
    $point=New-Object DemoInput+POINT
    $point.X=[int]($rect.Right*.5);$point.Y=[int]($rect.Bottom*.5)
    [DemoInput]::ClientToScreen($window,[ref]$point)|Out-Null
    [DemoInput]::SetCursorPos($point.X,$point.Y)|Out-Null
    [DemoInput]::mouse_event(0x20,0,0,0,[UIntPtr]::Zero)
    try {
        for($step=0;$step -lt 4;$step++){
            Start-Sleep -Milliseconds 50
            [DemoInput]::mouse_event(0x1,16,6,0,[UIntPtr]::Zero)
        }
        Start-Sleep -Milliseconds 60
    } finally {[DemoInput]::mouse_event(0x40,0,0,0,[UIntPtr]::Zero)}
    [DemoInput]::mouse_event(0x800,0,0,120,[UIntPtr]::Zero)
    $null=Wait-Probe {param($p) [Math]::Abs($p.cameraYaw-$beforeCamera.cameraYaw) -gt 1 -and $p.cameraDistance -lt $beforeCamera.cameraDistance-.2 -and $p.action -eq 'Melee'} 'Native orbit/zoom input did not change the camera'
    Press-Key 0x41 # Restart an action for a separate pan-during-animation check.
    Press-Key 0x27 # Right arrow pans the camera independently of the action.
    $null=Wait-Probe {param($p) [Math]::Abs($p.cameraFocus.x-$beforeCamera.cameraFocus.x)+[Math]::Abs($p.cameraFocus.z-$beforeCamera.cameraFocus.z) -gt .02 -and $p.action -eq 'Melee'} 'Native pan input did not change camera focus'
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
        Zoom-ForMove
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
        Zoom-ForMove
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
@{timestamp=(Get-Date).ToString('o');processId=$DemoProcessId;buildGuid=$initial.buildGuid;contentFingerprint=$initial.contentFingerprint;keyboardLayout=$initial.keyboardLayout;physicalAKeyLabel=$initial.physicalAKeyLabel;checks=@($checks);failures=@($failures)} |
    ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 (Join-Path $EvidencePath 'windows-input-verification.json')
if($failures.Count){throw ($failures -join '; ')}
Write-Output 'WINDOWS_INPUT_VERIFICATION_PASS'
