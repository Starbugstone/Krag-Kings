$ErrorActionPreference='Stop'
Add-Type @'
using System;
using System.Runtime.InteropServices;
using System.Text;
public static class KKForegroundReadOnly {
 [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hwnd,out uint pid);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr hwnd,StringBuilder name,int count);
}
'@
$window=[KKForegroundReadOnly]::GetForegroundWindow();$ownerId=[uint32]0
$null=[KKForegroundReadOnly]::GetWindowThreadProcessId($window,[ref]$ownerId)
$name=New-Object Text.StringBuilder 256;$null=[KKForegroundReadOnly]::GetClassName($window,$name,256)
$owner=Get-Process -Id $ownerId -ErrorAction SilentlyContinue
[ordered]@{utc=[DateTime]::UtcNow.ToString('o');timing='Read after game cleanup; not proof of owner at the earlier input abort';hwnd=$window.ToInt64();processId=$ownerId;processName=$owner.ProcessName;windowClass=$name.ToString();windowTitleCollected=$false;windowMutated=$false}|ConvertTo-Json|Set-Content 'D:\Dev\Krag-Kings\benchmark\local\evidence\unreal-native-input\coherent79-6926-first\foreground-after-cleanup.json' -Encoding UTF8
