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
        clientInfo = @{ name = 'codex-akm-import'; version = '1.0' }
    }
} | ConvertTo-Json -Depth 10 -Compress
$response = Invoke-WebRequest -Uri $endpoint -Method Post -ContentType 'application/json' -Headers @{ Accept = $accept } -Body $initialize
$session = [string]$response.Headers['Mcp-Session-Id']
Write-Output "SESSION=$session"
Write-Output $response.Content

$headers = @{ Accept = $accept; 'Mcp-Session-Id' = $session }
$initialized = @{ jsonrpc = '2.0'; method = 'notifications/initialized'; params = @{} } | ConvertTo-Json -Compress
Invoke-WebRequest -Uri $endpoint -Method Post -ContentType 'application/json' -Headers $headers -Body $initialized | Out-Null

$list = @{ jsonrpc = '2.0'; id = 2; method = 'tools/call'; params = @{ name = 'list_toolsets'; arguments = @{} } } | ConvertTo-Json -Depth 10 -Compress
$listed = Invoke-WebRequest -Uri $endpoint -Method Post -ContentType 'application/json' -Headers $headers -Body $list
Write-Output $listed.Content
