# PowerShell script to provide HuggingFace credentials to Git
param([string]$prompt)

# For username prompt
if ($prompt -like "*Username*") {
    Write-Host "Srinivas989"
}
# For password prompt
elseif ($prompt -like "*Password*") {
    # Read token from huggingface
    $tokenPath = "$env:USERPROFILE\.huggingface\token"
    if (Test-Path $tokenPath) {
        $token = Get-Content $tokenPath | Out-String
        Write-Host $token.Trim()
    } else {
        Write-Error "HuggingFace token not found at $tokenPath"
        exit 1
    }
}
