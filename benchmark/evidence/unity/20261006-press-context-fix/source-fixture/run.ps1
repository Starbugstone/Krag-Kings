$ErrorActionPreference='Stop'
Add-Type -Path (Join-Path $PSScriptRoot 'PressContextSourceAudit.cs')
$cases=[KKPressContextSourceAudit]::Run()
@{checkedUtc=[DateTime]::UtcNow.ToString('o');scope='Source-derived digital button/event-order fixture';passed=$true;caseCount=$cases.Length;cases=$cases;inputSystemPackage='1.19.0';actualUnityRuntimeExecuted=$false;nativeInputSent=$false;gameplayCodeChanged=$false;assumption='Button frame tracking already initialized by prior polls, as in the warmed demo.';limits='Uses the exact extracted UpdateWasPressed method with minimal value/device stubs; it does not execute the Unity Input System event backend.';fixtureSha256=(Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $PSScriptRoot 'PressContextSourceAudit.cs')).Hash.ToLower()}|ConvertTo-Json -Depth 8|Set-Content -Encoding UTF8 (Join-Path $PSScriptRoot 'result.json')
Write-Output 'PRESS_CONTEXT_SOURCE_FIXTURE_PASS'
