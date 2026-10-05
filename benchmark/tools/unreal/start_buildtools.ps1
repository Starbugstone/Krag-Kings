$ErrorActionPreference='Stop'
$Bootstrap='D:\Dev\Krag-Kings\benchmark\unreal\setup\vs_BuildTools.exe'
$Signature=Get-AuthenticodeSignature $Bootstrap
if($Signature.Status -ne 'Valid' -or $Signature.SignerCertificate.Subject -notmatch 'Microsoft Corporation'){throw 'Unverified installer'}
Start-Process -FilePath $Bootstrap -ArgumentList '--installPath "D:\DevTools\VS2022BuildTools" --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended'
Write-Output 'VS2022 Build Tools setup opened. Installation and legal acceptance not yet verified.'
