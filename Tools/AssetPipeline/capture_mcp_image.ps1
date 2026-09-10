param(
    [Parameter(Mandatory = $true)][string]$OutputPath,
    [string]$Ref = ''
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
        clientInfo = @{ name = 'codex-screenshot-tools'; version = '1.0' }
    }
} | ConvertTo-Json -Depth 10 -Compress

$response = Invoke-WebRequest -Uri $endpoint -Method Post -ContentType 'application/json' -Headers @{ Accept = $accept } -Body $initialize
$session = [string]$response.Headers['Mcp-Session-Id']
$headers = @{ Accept = $accept; 'Mcp-Session-Id' = $session }
$initialized = @{ jsonrpc = '2.0'; method = 'notifications/initialized'; params = @{} } | ConvertTo-Json -Compress
Invoke-WebRequest -Uri $endpoint -Method Post -ContentType 'application/json' -Headers $headers -Body $initialized | Out-Null

$request = @{
    jsonrpc = '2.0'
    id = 2
    method = 'tools/call'
    params = @{
        name = 'call_tool'
        arguments = @{
            toolset_name = 'SlateInspectorToolset.SlateInspectorToolset'
            tool_name = 'Screenshot'
            arguments = @{ Ref = $Ref }
        }
    }
} | ConvertTo-Json -Depth 20 -Compress

$result = Invoke-WebRequest -Uri $endpoint -Method Post -ContentType 'application/json' -Headers $headers -Body $request
$payload = $result.Content | ConvertFrom-Json
$imageBlock = $payload.result.content | Where-Object { $_.type -eq 'image' } | Select-Object -First 1
if (-not $imageBlock) {
    throw "MCP screenshot returned no image block: $($result.Content)"
}

$directory = Split-Path -Parent $OutputPath
if ($directory -and -not (Test-Path -LiteralPath $directory)) {
    New-Item -ItemType Directory -Path $directory | Out-Null
}
[System.IO.File]::WriteAllBytes($OutputPath, [Convert]::FromBase64String($imageBlock.data))
Get-Item -LiteralPath $OutputPath | Select-Object FullName, Length, LastWriteTime
