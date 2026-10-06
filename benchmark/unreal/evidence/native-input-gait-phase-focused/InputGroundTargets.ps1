# Pure projection/selection helpers; sourcing this file sends no Windows input.
function Project-KKWorldPoint($Camera,[double[]]$Point,[int]$Width,[int]$Height) {
 $yaw=[double]$Camera.yaw*[Math]::PI/180;$pitch=[double]$Camera.pitch*[Math]::PI/180
 $cy=[Math]::Cos($yaw);$sy=[Math]::Sin($yaw);$cp=[Math]::Cos($pitch);$sp=[Math]::Sin($pitch)
 $dx=$Point[0]-$Camera.x;$dy=$Point[1]-$Camera.y;$dz=$Point[2]-$Camera.z
 $depth=$dx*$cp*$cy+$dy*$cp*$sy+$dz*$sp
 if($depth -le 1){return $null}
 $focal=$Width/(2*[Math]::Tan(62.9448*[Math]::PI/360))
 [pscustomobject]@{x=$Width*.5+(-$dx*$sy+$dy*$cy)*$focal/$depth;y=$Height*.5-(-$dx*$sp*$cy-$dy*$sp*$sy+$dz*$cp)*$focal/$depth;depth=$depth}
}
function Test-KKSegmentBox([double[]]$Start,[double[]]$End,[double[]]$Center,[double[]]$Extent) {
 $near=0.0;$far=1.0
 for($axis=0;$axis -lt 3;$axis++){
  $delta=$End[$axis]-$Start[$axis];$low=$Center[$axis]-$Extent[$axis];$high=$Center[$axis]+$Extent[$axis]
  if([Math]::Abs($delta) -lt .000001){if($Start[$axis] -lt $low -or $Start[$axis] -gt $high){return $false};continue}
  $a=($low-$Start[$axis])/$delta;$b=($high-$Start[$axis])/$delta
  $near=[Math]::Max($near,[Math]::Min($a,$b));$far=[Math]::Min($far,[Math]::Max($a,$b))
  if($near -gt $far){return $false}
 }
 return $true
}
function Get-KKGroundClickTarget($State,[int]$Width,[int]$Height) {
 if($State.portrait){throw 'Ground-input probe requires the observed wide camera.'}
 $selected=$State.units|Where-Object selected
 if(-not $selected){throw 'Ground-input probe has no selected unit.'}
 $projectionErrors=@()
 foreach($unit in $State.units){
  $point=Project-KKWorldPoint $State.camera @($unit.x,$unit.y,$unit.z) $Width $Height
  if(-not $point){throw 'Observed unit projects behind the camera.'}
  $error=[Math]::Sqrt([Math]::Pow($point.x-$unit.screen_x,2)+[Math]::Pow($point.y-$unit.screen_y,2));$projectionErrors+=$error
  if($error -gt 2){throw "Runtime camera projection adapter disagrees by $error pixels; no click sent."}
 }
 $best=$null;$bestScore=[double]::MaxValue
 foreach($distance in @(140,190,240)){
  for($index=0;$index -lt 24;$index++){
   $angle=$index*[Math]::PI/12;$x=[double]$selected.x+$distance*[Math]::Cos($angle);$y=[double]$selected.y+$distance*[Math]::Sin($angle)
   if([Math]::Abs($x) -gt 3900 -or [Math]::Abs($y) -gt 3900){continue}
   # Predict the validated central dune height; the actual game trace accepts it.
   $sx=$x*.01;$sy=-$y*.01
   $z=100*(.8+1.1*[Math]::Sin(.105*$sx+.035*$sy)+.65*[Math]::Sin(.055*$sx-.145*$sy)+.30*[Math]::Cos(.22*$sx+.13*$sy))
   $target=@($x,$y,$z);$screen=Project-KKWorldPoint $State.camera $target $Width $Height
   if(-not $screen -or $screen.x -lt 70 -or $screen.x -gt ($Width-70) -or $screen.y -lt 125 -or $screen.y -gt ($Height-120)){continue}
   $blocked=$false
   foreach($unit in $State.units){
    $radius=if($unit.species -eq 'Krag'){47.0}else{29.0};$selectedRadius=if($selected.species -eq 'Krag'){47.0}else{29.0}
    if(-not $unit.selected){
     $vx=$x-$selected.x;$vy=$y-$selected.y
     $t=[Math]::Max(0,[Math]::Min(1,(($unit.x-$selected.x)*$vx+($unit.y-$selected.y)*$vy)/($vx*$vx+$vy*$vy)))
     $separation=[Math]::Sqrt([Math]::Pow($selected.x+$t*$vx-$unit.x,2)+[Math]::Pow($selected.y+$t*$vy-$unit.y,2))
     if($separation -lt ($radius+$selectedRadius+15)){$blocked=$true;break}
    }
    # Conservative bounds include arms/gear as well as the selection capsule.
    $extent=if($unit.species -eq 'Krag'){@(85,85,120)}else{@(48,48,82)}
    if(Test-KKSegmentBox @($State.camera.x,$State.camera.y,$State.camera.z) $target @($unit.x,$unit.y,$unit.z) $extent){$blocked=$true;break}
   }
   if($blocked){continue}
   $score=[Math]::Abs($screen.x-$Width*.5)+[Math]::Abs($screen.y-$Height*.70)+$distance*.1
   if($score -lt $bestScore){$bestScore=$score;$best=[pscustomobject]@{worldCentimeters=$target;clientPoint=@($screen.x,$screen.y);projectionErrorsPixels=$projectionErrors;distanceFromSelectedCm=$distance;method='Observed camera checked against actual projected unit centers; predicted dune height; footprint/path and conservative unit occlusion exclusion. Actual game terrain trace remains authoritative.'}}
  }
 }
 if(-not $best){throw 'No visible unoccupied ground target survived checks; no click sent.'}
 return $best
}
