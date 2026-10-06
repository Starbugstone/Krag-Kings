# Lightweight source compilation using the exact compiler/references from this
# project's last real Unity compilation. Does not mutate Unity's cache or import assets.
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$project=Join-Path $repo 'benchmark\unity'
$output=Join-Path $repo 'benchmark\local\unity-source-check'
New-Item -ItemType Directory -Force $output | Out-Null
$editorResponse=Get-ChildItem (Join-Path $project 'Library\Bee\artifacts') -Filter 'Assembly-CSharp-Editor.rsp' -Recurse | Sort-Object LastWriteTime -Descending | Select-Object -First 1
$runtimeResponse=if($editorResponse){Get-Item (Join-Path $editorResponse.DirectoryName 'Assembly-CSharp.rsp')}
if(-not $runtimeResponse){throw 'Run a real Unity compilation first to establish matching references.'}
$compiler='D:\Unity\Hub\6000.4.4f1\Editor\Data\DotNetSdkRoslyn\csc.dll'
$dotnet='D:\Unity\Hub\6000.4.4f1\Editor\Data\NetCoreRuntime\dotnet.exe'
Push-Location $project
try {
    foreach($assembly in @('Assembly-CSharp','Assembly-CSharp-Editor')){
        $inputPath=Join-Path $runtimeResponse.DirectoryName ($assembly+'.rsp')
        $text=Get-Content -Raw $inputPath
        $text=[regex]::Replace($text,'(?m)^-out:.*$',('-out:"'+(Join-Path $output ($assembly+'.dll'))+'"'))
        $text=[regex]::Replace($text,'(?m)^-refout:.*$',('-refout:"'+(Join-Path $output ($assembly+'.ref.dll'))+'"'))
        if($assembly -eq 'Assembly-CSharp-Editor'){
            $text=[regex]::Replace($text,'(?m)^-r:"[^"]*/Assembly-CSharp\.ref\.dll"\r?$',('-r:"'+(Join-Path $output 'Assembly-CSharp.ref.dll')+'"'))
        }
        $text=[regex]::Replace($text,'(?m)^"[^"\r\n]+\.cs"\r?\n','')
        $isEditor=$assembly -eq 'Assembly-CSharp-Editor'
        $sources=Get-ChildItem (Join-Path $project 'Assets') -Filter '*.cs' -Recurse | Where-Object {($_.FullName.Replace('\','/').Contains('/Editor/')) -eq $isEditor}
        foreach($source in $sources){$text+="`n"+'"'+$source.FullName+'"'}
        $response=Join-Path $output ($assembly+'.rsp')
        [IO.File]::WriteAllText($response,$text)
        & $dotnet exec $compiler /nostdlib /noconfig ('@'+$response) 2>&1 | Tee-Object (Join-Path $output ($assembly+'.log'))
        if($LASTEXITCODE -ne 0){throw ($assembly+' source compilation failed')}
        Write-Output ('SOURCE_COMPILE_OK '+$assembly)
    }
} finally {Pop-Location}
