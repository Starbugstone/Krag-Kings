$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$source=Join-Path $repo 'benchmark\unity\Assets\Benchmark\Editor\LinearScalarMap.cs'
Add-Type -Path $source
$checks=[System.Collections.Generic.List[string]]::new()
function Close([double]$actual,[double]$expected,[string]$label){
 if([Math]::Abs($actual-$expected) -gt 0.0000001){throw ($label+': expected '+$expected+', actual '+$actual)}
}
$constant=[KragKings.Editor.LinearScalarMap]::new([float[]]@(0.375,0.375,0.375,0.375),2,2)
foreach($point in @(@(0,0),@(3,2),@(7,5))){Close ($constant.AtOutputTexel($point[0],$point[1],8,6)) .375 'constant expansion'}
if(-not $constant.IsConstant){throw 'Constant map was not recognized'}
$checks.Add('Constant scalar expansion preserves exact value at larger target dimensions')
$gradient=[KragKings.Editor.LinearScalarMap]::new([float[]]@(0,.25,.5,.75),2,2)
Close ($gradient.AtOutputTexel(1,1,4,4)) .1875 'two-dimensional gradient first interior'
Close ($gradient.AtOutputTexel(2,2,4,4)) .5625 'two-dimensional gradient second interior'
Close ($gradient.AtOutputTexel(0,0,4,4)) 0 'lower atlas boundary'
Close ($gradient.AtOutputTexel(3,3,4,4)) .75 'upper atlas boundary'
$checks.Add('Bilinear pixel-center sampling preserves a nonconstant 2D gradient and clamps atlas edges')
Close ($gradient.AtOutputTexel(0,1,2,2)) .5 'equal-size exact sampling'
Close ($gradient.AtOutputTexel(0,0,1,1)) .375 'downsampled center'
$checks.Add('Existing equal-size values and nonconstant downsampled center remain correct')
$row=[KragKings.Editor.LinearScalarMap]::new([float[]]@(0,1),2,1)
Close ($row.AtOutputTexel(1,4,4,7)) .25 'single-row interpolation'
$checks.Add('Single-row source safely resizes both axes')
$rejected=$false
try{$null=[KragKings.Editor.LinearScalarMap]::new([float[]]@(0,1),2,2)}catch{$rejected=$true}
if(-not $rejected){throw 'Invalid dimension/sample contract was accepted'}
$checks.Add('Mismatched source dimensions are rejected')
$report=[ordered]@{scope='Actual production scalar sampler compiled outside Unity; no texture import or rendering';passed=$true;checks=@($checks);sourceSha256=(Get-FileHash $source -Algorithm SHA256).Hash.ToLower();unityImportExecuted=$false}
$output=Join-Path $repo 'benchmark\local\evidence\unity-scalar-packing'
New-Item -ItemType Directory -Force $output|Out-Null
$report|ConvertTo-Json -Depth 5|Set-Content -Encoding UTF8 (Join-Path $output 'result.json')
Write-Output 'SCALAR_PACKING_CHECK_PASS 5 cases'
