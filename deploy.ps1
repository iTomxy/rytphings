# RUN: .\deploy.ps1

$rime = "$env:APPDATA\Rime"
$rimeBase = "$env:USERPROFILE\Programs\Rime"

Get-ChildItem "$rimeBase\weasel-*" -Directory | Where-Object { !(Get-ChildItem $_.FullName) } | Remove-Item
$rimeBin = (Get-ChildItem "$rimeBase\weasel-*" -Directory)[-1].FullName

Copy-Item "rytphings.*.yaml" $rime
& "$rimeBin\WeaselDeployer.exe" /deploy
