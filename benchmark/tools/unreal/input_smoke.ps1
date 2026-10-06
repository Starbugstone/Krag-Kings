[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$StatePath,[int]$GameProcessId=0,
 [ValidateSet('Packaged','EditorGame')][string]$ExecutionMode='Packaged')
$ErrorActionPreference='Stop'
Add-Type @'
using System;using System.Runtime.InteropServices;
public static class KKInput {
 [StructLayout(LayoutKind.Sequential)]public struct POINT {public int X,Y;}
 [StructLayout(LayoutKind.Sequential)]public struct RECT {public int Left,Top,Right,Bottom;}
 [DllImport("user32.dll")]public static extern bool SetProcessDPIAware();
 [DllImport("user32.dll")]public static extern bool SetForegroundWindow(IntPtr h);
 [DllImport("user32.dll")]public static extern IntPtr GetForegroundWindow();
 [DllImport("user32.dll")]public static extern bool ClientToScreen(IntPtr h,ref POINT p);
 [DllImport("user32.dll")]public static extern bool GetClientRect(IntPtr h,out RECT r);
 [DllImport("user32.dll")]public static extern bool SetCursorPos(int x,int y);
 [DllImport("user32.dll")]public static extern void mouse_event(uint flags,uint dx,uint dy,uint data,UIntPtr extra);
 [DllImport("user32.dll")]public static extern uint GetWindowThreadProcessId(IntPtr h,out uint processId);
 [DllImport("user32.dll")]public static extern IntPtr GetKeyboardLayout(uint threadId);
 [DllImport("user32.dll",EntryPoint="MapVirtualKeyExW",ExactSpelling=true)]public static extern uint MapVirtualKeyEx(uint code,uint mapType,IntPtr layout);
 [StructLayout(LayoutKind.Sequential)]public struct KEYBDINPUT {public ushort vk,scan;public uint flags,time;public UIntPtr extra;}
 [StructLayout(LayoutKind.Sequential)]public struct MOUSEINPUT {public int dx,dy;public uint data,flags,time;public UIntPtr extra;}
 [StructLayout(LayoutKind.Explicit)]public struct INPUTUNION {[FieldOffset(0)]public KEYBDINPUT key;[FieldOffset(0)]public MOUSEINPUT mouse;}
 [StructLayout(LayoutKind.Sequential)]public struct INPUT {public uint type;public INPUTUNION value;}
 [DllImport("user32.dll",SetLastError=true)]static extern uint SendInput(uint count,INPUT[] inputs,int size);
 public static void SendScan(uint scan,bool up) {
  uint flags=8u|((scan&0xFF00u)!=0?1u:0u)|(up?2u:0u);
  var input=new INPUT {type=1,value=new INPUTUNION {key=new KEYBDINPUT {scan=(ushort)(scan&0xFFu),flags=flags}}};
  if(SendInput(1,new[]{input},Marshal.SizeOf(typeof(INPUT)))!=1)throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error());
 }
}
'@
[KKInput]::SetProcessDPIAware()|Out-Null
$game=if($GameProcessId){Get-Process -Id $GameProcessId}else{Get-Process KragKingsBenchmark* -ErrorAction SilentlyContinue|Where-Object {$_.MainWindowHandle -ne 0}|Select-Object -First 1}
if(-not $game -or $game.MainWindowHandle -eq 0){throw 'A visible Unreal demo is required.'}
if($ExecutionMode -eq 'EditorGame' -and $game.ProcessName -notlike 'UnrealEditor*'){throw 'EditorGame evidence requires the explicitly selected Unreal editor game process.'}
if($ExecutionMode -eq 'Packaged' -and $game.ProcessName -notlike 'KragKingsBenchmark*'){throw 'Packaged evidence requires the actual standalone KragKingsBenchmark process.'}
[KKInput]::SetForegroundWindow($game.MainWindowHandle)|Out-Null
Start-Sleep -Milliseconds 200
function Assert-Foreground {if([KKInput]::GetForegroundWindow() -ne $game.MainWindowHandle){throw 'Demo lost foreground; stopped input delivery to preserve other applications.'}}
function Read-State {
 for($i=0;$i -lt 20;$i++) {try{return Get-Content $StatePath -Raw|ConvertFrom-Json}catch{Start-Sleep -Milliseconds 50}}
 throw 'No readable runtime input-state.json; launch with -KKInputState.'
}
function Send-Key([byte]$Code,[bool]$Up=$false) {
 [uint32]$owner=0
 $thread=[KKInput]::GetWindowThreadProcessId($game.MainWindowHandle,[ref]$owner)
 if($owner -ne $game.Id){throw 'Demo window ownership changed; keyboard input stopped.'}
 $layout=[KKInput]::GetKeyboardLayout($thread)
 # Supply physical scan codes to raw-input consumers. This host's French HKL
 # omits E0 from the navigation mapping even with MAPVK_VK_TO_VSC_EX (type 4).
 $mapped=[KKInput]::MapVirtualKeyEx($Code,4,$layout)
 if($mapped -eq 0){throw "No scan code for virtual key $Code in the demo keyboard layout."}
 if(($Code -ge 0x21 -and $Code -le 0x28) -or $Code -eq 0x2D -or $Code -eq 0x2E){$mapped=$mapped -bor 0xE000}
 [KKInput]::SendScan($mapped,$Up)
}
function Press-Key([byte]$Code) {
 Assert-Foreground
 Send-Key $Code
 try {Start-Sleep -Milliseconds 60} finally {Send-Key $Code $true}
}
function Hold-Key([byte]$Code,[int]$Milliseconds=250) {
 Assert-Foreground
 Send-Key $Code
 try {Start-Sleep -Milliseconds $Milliseconds} finally {Send-Key $Code $true}
}
function Orbit-Camera {
 Assert-Foreground
 $rect=New-Object KKInput+RECT;[KKInput]::GetClientRect($game.MainWindowHandle,[ref]$rect)|Out-Null
 $origin=New-Object KKInput+POINT;[KKInput]::ClientToScreen($game.MainWindowHandle,[ref]$origin)|Out-Null
 $x=$origin.X+[int]($rect.Right*.5);$y=$origin.Y+[int]($rect.Bottom*.5)
 [KKInput]::SetCursorPos($x,$y)|Out-Null
 [KKInput]::mouse_event(0x20,0,0,0,[UIntPtr]::Zero)
 try {for($i=0;$i -lt 4;$i++){Assert-Foreground;Start-Sleep -Milliseconds 50;[KKInput]::mouse_event(0x1,16,6,0,[UIntPtr]::Zero)}}
 finally {[KKInput]::mouse_event(0x40,0,0,0,[UIntPtr]::Zero)}
}
function Click-Client([double]$X,[double]$Y,[bool]$Right=$false,[bool]$Shift=$false) {
 Assert-Foreground
 $bounds=New-Object KKInput+RECT;[KKInput]::GetClientRect($game.MainWindowHandle,[ref]$bounds)|Out-Null
 if($X -lt 0 -or $Y -lt 0 -or $X -ge $bounds.Right -or $Y -ge $bounds.Bottom){throw 'Requested click lies outside game client; input stopped.'}
 $origin=New-Object KKInput+POINT
 [KKInput]::ClientToScreen($game.MainWindowHandle,[ref]$origin)|Out-Null
 [KKInput]::SetCursorPos($origin.X+[int]$X,$origin.Y+[int]$Y)|Out-Null
 if($Shift){Send-Key 0xA0}
 try {
  [KKInput]::mouse_event($(if($Right){0x8}else{0x2}),0,0,0,[UIntPtr]::Zero)
  Start-Sleep -Milliseconds 60
  [KKInput]::mouse_event($(if($Right){0x10}else{0x4}),0,0,0,[UIntPtr]::Zero)
 }finally{if($Shift){Send-Key 0xA0 $true}}
}
$checks=New-Object System.Collections.Generic.List[object]
function Expect-State([string]$Name,[scriptblock]$Predicate,[int]$TimeoutMs=3000) {
 $end=[DateTime]::UtcNow.AddMilliseconds($TimeoutMs);$pass=$false
 do {$state=Read-State;if(& $Predicate $state){$pass=$true;break};Start-Sleep -Milliseconds 75}while([DateTime]::UtcNow -lt $end)
 $checks.Add([pscustomobject]@{check=$Name;passed=$pass;runtimeElapsed=$state.elapsed})
 Write-Output "$Name : $pass"
 if(-not $pass){throw "Runtime input check failed: $Name"}
}
try {
 $initial=Read-State;Start-Sleep -Milliseconds 250
 if((Read-State).elapsed -le $initial.elapsed){throw 'Runtime state is stale; game is not updating.'}
 $nib=$initial.units|Where-Object {$_.species -eq 'Nib'}
 Click-Client $nib.screen_x $nib.screen_y
 Expect-State 'LMB selects Nib' {param($s)($s.units|Where-Object {$_.species -eq 'Nib'}).selected}
 Press-Key 0x09
 Expect-State 'Tab changes selected unit' {param($s)($s.units|Where-Object {$_.species -eq 'Krag'}).selected}
 Press-Key 0x41
 Expect-State 'Krag melee begins for overlap test' {param($s)($s.units|Where-Object {$_.species -eq 'Krag'}).action -eq 'Melee'}
 $nib=(Read-State).units|Where-Object {$_.species -eq 'Nib'}
 Click-Client $nib.screen_x $nib.screen_y
 Press-Key 0x46
 Expect-State 'Nib shoots while Krag melee remains active' {param($s)(($s.units|Where-Object {$_.species -eq 'Krag'}).action -eq 'Melee') -and (($s.units|Where-Object {$_.species -eq 'Nib'}).action -eq 'Shoot')}
 $krag=(Read-State).units|Where-Object {$_.species -eq 'Krag'}
 Click-Client $krag.screen_x $krag.screen_y
 foreach($entry in @(@(0x41,'Melee'),@(0x46,'Shoot'),@(0x48,'Hit'))) {
  Press-Key ([byte]$entry[0]);$action=$entry[1]
  Expect-State "$action key triggers authored action" {param($s)($s.units|Where-Object selected).action -eq $action}
 }
 Press-Key 0x41
 $camera=(Read-State).camera
 Hold-Key 0x27
 Expect-State 'Arrow pans camera during action' {param($s)([math]::Abs($s.camera.x-$camera.x)+[math]::Abs($s.camera.y-$camera.y) -gt 5) -and (($s.units|Where-Object selected).action -eq 'Melee')}
 $camera=(Read-State).camera
 Orbit-Camera
 Expect-State 'MMB orbits camera' {param($s)[math]::Abs($s.camera.yaw-$camera.yaw) -gt 1}
 $camera=(Read-State).camera
 Assert-Foreground;[KKInput]::mouse_event(0x800,0,0,120,[UIntPtr]::Zero)
 Expect-State 'Mouse wheel zooms camera' {param($s)[math]::Abs($s.camera.z-$camera.z) -gt 3}
 Press-Key 0x24
 $before=Read-State;$variant=($before.units|Where-Object selected).variant
 Press-Key 0x56
 Expect-State 'V changes bionic variant' {param($s)($s.units|Where-Object selected).variant -ne $variant}
 Press-Key 0x45
 Expect-State 'E starts facial acting' {param($s)($s.units|Where-Object selected).face_active}
 Expect-State 'Facial curves reach applied mesh morph weights' {param($s)($s.units|Where-Object selected).facial_morph_weight -gt .01}
 Press-Key 0x43
 Expect-State 'C enters portrait' {param($s)$s.portrait}
 $camera=(Read-State).camera
 Hold-Key 0x27
 Expect-State 'Portrait camera retains pan control' {param($s)$s.portrait -and ([math]::Abs($s.camera.x-$camera.x)+[math]::Abs($s.camera.y-$camera.y) -gt 3)}
 Press-Key 0x77
 Press-Key 0x24
 Expect-State 'Home resets portrait' {param($s)-not $s.portrait}
 $rect=New-Object KKInput+RECT;[KKInput]::GetClientRect($game.MainWindowHandle,[ref]$rect)|Out-Null
 Click-Client ($rect.Right*.4) ($rect.Bottom*.8) $true $false
 Expect-State 'RMB runs to terrain' {param($s)($s.units|Where-Object selected).action -eq 'Run'}
 Expect-State 'Run activates applied body corrective weights' {param($s)($s.units|Where-Object selected).body_morph_weight -gt .01}
 $before=Read-State;Start-Sleep -Milliseconds 700;$after=Read-State
 $u0=$before.units|Where-Object selected;$u1=$after.units|Where-Object selected
 $moved=[math]::Sqrt([math]::Pow($u1.x-$u0.x,2)+[math]::Pow($u1.y-$u0.y,2))
 $checks.Add([pscustomobject]@{check='RMB causes world movement';passed=($moved -gt 25);distanceCm=$moved})
 Click-Client ($rect.Right*.65) ($rect.Bottom*.75) $true $true
 Expect-State 'Shift+RMB walks to terrain' {param($s)($s.units|Where-Object selected).action -eq 'Walk'}
 Press-Key 0x77
} finally {
 $report=[ordered]@{source='Windows mouse and keyboard delivered to visible Unreal demo';executionMode=$ExecutionMode;packagedBuildTested=($ExecutionMode -eq 'Packaged');mouse_keyboard_delivery_tested=($checks.Count -gt 0);visual_quality_accepted=$false;timestampUtc=[DateTime]::UtcNow.ToString('o');checks=@($checks.ToArray())}
 $report|ConvertTo-Json -Depth 6|Set-Content (Join-Path (Split-Path $StatePath) 'input-smoke-report.json') -Encoding UTF8
}
