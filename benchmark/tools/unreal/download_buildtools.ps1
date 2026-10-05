$ErrorActionPreference='Stop'
$TaskSetupDir='D:\Dev\Krag-Kings\benchmark\unreal\setup'
New-Item -ItemType Directory -Force -Path $TaskSetupDir | Out-Null
$TaskBootstrap=Join-Path $TaskSetupDir 'vs_BuildTools.exe'
Invoke-WebRequest -UseBasicParsing -Uri 'https://aka.ms/vs/17/release/vs_BuildTools.exe' -OutFile $TaskBootstrap
$Sig=Get-AuthenticodeSignature $TaskBootstrap
[PSCustomObject]@{Path=$TaskBootstrap;Status=$Sig.Status.ToString();Signer=$Sig.SignerCertificate.Subject;Bytes=(Get-Item $TaskBootstrap).Length}|ConvertTo-Json
if($Sig.Status -ne 'Valid' -or $Sig.SignerCertificate.Subject -notmatch 'Microsoft Corporation'){throw 'Installer signature is not verified Microsoft.'}
