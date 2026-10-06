using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.LowLevel;

namespace KragKings.Benchmark
{
    // Input System invokes onEvent before applying that event to device state.
    // Retain each press before later pointer/Shift events replace its context.
    public sealed class DemoMovePressQueue : IDisposable
    {
        [Serializable] public struct Press
        {
            public Vector2 position;
            public bool walk;
            public int mouseDeviceId,eventId;
            public double eventTime;
        }
        readonly Queue<Press> pending=new();
        readonly Func<bool> acceptEvents;
        readonly IDisposable mergingLease;
        bool disposed;

        sealed class LeaseState {public int users;public bool original;}
        static readonly Dictionary<InputSettings,LeaseState> mergingLeases=new();
        sealed class MergingLease : IDisposable
        {
            InputSettings settings;
            public MergingLease()
            {
                settings=InputSystem.settings;
                if(!mergingLeases.TryGetValue(settings,out var state))
                {
                    state=new LeaseState {original=settings.disableRedundantEventsMerging};
                    mergingLeases.Add(settings,state);
                }
                ++state.users;
                // FastMouse can merge a first-event press with a later held
                // report before onEvent, replacing its original cursor.
                settings.disableRedundantEventsMerging=true;
            }
            public void Dispose()
            {
                if(settings==null)return;
                var owned=settings;settings=null;
                if(--mergingLeases[owned].users!=0)return;
                bool original=mergingLeases[owned].original;mergingLeases.Remove(owned);
                owned.disableRedundantEventsMerging=original;
            }
        }
        public static IDisposable AcquirePressPositionLease()=>new MergingLease();

        public DemoMovePressQueue(Func<bool> acceptEvents)
        {
            this.acceptEvents=acceptEvents??throw new ArgumentNullException(nameof(acceptEvents));
            mergingLease=AcquirePressPositionLease();
            InputSystem.onEvent+=OnEvent;
            InputSystem.onDeviceChange+=OnDeviceChange;
        }
        public bool TryDequeue(out Press press)=>pending.TryDequeue(out press);
        public void Clear()=>pending.Clear();

        void OnEvent(InputEventPtr input,InputDevice device)
        {
            if(disposed||!acceptEvents()) {pending.Clear();return;}
            if(input.handled||!device.enabled||device is not Mouse mouse ||
                (!input.IsA<StateEvent>()&&!input.IsA<DeltaStateEvent>()))return;
            if(!mouse.rightButton.ReadValueFromEvent(input,out float value) ||
                value<mouse.rightButton.pressPointOrDefault||mouse.rightButton.isPressed)return;
            Vector2 position=mouse.position.ReadValueFromEvent(input,out Vector2 eventPosition)
                ?eventPosition:mouse.position.ReadValue();
            var keyboard=Keyboard.current;
            pending.Enqueue(new Press {
                position=position,
                walk=keyboard!=null&&keyboard.enabled&&(keyboard.leftShiftKey.isPressed||keyboard.rightShiftKey.isPressed),
                mouseDeviceId=mouse.deviceId,eventId=input.id,eventTime=input.time
            });
        }
        void OnDeviceChange(InputDevice device,InputDeviceChange change)
        {
            if(device is not Mouse && device is not Keyboard)return;
            if(change==InputDeviceChange.Removed||change==InputDeviceChange.Disconnected||
                change==InputDeviceChange.Disabled||change==InputDeviceChange.SoftReset||change==InputDeviceChange.HardReset)
                pending.Clear();
        }
        public void Dispose()
        {
            if(disposed)return;
            disposed=true;pending.Clear();
            InputSystem.onEvent-=OnEvent;
            InputSystem.onDeviceChange-=OnDeviceChange;
            mergingLease.Dispose();
        }
    }
}
