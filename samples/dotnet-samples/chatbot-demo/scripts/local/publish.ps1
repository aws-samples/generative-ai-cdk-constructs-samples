# Navigate to root of repo
Push-Location -Path $PSScriptRoot\..\..

$PublishDirectory="$PWD\dist"
$AppDirectory="$PWD\src"

Remove-Item $PublishDirectory -r -Force

Push-Location "$AppDirectory\ChatbotDemo"
dotnet publish -c Release -r linux-x64 -p:Version=2.0.0.0 --no-self-contained -o $PublishDirectory/release/publish/ChatbotDemo

Write-Output '\nListing published files\n'
Get-ChildItem $PublishDirectory/release/publish/ChatbotDemo
Pop-Location
