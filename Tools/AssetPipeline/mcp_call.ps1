param(
    [Parameter(Mandatory = $true)][string]$Tool,
    [string]$ArgumentsJson = '{}'
)

$ErrorActionPreference = 'Stop'
$endpoint = 'http://127.0.0.1:8000/mcp'
$accept = 'application/json, text/event-stream'
$initialize = @{
    jsonrpc = '2.0'
    id = 1
    method = 'initialize'
    params = @{
        protocolVersion = '2025-06-18'
        capabilities = @{}
        clientInfo = @{ name = 'codex-akm-tools'; version = '1.0' }
    }
} | ConvertTo-Json -Depth 10 -Compress
$response = Invoke-WebRequest -Uri $endpoint -Method Post -ContentType 'application/json' -Headers @{ Accept = $accept } -Body $initialize
$session = [string]$response.Headers['Mcp-Session-Id']
$headers = @{ Accept = $accept; 'Mcp-Session-Id' = $session }
$initialized = @{ jsonrpc = '2.0'; method = 'notifications/initialized'; params = @{} } | ConvertTo-Json -Compress
Invoke-WebRequest -Uri $endpoint -Method Post -ContentType 'application/json' -Headers $headers -Body $initialized | Out-Null

$arguments = $ArgumentsJson | ConvertFrom-Json -AsHashtable
$request = @{ jsonrpc = '2.0'; id = 2; method = 'tools/call'; params = @{ name = $Tool; arguments = $arguments } } | ConvertTo-Json -Depth 30 -Compress
$result = Invoke-WebRequest -Uri $endpoint -Method Post -ContentType 'application/json' -Headers $headers -Body $request
Write-Output $result.Content
