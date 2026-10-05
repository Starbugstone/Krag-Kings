param([int]$X,[int]$Y)
Add-Type @'
using System;using System.Runtime.InteropServices;
public class LauncherMouse{[DllImport("user32.dll")]public static extern bool SetCursorPos(int X,int Y);[DllImport("user32.dll")]public static extern void mouse_event(uint f,uint x,uint y,uint d,UIntPtr e);}
'@
[LauncherMouse]::SetCursorPos($X,$Y)|Out-Null
[LauncherMouse]::mouse_event(2,0,0,0,[UIntPtr]::Zero)
[LauncherMouse]::mouse_event(4,0,0,0,[UIntPtr]::Zero)
