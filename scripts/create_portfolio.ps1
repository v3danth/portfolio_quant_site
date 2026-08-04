param(
    [int]$UserId = 1,
    [string]$PortfolioName = "My Portfolio",
    [string]$ApiUrl = "http://127.0.0.1:8000"
)

$endpoint = "$ApiUrl/api/v1/portfolios"
$body = @{
    user_id = $UserId
    name = $PortfolioName
} | ConvertTo-Json

Write-Host "Creating portfolio: $PortfolioName for user $UserId"
Write-Host "Endpoint: $endpoint"
Write-Host "Body: $body"

$response = curl -X POST $endpoint `
    -H "Content-Type: application/json" `
    -d $body

Write-Host "Response:"
$response | ConvertFrom-Json | ConvertTo-Json -Depth 10
