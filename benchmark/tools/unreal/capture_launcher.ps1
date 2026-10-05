$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;using System.Runtime.InteropServices;public class LauncherCapture{[StructLayout(LayoutKind.Sequential)] public struct RECT{public int Left,Top,Right,Bottom;}[DllImport("user32.dll")]public static extern bool GetWindowRect(IntPtr h,out RECT r);[DllImport("user32.dll")]public static extern bool PrintWindow(IntPtr h,IntPtr dc,uint flags);}
'@
$p=Get-Process EpicGamesLauncher -ErrorAction SilentlyContinue | Where-Object {$_.MainWindowHandle -ne 0} | Select-Object -First 1
if(-not $p){throw 'Epic Launcher has no visible window yet.'}
$r=New-Object LauncherCapture+RECT
[LauncherCapture]::GetWindowRect($p.MainWindowHandle,[ref]$r)|Out-Null
$b=New-Object System.Drawing.Bitmap ($r.Right-$r.Left),($r.Bottom-$r.Top)
$g=[System.Drawing.Graphics]::FromImage($b);$dc=$g.GetHdc()
try{[LauncherCapture]::PrintWindow($p.MainWindowHandle,$dc,2)|Out-Null}finally{$g.ReleaseHdc($dc)}
$b.Save('D:\Dev\Krag-Kings\benchmark\unreal\evidence\epic-launcher.png',[System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose();$b.Dispose()
Write-Output ($r|ConvertTo-Json)
