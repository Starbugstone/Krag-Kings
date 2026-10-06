# Dot-source this helper only for an explicitly identified task-owned game HWND.
# It never closes, hides, captures, or changes another application's window.
if(-not ('KKOwnedWindowLease' -as [type])) {
Add-Type @'
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
public sealed class KKOwnedWindowLease : IDisposable {
 [StructLayout(LayoutKind.Sequential)]public struct POINT {public int X,Y;}
 [StructLayout(LayoutKind.Sequential)]struct MSG {public IntPtr hwnd;public uint message;public UIntPtr wparam;public IntPtr lparam;public uint time;public POINT point;public uint extra;}
 public sealed class PointerEvidence {public long gameHwnd,foregroundHwnd,pointerHwnd;public uint gamePid,foregroundPid,pointerPid;public int x,y;}
 [DllImport("user32.dll")]static extern bool IsWindow(IntPtr h);
 [DllImport("user32.dll")]static extern bool IsIconic(IntPtr h);
 [DllImport("user32.dll")]static extern bool IsWindowVisible(IntPtr h);
 [DllImport("user32.dll")]static extern IntPtr GetWindow(IntPtr h,uint command);
 [DllImport("user32.dll",EntryPoint="GetWindowLongPtrW")]static extern IntPtr GetWindowLongPtr(IntPtr h,int index);
 [DllImport("user32.dll",SetLastError=true)]static extern bool SetWindowPos(IntPtr h,IntPtr after,int x,int y,int w,int height,uint flags);
 [DllImport("user32.dll")]static extern IntPtr GetForegroundWindow();
 [DllImport("user32.dll")]static extern bool SetForegroundWindow(IntPtr h);
 [DllImport("user32.dll")]static extern bool BringWindowToTop(IntPtr h);
 [DllImport("user32.dll")]static extern bool AttachThreadInput(uint a,uint b,bool attach);
 [DllImport("kernel32.dll")]static extern uint GetCurrentThreadId();
 [DllImport("user32.dll")]static extern bool PeekMessage(out MSG msg,IntPtr h,uint min,uint max,uint remove);
 [DllImport("user32.dll")]static extern uint GetWindowThreadProcessId(IntPtr h,out uint pid);
 [DllImport("user32.dll")]static extern bool GetCursorPos(out POINT p);
 [DllImport("user32.dll")]static extern IntPtr WindowFromPoint(POINT p);
 readonly IntPtr window,previousNeighbor;readonly uint owner;readonly bool wasTopmost;
 bool restored;
 public bool OriginalTopmost {get{return wasTopmost;}}
 public long OriginalPreviousHwnd {get{return previousNeighbor.ToInt64();}}
 public bool Restored {get{return restored;}}
 static bool Topmost(IntPtr h){return (GetWindowLongPtr(h,-20).ToInt64()&8)!=0;}
 static uint Owner(IntPtr h){uint p;GetWindowThreadProcessId(h,out p);return p;}
 KKOwnedWindowLease(IntPtr h,uint pid){window=h;owner=pid;Validate();wasTopmost=Topmost(h);previousNeighbor=GetWindow(h,3);}
 public static KKOwnedWindowLease Acquire(IntPtr h,uint pid) {
  var lease=new KKOwnedWindowLease(h,pid);
  try {
   if(!SetWindowPos(h,new IntPtr(-1),0,0,0,0,0x13))throw new Win32Exception(Marshal.GetLastWin32Error());
   lease.Focus();lease.AssertForeground();return lease;
  }catch{lease.Dispose();throw;}
 }
 void Validate(){if(!IsWindow(window)||Owner(window)!=owner||!IsWindowVisible(window)||IsIconic(window))throw new InvalidOperationException("Explicit game HWND is unavailable, minimized, or no longer owned by the game; stopped.");}
 void Focus(){
  Validate();SetForegroundWindow(window);if(GetForegroundWindow()==window)return;
  MSG m;PeekMessage(out m,IntPtr.Zero,0,0,0);uint ignored;
  uint current=GetCurrentThreadId(),foreground=GetWindowThreadProcessId(GetForegroundWindow(),out ignored),target=GetWindowThreadProcessId(window,out ignored);
  bool joinForeground=false,joinTarget=false;
  try {
   if(foreground!=0&&foreground!=current)joinForeground=AttachThreadInput(current,foreground,true);
   if(target!=0&&target!=current&&target!=foreground)joinTarget=AttachThreadInput(current,target,true);
   BringWindowToTop(window);SetForegroundWindow(window);
  }finally{if(joinTarget)AttachThreadInput(current,target,false);if(joinForeground)AttachThreadInput(current,foreground,false);}
 }
 public void AssertForeground(){Validate();if(GetForegroundWindow()!=window)throw new InvalidOperationException("Game does not own foreground; stopped without sending input to another application.");}
 public PointerEvidence InspectPointer(){POINT p;if(!GetCursorPos(out p))throw new InvalidOperationException("Cannot read cursor position.");IntPtr under=WindowFromPoint(p),front=GetForegroundWindow();return new PointerEvidence{gameHwnd=window.ToInt64(),gamePid=owner,foregroundHwnd=front.ToInt64(),foregroundPid=Owner(front),pointerHwnd=under.ToInt64(),pointerPid=Owner(under),x=p.X,y=p.Y};}
 public PointerEvidence AssertPointer(){AssertForeground();var p=InspectPointer();if(p.pointerPid!=owner)throw new InvalidOperationException("Pointer is obstructed: HWND "+p.pointerHwnd+" belongs to PID "+p.pointerPid+", expected game PID "+owner+". No mouse event sent.");return p;}
 public void Dispose(){
  if(restored)return;
  // A closed/reused handle must never let cleanup affect another process.
  if(!IsWindow(window)||Owner(window)!=owner){restored=true;return;}
  if(!SetWindowPos(window,new IntPtr(wasTopmost?-1:-2),0,0,0,0,0x13))throw new Win32Exception(Marshal.GetLastWin32Error());
  // Reinsert only our HWND after its saved surviving neighbor in the same band.
  if(previousNeighbor!=IntPtr.Zero&&IsWindow(previousNeighbor)&&Topmost(previousNeighbor)==wasTopmost)
   if(!SetWindowPos(window,previousNeighbor,0,0,0,0,0x13))throw new Win32Exception(Marshal.GetLastWin32Error());
  restored=true;
 }
}
'@
}
