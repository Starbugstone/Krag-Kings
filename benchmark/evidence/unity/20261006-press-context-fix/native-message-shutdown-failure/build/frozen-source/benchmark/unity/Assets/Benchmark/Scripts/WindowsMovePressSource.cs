using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;

namespace KragKings.Benchmark
{
    // Windows owns the press-time modifier and client coordinates in this
    // message. Input System's native keyboard/mouse queues can reorder them.
    // https://learn.microsoft.com/windows/win32/inputdev/wm-rbuttondown
    public sealed class WindowsMovePressSource : IDisposable
    {
        [Serializable] public struct Press
        {
            public int sequence,clientX,clientY,clientWidth,clientHeight,messageTimeMilliseconds;
            public uint message,flags;
            public bool walk;
            public string utc;
        }
        public static bool Supported
        {
            get {
#if UNITY_STANDALONE_WIN && !UNITY_EDITOR
                return true;
#else
                return false;
#endif
            }
        }
        [StructLayout(LayoutKind.Sequential)] struct Rect {public int left,top,right,bottom;}
        [UnmanagedFunctionPointer(CallingConvention.Winapi)] delegate IntPtr WindowProc(IntPtr hwnd,uint message,UIntPtr wParam,IntPtr lParam);
        [UnmanagedFunctionPointer(CallingConvention.Winapi)] delegate bool EnumProc(IntPtr hwnd,IntPtr data);
        [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc callback,IntPtr data);
        [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr hwnd,out uint process);
        [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern int GetClassNameW(IntPtr hwnd,StringBuilder name,int count);
        [DllImport("user32.dll")] static extern bool IsWindow(IntPtr hwnd);
        [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr hwnd);
        [DllImport("user32.dll")] static extern bool GetClientRect(IntPtr hwnd,out Rect rect);
        [DllImport("user32.dll")] static extern IntPtr GetForegroundWindow();
        [DllImport("user32.dll")] static extern int GetMessageTime();
        [DllImport("kernel32.dll")] static extern uint GetCurrentProcessId();
        [DllImport("kernel32.dll")] static extern void SetLastError(uint error);
        [DllImport("user32.dll",EntryPoint="GetWindowLongPtrW",SetLastError=true)] static extern IntPtr GetWindowLongPtr(IntPtr hwnd,int index);
        [DllImport("user32.dll",EntryPoint="SetWindowLongPtrW",SetLastError=true)] static extern IntPtr SetWindowLongPtr(IntPtr hwnd,int index,IntPtr value);
        [DllImport("user32.dll",EntryPoint="CallWindowProcW")] static extern IntPtr CallWindowProc(IntPtr previous,IntPtr hwnd,uint message,UIntPtr wParam,IntPtr lParam);
        const int ProcedureIndex=-4;
        const uint RightDown=0x0204,RightDoubleClick=0x0206,NonClientDestroy=0x0082;
        static readonly object ownersGate=new();
        // Roots delegates until safely detached, including a later subclass
        // that interposes above ours. Never overwrite another subclass chain.
        static readonly Dictionary<IntPtr,WindowsMovePressSource> owners=new();
        readonly object gate=new();
        readonly Queue<Press> pending=new(),history=new();
        readonly WindowProc callback;
        readonly IntPtr window,callbackPointer;
        readonly uint process;
        readonly bool recordDiagnostics;
        IntPtr previous;
        volatile bool enabled=true,disposed;
        int sequence;
        string callbackError;
        public bool Restored {get;private set;}
        public bool RestorationDeferred {get;private set;}
        public long WindowHandle=>window.ToInt64();
        public long OriginalProcedure=>previous.ToInt64();
        public long HookProcedure=>callbackPointer.ToInt64();
        public long ProcedureAfterDispose {get;private set;}
        public string CallbackError {get{lock(gate)return callbackError;}}

        public WindowsMovePressSource(bool recordDiagnostics)
        {
            if(!Supported||IntPtr.Size!=8)throw new PlatformNotSupportedException("The native movement source requires a Windows 64-bit player.");
            this.recordDiagnostics=recordDiagnostics;process=GetCurrentProcessId();
            IntPtr found=IntPtr.Zero;
            EnumWindows((hwnd,unused)=>{
                GetWindowThreadProcessId(hwnd,out uint pid);
                if(pid!=process||!IsWindowVisible(hwnd))return true;
                var name=new StringBuilder(128);GetClassNameW(hwnd,name,name.Capacity);
                if(name.ToString()!="UnityWndClass"||!GetClientRect(hwnd,out var rect)||rect.right<=rect.left||rect.bottom<=rect.top)return true;
                found=hwnd;return false;
            },IntPtr.Zero);
            if(found==IntPtr.Zero)throw new InvalidOperationException("No visible Unity game window belongs to this process.");
            window=found;callback=HandleMessage;callbackPointer=Marshal.GetFunctionPointerForDelegate(callback);
            lock(ownersGate)
            {
                if(owners.ContainsKey(window))throw new InvalidOperationException("This game window already has a movement source.");
                previous=GetWindowLongPtr(window,ProcedureIndex);
                if(previous==IntPtr.Zero)throw new InvalidOperationException("The owned game window has no procedure to preserve.");
                owners.Add(window,this);
                SetLastError(0);var replaced=SetWindowLongPtr(window,ProcedureIndex,callbackPointer);
                if(replaced==IntPtr.Zero)
                {
                    owners.Remove(window);
                    throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error(),"Cannot attach the owned-window movement source.");
                }
                previous=replaced;
            }
        }
        public void SetEnabled(bool value){enabled=value;if(!value)Clear();}
        public void Clear(){lock(gate)pending.Clear();}
        public bool TryDequeue(out Press press){lock(gate)return pending.TryDequeue(out press);}
        public Press[] SnapshotHistory(){lock(gate)return history.ToArray();}
        IntPtr HandleMessage(IntPtr hwnd,uint message,UIntPtr wParam,IntPtr lParam)
        {
            // This callback uses only Win32 and thread-safe managed values.
            // Every message still reaches Unity's original procedure.
            try
            {
                if(message==0x0008||message==0x001F||message==0x0219||(message==0x001C&&wParam==UIntPtr.Zero))Clear();
                if(!disposed&&enabled&&hwnd==window&&(message==RightDown||message==RightDoubleClick)&&GetForegroundWindow()==window)
                {
                    GetWindowThreadProcessId(window,out uint owner);
                    if(owner==process&&GetClientRect(window,out var rect)&&rect.right>rect.left&&rect.bottom>rect.top)
                    {
                        long coordinates=lParam.ToInt64();uint flags=(uint)wParam.ToUInt64();
                        var press=new Press {sequence=++sequence,clientX=unchecked((short)(coordinates&0xffff)),clientY=unchecked((short)((coordinates>>16)&0xffff)),
                            clientWidth=rect.right-rect.left,clientHeight=rect.bottom-rect.top,walk=(flags&0x0004)!=0,flags=flags,message=message,
                            messageTimeMilliseconds=GetMessageTime(),utc=recordDiagnostics?DateTime.UtcNow.ToString("o"):null};
                        lock(gate){pending.Enqueue(press);if(recordDiagnostics){if(history.Count==48)history.Dequeue();history.Enqueue(press);}}
                    }
                }
            }
            catch(Exception error){lock(gate)callbackError=error.GetType().Name+": "+error.Message;}
            IntPtr result=CallWindowProc(previous,hwnd,message,wParam,lParam);
            if(message==NonClientDestroy){disposed=true;enabled=false;Clear();lock(ownersGate)owners.Remove(window);Restored=true;RestorationDeferred=false;}
            return result;
        }
        public void Dispose()
        {
            if(disposed)return;
            disposed=true;enabled=false;Clear();
            lock(ownersGate)
            {
                GetWindowThreadProcessId(window,out uint owner);
                if(!IsWindow(window)||owner!=process){owners.Remove(window);Restored=true;return;}
                if(GetWindowLongPtr(window,ProcedureIndex)!=callbackPointer){RestorationDeferred=true;return;}
                SetLastError(0);var old=SetWindowLongPtr(window,ProcedureIndex,previous);
                if(old==IntPtr.Zero){RestorationDeferred=true;throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error(),"Cannot restore the owned game window procedure.");}
                if(old!=callbackPointer)
                {
                    // A concurrent subclass interposed after our comparison.
                    // Restore that chain and keep our disabled delegate alive.
                    SetWindowLongPtr(window,ProcedureIndex,old);RestorationDeferred=true;return;
                }
                ProcedureAfterDispose=GetWindowLongPtr(window,ProcedureIndex).ToInt64();
                owners.Remove(window);Restored=ProcedureAfterDispose==previous.ToInt64();
            }
        }
    }
}
