Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Drawing
$p = Get-Process EpicGamesLauncher -ErrorAction SilentlyContinue | Where-Object {$_.MainWindowHandle -ne 0} | Select-Object -First 1
if (-not $p) { Get-Process EpicGamesLauncher -ErrorAction SilentlyContinue | Select-Object Id,MainWindowTitle; exit 2 }
$e = [System.Windows.Automation.AutomationElement]::FromHandle($p.MainWindowHandle)
$r=$e.Current.BoundingRectangle
[PSCustomObject]@{Id=$p.Id;Title=$p.MainWindowTitle;X=$r.X;Y=$r.Y;Width=$r.Width;Height=$r.Height}|ConvertTo-Json
$all=$e.FindAll([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.Condition]::TrueCondition)
foreach($c in $all){ if($c.Current.Name -or $c.Current.AutomationId){ [PSCustomObject]@{Name=$c.Current.Name;Id=$c.Current.AutomationId;Type=$c.Current.ControlType.ProgrammaticName;Enabled=$c.Current.IsEnabled;Bounds=$c.Current.BoundingRectangle.ToString()}|ConvertTo-Json -Compress } }
if($r.Width -gt 0 -and $r.Height -gt 0){
$b=New-Object System.Drawing.Bitmap ([int]$r.Width),([int]$r.Height)
$g=[System.Drawing.Graphics]::FromImage($b)
$g.CopyFromScreen([int]$r.X,[int]$r.Y,0,0,$b.Size)
$b.Save('D:\Dev\Krag-Kings\benchmark\unreal\evidence\epic-launcher.png',[System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose();$b.Dispose()
}
