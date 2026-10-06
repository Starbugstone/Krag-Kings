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
        [Serializable] public struct DiagnosticEdge
        {
            public string utc,deviceKind,eventType,updateType;
            public int frame,eventId,deviceId,keyboardDeviceId;
            public uint inputUpdateCount;
            public double eventTime;
            public float leftShiftBefore,rightShiftBefore,leftShiftEvent,rightShiftEvent,rightButtonBefore,rightButtonEvent;
            public bool hasLeftShift,hasRightShift,hasRightButton,leftShiftPressedBefore,rightShiftPressedBefore;
            public Vector2 eventPosition,currentPosition;
        }
        readonly Queue<Press> pending=new();
        readonly Queue<DiagnosticEdge> diagnosticEdges=new();
        readonly Func<bool> acceptEvents;
        readonly IDisposable mergingLease;
        readonly bool recordDiagnostics,captureMovement;
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

        public DemoMovePressQueue(Func<bool> acceptEvents,bool recordDiagnostics=false,bool captureMovement=true)
        {
            this.acceptEvents=acceptEvents??throw new ArgumentNullException(nameof(acceptEvents));
            this.recordDiagnostics=recordDiagnostics;
            this.captureMovement=captureMovement;
            mergingLease=captureMovement?AcquirePressPositionLease():null;
            InputSystem.onEvent+=OnEvent;
            InputSystem.onDeviceChange+=OnDeviceChange;
        }
        public bool TryDequeue(out Press press)=>pending.TryDequeue(out press);
        public DiagnosticEdge[] SnapshotDiagnosticEdges()=>diagnosticEdges.ToArray();
        public void Clear()=>pending.Clear();

        void RecordDiagnostic(InputEventPtr input,InputDevice device)
        {
            if(!recordDiagnostics||input.handled||!device.enabled||(!input.IsA<StateEvent>()&&!input.IsA<DeltaStateEvent>()))return;
            var keyboard=Keyboard.current;
            var edge=new DiagnosticEdge {utc=DateTime.UtcNow.ToString("o"),frame=Time.frameCount,eventId=input.id,eventTime=input.time,deviceId=device.deviceId,
                eventType=input.type.ToString(),updateType=InputState.currentUpdateType.ToString(),inputUpdateCount=InputState.updateCount,keyboardDeviceId=keyboard?.deviceId??0,
                leftShiftBefore=keyboard?.leftShiftKey.ReadValue()??0,rightShiftBefore=keyboard?.rightShiftKey.ReadValue()??0,
                leftShiftPressedBefore=keyboard?.leftShiftKey.isPressed??false,rightShiftPressedBefore=keyboard?.rightShiftKey.isPressed??false};
            if(device is Keyboard keys)
            {
                edge.deviceKind="KeyboardShift";
                edge.hasLeftShift=keys.leftShiftKey.ReadValueFromEvent(input,out edge.leftShiftEvent);
                edge.hasRightShift=keys.rightShiftKey.ReadValueFromEvent(input,out edge.rightShiftEvent);
                if(!(edge.hasLeftShift&&edge.leftShiftEvent!=keys.leftShiftKey.ReadValue())&&!(edge.hasRightShift&&edge.rightShiftEvent!=keys.rightShiftKey.ReadValue()))return;
            }
            else if(device is Mouse pointer)
            {
                edge.deviceKind="MouseRightButton";edge.rightButtonBefore=pointer.rightButton.ReadValue();
                edge.hasRightButton=pointer.rightButton.ReadValueFromEvent(input,out edge.rightButtonEvent);
                if(!edge.hasRightButton||edge.rightButtonEvent==edge.rightButtonBefore)return;
                edge.currentPosition=pointer.position.ReadValue();
                edge.eventPosition=pointer.position.ReadValueFromEvent(input,out Vector2 position)?position:edge.currentPosition;
            }
            else return;
            if(diagnosticEdges.Count==48)diagnosticEdges.Dequeue();
            diagnosticEdges.Enqueue(edge);
        }

        void OnEvent(InputEventPtr input,InputDevice device)
        {
            if(disposed||!acceptEvents()) {pending.Clear();return;}
            RecordDiagnostic(input,device);
            if(!captureMovement)return;
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
            mergingLease?.Dispose();
        }
    }
}
