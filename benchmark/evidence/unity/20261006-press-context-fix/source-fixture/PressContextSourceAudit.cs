using System;using System.Collections.Generic;
public static class KKPressContextSourceAudit {
 public class Device {public uint m_CurrentUpdateStepCount=1;}
 public class WarmedButton {
  public Device device=new Device();public float value;
  internal bool m_LastUpdateWasPress; internal uint m_UpdateCountLastPressed,m_UpdateCountLastReleased;
  bool IsValueConsideredPressed(float x){return x>=.5f;}
  public bool isPressed {get{return m_LastUpdateWasPress;}}
  public bool wasPressedThisFrame {get{return device.m_CurrentUpdateStepCount==m_UpdateCountLastPressed;}}
internal void UpdateWasPressed()
        {
            var isNowPressed = IsValueConsideredPressed(value);

            if (m_LastUpdateWasPress != isNowPressed)
            {
                if (isNowPressed)
                    m_UpdateCountLastPressed = device.m_CurrentUpdateStepCount;
                else
                    m_UpdateCountLastReleased = device.m_CurrentUpdateStepCount;

                m_LastUpdateWasPress = isNowPressed;
            }
        }
 }
 public class Intent {public bool walk;public float x,y;}
 public class EventSequence {
  public bool left,right;public float pointerX,pointerY;
  public WarmedButton button=new WarmedButton();public List<Intent> queue=new List<Intent>();
  public void Shift(bool isRight,bool down){if(isRight)right=down;else left=down;}
  public void Mouse(bool down,bool hasPosition,float x,float y){
   // Model the installed callback-before-state-update ordering. This fixture
   // does not load Unity, call InputSystem APIs, or send native OS input.
   if(down&&!button.isPressed)queue.Add(new Intent{walk=left||right,x=hasPosition?x:pointerX,y=hasPosition?y:pointerY});
   if(hasPosition){pointerX=x;pointerY=y;}
   button.value=down?1:0;button.UpdateWasPressed();
  }
  public void FocusLost(){queue.Clear();left=right=false;button.value=0;button.UpdateWasPressed();}
 }
 public class Result {public string name;public bool pollingEmitsMove,pollingWalk;public Intent[] queued;public bool passed;}
 static Result Capture(string name,EventSequence x,bool expectedPollingWalk,params bool[] expectedWalks){
  bool ok=x.button.wasPressedThisFrame && (x.left||x.right)==expectedPollingWalk && x.queue.Count==expectedWalks.Length;
  for(int i=0;i<x.queue.Count&&i<expectedWalks.Length;i++)ok&=x.queue[i].walk==expectedWalks[i];
  return new Result{name=name,pollingEmitsMove=x.button.wasPressedThisFrame,pollingWalk=x.left||x.right,queued=x.queue.ToArray(),passed=ok};
 }
 public static Result[] Run(){
  var results=new List<Result>();
  foreach(bool side in new[]{false,true}){
   var x=new EventSequence();x.Shift(side,true);x.Mouse(true,true,100,200);x.Mouse(false,false,0,0);x.Shift(side,false);
   results.Add(Capture(side?"Right Shift released in same update":"Left Shift released in same update",x,false,true));
  }
  {var x=new EventSequence();x.Shift(false,true);x.Mouse(true,true,100,200);x.Mouse(false,false,0,0);x.Shift(false,false);x.Mouse(true,true,300,400);x.Mouse(false,false,0,0);x.Shift(true,true);x.Mouse(true,true,500,600);x.Mouse(false,false,0,0);x.Shift(true,false);results.Add(Capture("Three presses in one update preserve Walk/Run/Walk",x,false,true,false,true));}
  {var x=new EventSequence();x.pointerX=25;x.pointerY=50;x.Shift(false,true);x.Mouse(true,false,0,0);x.Mouse(true,true,900,950);x.Mouse(false,false,0,0);x.Shift(false,false);var r=Capture("Button delta uses prior pointer; later motion does not change queued target",x,false,true);r.passed&=r.queued[0].x==25&&r.queued[0].y==50;results.Add(r);}
  {var x=new EventSequence();x.Shift(true,true);x.Mouse(true,true,100,200);x.FocusLost();results.Add(new Result{name="Focus loss clears pending intent and held-state model",pollingEmitsMove=x.button.wasPressedThisFrame,pollingWalk=x.left||x.right,queued=x.queue.ToArray(),passed=x.queue.Count==0&&!x.left&&!x.right&&!x.button.isPressed});}
  foreach(var r in results)if(!r.passed)throw new Exception("Source-derived fixture failed: "+r.name);
  return results.ToArray();
 }
}
