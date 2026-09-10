param([Parameter(Mandatory = $true)][string]$OutputPath)

$args = @{
    toolset_name = 'EditorToolset.EditorAppToolset'
    tool_name = 'CaptureEditorImage'
    arguments = @{}
} | ConvertTo-Json -Depth 10 -Compress
$raw = & "$PSScriptRoot\mcp_call.ps1" -Tool 'call_tool' -ArgumentsJson $args | Out-String
$outer = $raw | ConvertFrom-Json
$inner = $outer.result.content[0].text | ConvertFrom-Json
$bytes = [Convert]::FromBase64String($inner.returnValue.data)
[IO.File]::WriteAllBytes($OutputPath, $bytes)
Write-Output $OutputPath
