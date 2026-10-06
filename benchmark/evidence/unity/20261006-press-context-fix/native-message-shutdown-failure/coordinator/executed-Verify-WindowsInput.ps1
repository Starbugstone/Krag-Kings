param(
    [Parameter(Mandatory=$true)][int]$DemoProcessId,
    [Parameter(Mandatory=$true)][string]$EvidencePath,
    [string]$WindowHelperPath=(Join-Path $PSScriptRoot '..\capture\OwnedGameWindow.ps1'),
    [switch]$ModifierOnly,
    [switch]$RequireWindowsPressContext
)
$ErrorActionPreference='Stop'
. $WindowHelperPath
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;using System.Runtime.InteropServices;
public static class DemoInput {
 [StructLayout(LayoutKind.Sequential)] public struct POINT { public int X,Y; }
 [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left,Top,Right,Bottom; }
 [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
 [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
 [DllImport("user32.dll")] public static extern short GetAsyncKeyState(int key);
 [DllImport("user32.dll")] public static extern bool ClientToScreen(IntPtr h,ref POINT p);
 [DllImport("user32.dll")] public static extern bool ScreenToClient(IntPtr h,ref POINT p);
 [DllImport("user32.dll")] public static extern bool GetCursorPos(out POINT p);
 [DllImport("user32.dll")] public static extern uint GetDpiForWindow(IntPtr h);
 [DllImport("user32.dll")] public static extern IntPtr GetWindowDpiAwarenessContext(IntPtr h);
 [DllImport("user32.dll")] public static extern IntPtr GetThreadDpiAwarenessContext();
 [DllImport("user32.dll")] public static extern int GetAwarenessFromDpiAwarenessContext(IntPtr h);
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
 public static void SendQuickMoveClick(ushort shiftScan) {
  var inputs=new System.Collections.Generic.List<INPUT>();
  if(shiftScan!=0)inputs.Add(new INPUT {type=1,value=new INPUTUNION {key=new KEYBDINPUT {scan=shiftScan,flags=8}}});
  inputs.AddRange(new[]{
   new INPUT {type=0,value=new INPUTUNION {mouse=new MOUSEINPUT {flags=8}}},
   new INPUT {type=0,value=new INPUTUNION {mouse=new MOUSEINPUT {flags=16}}}
  });
  if(shiftScan!=0)inputs.Add(new INPUT {type=1,value=new INPUTUNION {key=new KEYBDINPUT {scan=shiftScan,flags=10}}});
  uint sent=SendInput((uint)inputs.Count,inputs.ToArray(),Marshal.SizeOf(typeof(INPUT)));
  if(sent!=inputs.Count){if(shiftScan!=0)SendScan(shiftScan,true);throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error());}
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
    try {
        $windowLease.AssertForeground()
        foreach($key in @(0x5B,0x5C,0xA2,0xA3,0xA4,0xA5)) {
            if(([int][DemoInput]::GetAsyncKeyState($key) -band 0x8000) -ne 0){throw 'An external Windows/Ctrl/Alt modifier is held; stopped before sending test input.'}
        }
    }
    catch {try{$pointerEvidence.Add($windowLease.InspectPointer())}catch{};throw}
}
function Record-InputEdge([string]$Kind,$Detail) {
    $front=[DemoInput]::GetForegroundWindow();$owner=[uint32]0
    $null=[DemoInput]::GetWindowThreadProcessId($front,[ref]$owner)
    $modifiers=[ordered]@{}
    foreach($key in @(0xA0,0xA1,0xA2,0xA3,0xA4,0xA5,0x5B,0x5C)) {
        $modifiers[('0x{0:X2}' -f $key)]=(([int][DemoInput]::GetAsyncKeyState($key) -band 0x8000) -ne 0)
    }
    $inputEdges.Add(@{utc=[DateTime]::UtcNow.ToString('o');kind=$Kind;detail=$Detail;foregroundHwnd=$front.ToInt64();foregroundPid=$owner;modifiers=$modifiers})
}
function Read-PointerGeometry($Probe) {
    $r=New-Object DemoInput+RECT;$origin=New-Object DemoInput+POINT;$screen=New-Object DemoInput+POINT
    if(-not [DemoInput]::GetClientRect($window,[ref]$r) -or -not [DemoInput]::ClientToScreen($window,[ref]$origin) -or -not [DemoInput]::GetCursorPos([ref]$screen)){throw 'Cannot record owned game client/pointer geometry'}
    $client=New-Object DemoInput+POINT;$client.X=$screen.X;$client.Y=$screen.Y
    if(-not [DemoInput]::ScreenToClient($window,[ref]$client)){throw 'Cannot transform the pointer into the owned game client'}
    return @{clientWidth=$r.Right-$r.Left;clientHeight=$r.Bottom-$r.Top;clientOrigin=@{x=$origin.X;y=$origin.Y};screenCursor=@{x=$screen.X;y=$screen.Y};clientCursor=@{x=$client.X;y=$client.Y};
        outputWidth=$Probe.width;outputHeight=$Probe.height;expectedUnityCursor=@{x=$client.X*$Probe.width/($r.Right-$r.Left);y=($r.Bottom-$r.Top-$client.Y)*$Probe.height/($r.Bottom-$r.Top)};
        windowDpi=[DemoInput]::GetDpiForWindow($window);windowDpiAwareness=[DemoInput]::GetAwarenessFromDpiAwarenessContext([DemoInput]::GetWindowDpiAwarenessContext($window));threadDpiAwareness=[DemoInput]::GetAwarenessFromDpiAwarenessContext([DemoInput]::GetThreadDpiAwarenessContext())}
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
    if(-not $Up){Focus-Demo}
    Record-InputEdge 'KeyBefore' @{virtualKey=$Key;scan=$scan;up=$Up}
    [DemoInput]::SendScan($scan,$Up)
    Record-InputEdge 'KeyAfter' @{virtualKey=$Key;scan=$scan;up=$Up}
}
function Click-World($ScreenPoint,[bool]$Right,[bool]$Walk=$false,[bool]$QuickWalk=$false,[uint16]$QuickShiftScan=0x2A) {
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
    Start-Sleep -Milliseconds 60
    $pointerEvidence.Add($windowLease.AssertPointer())
    $pointerGeometry=Read-PointerGeometry $probe
    Record-InputEdge 'PointerBeforeClick' @{requestedUnity=$ScreenPoint;requestedScreen=@{x=$point.X;y=$point.Y};geometry=$pointerGeometry}
    if([Math]::Abs($pointerGeometry.screenCursor.x-$point.X) -gt 2 -or [Math]::Abs($pointerGeometry.screenCursor.y-$point.Y) -gt 2){throw 'Pointer moved away from the injected destination before the click; stopped without sending mouse input.'}
    if($QuickWalk){
        if(-not $Right -or $Walk -ne ($QuickShiftScan -ne 0)){throw 'The immediate movement probe requires a consistent Shift mode.'}
        Focus-Demo
        Record-InputEdge 'ImmediateMoveBefore' @{shiftScan=$QuickShiftScan;pressPosition=$ScreenPoint;requestedHoldMilliseconds=0;geometry=(Read-PointerGeometry $probe)}
        [DemoInput]::SendQuickMoveClick($QuickShiftScan)
        Record-InputEdge 'ImmediateMoveAfter' @{shiftScan=$QuickShiftScan;pressPosition=$ScreenPoint;requestedHoldMilliseconds=0;geometry=(Read-PointerGeometry $probe)}
        return
    }
    $down=if($Right){8}else{2};$up=if($Right){16}else{4}
    if($Walk){Send-Key 0xA0}
    try {
        [DemoInput]::mouse_event($down,0,0,0,[UIntPtr]::Zero)
        Start-Sleep -Milliseconds 100
    } finally {
        [DemoInput]::mouse_event($up,0,0,0,[UIntPtr]::Zero)
        if($Walk){Send-Key 0xA0 $true}
    }
}
function Press-Key([byte]$Key) {
    Focus-Demo
    Send-Key $Key
    try {Start-Sleep -Milliseconds 90} finally {Send-Key $Key $true}
}
function Zoom-ForMove {
    # Repeated traversals spread the pair apart. Four fixed notches can leave
    # the next projected destination outside the window or behind the HUD.
    # Use only real wheel input and wait for its resulting camera probe.
    Focus-Demo
    for($notch=0;$notch -lt 36;$notch++){
        $probe=Read-Probe
        $p=$probe.moveScreen
        if($p.z -gt 0 -and $p.x -gt .12*$probe.width -and $p.x -lt .88*$probe.width -and $p.y -gt .16*$probe.height -and $p.y -lt .84*$probe.height){return}
        $before=$probe.cameraDistance
        if($before -ge 27.9){throw 'Movement destination remains outside the usable viewport at maximum zoom-out.'}
        [DemoInput]::mouse_event(0x800,0,0,4294967176,[UIntPtr]::Zero) # signed -120
        $null=Wait-Probe {param($p) $p.cameraDistance -gt $before+.2} 'Zoom-out did not update the actual camera projection'
    }
    throw 'Movement destination was not framed within the bounded wheel-input budget.'
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
$pointerEvidence=[System.Collections.Generic.List[object]]::new()
$cameraObservations=[System.Collections.Generic.List[object]]::new()
$inputEdges=[System.Collections.Generic.List[object]]::new()
$modifierObservations=[System.Collections.Generic.List[object]]::new()
$windowLease=$null
try {
    $initial=Read-Probe
    # Startup shader work can stall the first rendered frames. Never enqueue
    # the opening sequence against a stale projection/selection snapshot.
    $null=Wait-Probe {param($p) $p.frame -ge 120} 'Runtime did not finish initial rendered-frame warmup' 45
    $demo.Refresh();$window=$demo.MainWindowHandle
    $windowLease=[KKOwnedWindowLease]::Acquire($window,[uint32]$demo.Id)
    if($RequireWindowsPressContext){
        $initial=Read-Probe
        if($initial.movementBackend -ne 'Win32 message context' -or $initial.nativeWindowHandle -ne $window.ToInt64() -or $initial.inputMergingDisabled -or $initial.nativeInputError){throw 'Native movement source/profile does not match this owned game window.'}
    }
    if($ModifierOnly) {
        if(-not $initial.PSObject.Properties['movePressCount']){throw 'This package does not expose the press-context queue probe; build the authorized fix first.'}
        Press-Key 0x24
        $null=Wait-Probe {param($p) [Math]::Abs($p.cameraYaw-165) -lt .1 -and [Math]::Abs($p.cameraDistance-6.4) -lt .1} 'Home reset was not observed'
        $probe=Read-Probe
        Click-World ($probe.units | Where-Object species -eq 'Krag').screen $false
        $null=Wait-Probe {param($p) $p.selected -eq 'Krag'} 'Focused modifier probe could not select Krag'
        foreach($case in @(@{name='RightShift';scan=0x36},@{name='Unmodified after RightShift';scan=0},@{name='LeftShift';scan=0x2A},@{name='Unmodified after LeftShift';scan=0})) {
            $null=Wait-Probe {param($p) -not $p.moving -and $p.action -eq 'Idle'} 'Previous focused movement did not settle' 12
            Zoom-ForMove
            $before=Read-Probe;$target=$before.moveScreen;$expectedWalk=$case.scan -ne 0
            Click-World $target $true $expectedWalk $true ([uint16]$case.scan)
            $after=Wait-Probe {param($p) $p.movePressCount -gt $before.movePressCount} ($case.name+' immediate press was not dispatched')
            $modifierObservations.Add(@{name=$case.name;before=$before;after=$after;target=$target;requestedHoldMilliseconds=0})
            if($after.movePressCount -ne $before.movePressCount+1 -or -not $after.movePressAccepted -or $after.movePress.walk -ne $expectedWalk){throw ($case.name+' did not retain exactly one accepted press with the expected modifier')}
            if([Math]::Abs($after.movePress.position.x-$target.x) -gt 2 -or [Math]::Abs($after.movePress.position.y-$target.y) -gt 2){throw ($case.name+' captured pointer differs from the actual projected destination')}
            if($RequireWindowsPressContext){
                $native=@($after.nativePressHistory|Where-Object {$_.sequence -eq $after.movePress.eventId})
                if($native.Count -ne 1 -or $native[0].walk -ne $expectedWalk -or (($native[0].flags -band 4) -ne 0) -ne $expectedWalk -or $after.nativeInputError){throw ($case.name+' lacks one matching native press context with authoritative MK_SHIFT')}
            }
            $null=Wait-Probe {param($p) $p.moving -and $p.walking -eq $expectedWalk -and $p.action -eq $(if($expectedWalk){'Walk'}else{'Run'})} ($case.name+' did not produce the expected movement clip')
            $settled=Wait-Probe {param($p) -not $p.moving -and $p.action -eq 'Idle'} ($case.name+' movement did not finish') 12
            if($RequireWindowsPressContext -and $settled.movePressCount -ne $before.movePressCount+1){throw ($case.name+' produced a duplicate movement command')}
            $checks.Add($case.name+' zero-hold native batch retained cursor/modifier and completed movement')
        }
    } else {
    Press-Key 0x24
    Start-Sleep -Milliseconds 200
    $probe=Read-Probe
    Click-World ($probe.units | Where-Object species -eq 'Krag').screen $false
    $null=Wait-Probe {param($p) $p.selected -eq 'Krag'} 'Opening Krag click was not observed'
    Press-Key 0x41
    $null=Wait-Probe {param($p) ($p.units | Where-Object species -eq 'Krag').action -eq 'Melee'} 'Opening Krag melee was not observed'
    $probe=Read-Probe
    Click-World ($probe.units | Where-Object species -eq 'Nib').screen $false
    $null=Wait-Probe {param($p) $p.selected -eq 'Nib'} 'Opening Nib click was not observed'
    Press-Key 0x46
    $null=Wait-Probe {param($p) ($p.units | Where-Object species -eq 'Krag').action -eq 'Melee' -and ($p.units | Where-Object species -eq 'Nib').action -eq 'Shoot'} 'Native clicks/keys did not produce concurrent Krag melee and Nib shooting' 2
    $checks.Add('Native clicks and keys started Nib shooting while Krag melee continued')
    $null=Wait-Probe {param($p) @($p.units | Where-Object action -ne 'Idle').Count -eq 0} 'Overlapping actions did not finish' 8
    $beforeCameraFrame=(Read-Probe).frame
    Press-Key 0x41
    $beforeCamera=Wait-Probe {param($p) $p.frame -gt $beforeCameraFrame -and $p.action -eq 'Melee'} 'Camera overlap check did not observe a fresh Melee state'
    Focus-Demo
    $cameraObservations.Add(@{control='OrbitZoom';observedUtc=[DateTime]::UtcNow.ToString('o');beforeInputFrame=$beforeCameraFrame;actionFrame=$beforeCamera.frame;action=$beforeCamera.action;cameraYaw=$beforeCamera.cameraYaw;cameraDistance=$beforeCamera.cameraDistance})
    $rect=New-Object DemoInput+RECT
    [DemoInput]::GetClientRect($window,[ref]$rect)|Out-Null
    $point=New-Object DemoInput+POINT
    $point.X=[int]($rect.Right*.5);$point.Y=[int]($rect.Bottom*.5)
    [DemoInput]::ClientToScreen($window,[ref]$point)|Out-Null
    [DemoInput]::SetCursorPos($point.X,$point.Y)|Out-Null
    $pointerEvidence.Add($windowLease.AssertPointer())
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
    $beforePanFrame=(Read-Probe).frame
    Press-Key 0x41 # Restart an action for a separate pan-during-animation check.
    $beforePan=Wait-Probe {param($p) $p.frame -gt $beforePanFrame -and $p.action -eq 'Melee'} 'Pan check did not observe a fresh Melee state'
    $cameraObservations.Add(@{control='Pan';observedUtc=[DateTime]::UtcNow.ToString('o');beforeInputFrame=$beforePanFrame;actionFrame=$beforePan.frame;action=$beforePan.action;cameraFocus=$beforePan.cameraFocus;requestedArrowHoldMilliseconds=90})
    Press-Key 0x27 # Right arrow pans the camera independently of the action.
    $null=Wait-Probe {param($p) [Math]::Abs($p.cameraFocus.x-$beforePan.cameraFocus.x)+[Math]::Abs($p.cameraFocus.z-$beforePan.cameraFocus.z) -gt .02 -and $p.action -eq 'Melee'} 'Native pan input did not change camera focus'
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
        Press-Key 0x24
        Start-Sleep -Milliseconds 250
        Zoom-ForMove
        $probe=Read-Probe
        Click-World $probe.moveScreen $true $true $true
        $null=Wait-Probe {param($p) $p.moving -and $p.walking -and $p.action -eq 'Walk'} "$species immediate Shift + right-click lost its press-time modifier"
        $null=Wait-Probe {param($p) -not $p.moving -and $p.action -eq 'Idle'} "$species immediate walking command did not finish" 12
        $checks.Add("$species immediate Shift + right-click preserved walking after all input events were queued together")
    }
    Press-Key 0x24
    Start-Sleep -Milliseconds 300
    Press-Key 0x7B # F12 is the game's own capture path.
    $checks.Add('F12 capture input sent; output image must be inspected separately')
    }
} catch { $failures.Add($_.Exception.Message) }
finally {if($windowLease){try{$windowLease.Dispose()}catch{$failures.Add($_.Exception.Message)}}}
@{timestamp=(Get-Date).ToString('o');processId=$DemoProcessId;modifierOnly=[bool]$ModifierOnly;requireWindowsPressContext=[bool]$RequireWindowsPressContext;movementBackend=$initial.movementBackend;buildGuid=$initial.buildGuid;contentFingerprint=$initial.contentFingerprint;keyboardLayout=$initial.keyboardLayout;physicalAKeyLabel=$initial.physicalAKeyLabel;checks=@($checks);failures=@($failures);pointerGuards=@($pointerEvidence.ToArray());cameraObservations=@($cameraObservations.ToArray());inputEdges=@($inputEdges.ToArray());modifierObservations=@($modifierObservations.ToArray());windowLeaseRestored=($windowLease -and $windowLease.Restored)} |
    ConvertTo-Json -Depth 10 | Set-Content -Encoding UTF8 (Join-Path $EvidencePath 'windows-input-verification.json')
if($failures.Count){throw ($failures -join '; ')}
Write-Output 'WINDOWS_INPUT_VERIFICATION_PASS'
