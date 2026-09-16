<#
.SYNOPSIS
  Codex 自己的 UE MCP 桥（v2：复用会话 + 批量调用）。不改动 mcp_call.ps1 / mcp_probe.ps1。

.DESCRIPTION
  以 JSON-RPC over HTTP 与 UE 编辑器内的 MCP 服务通信。使用 System.Net.WebRequest
  发送显式 UTF-8 字节，避开 Windows PowerShell 5.1 下 Invoke-WebRequest 解析 SSE
  响应时的 NullReferenceException，也不受 curl 引号转义影响。

  v2 的两处开销优化：
    1. 会话复用——Mcp-Session-Id 缓存在 %TEMP%\codex-ue-mcp-session.json，后续调用
       跳过 initialize / notifications/initialized 两次往返；会话失效自动重连一次。
    2. 批量调用——-BatchFile 一次进程启动、一次握手，顺序执行整串工具调用。
       多步建模流程（建体→布尔→UV→碰撞→保存）不再每步起一次进程。

.PARAMETER Tool
  裸工具名。call_tool 时，工具集全名放 arguments 里的 toolset_name，tool_name 用
  GetLogEntries 这样的裸名；带工具集前缀的名字会被判 Unknown tool。

.EXAMPLE
  powershell -NoProfile -File Tools/AssetPipeline/mcp_call_codex.ps1 -ListToolsets

.EXAMPLE
  powershell -NoProfile -File Tools/AssetPipeline/mcp_call_codex.ps1 -DescribeToolset Vibe3D.ModelingService

.EXAMPLE
  # 内层参数含引号时用文件，避开 PowerShell 5.1 的 -File 吃引号问题
  powershell -NoProfile -File Tools/AssetPipeline/mcp_call_codex.ps1 -Tool call_tool -ArgumentsFile payload.json

.EXAMPLE
  # 批量：一次启动执行整串调用
  powershell -NoProfile -File Tools/AssetPipeline/mcp_call_codex.ps1 -BatchFile batch.json -NewSession
#>
param(
    [string]$Endpoint = 'http://127.0.0.1:8000/mcp',
    [string]$Tool,
    [string]$ArgumentsJson = '{}',
    [string]$ArgumentsFile,
    [string]$BatchFile,
    [string]$DescribeToolset,
    [switch]$ListTools,
    [switch]$ListToolsets,
    [switch]$Json,
    [switch]$NewSession,
    [int]$SessionMaxAgeSeconds = 900
)

$ErrorActionPreference = 'Stop'
$script:Session = ''
$script:SessionStore = Join-Path $env:TEMP 'codex-ue-mcp-session.json'

function Send([string]$Json,[string]$Session) {
    $request = [System.Net.WebRequest]::Create($Endpoint)
    $request.Method = 'POST'
    $request.ContentType = 'application/json'
    $request.Accept = 'application/json'
    if ($Session) { $request.Headers['Mcp-Session-Id'] = $Session }
    $bytes = [Text.Encoding]::UTF8.GetBytes($Json)
    $request.ContentLength = $bytes.Length
    try { $stream = $request.GetRequestStream() }
    catch [System.Net.WebException] { throw "MCP 无响应：$Endpoint。UE 编辑器是否在运行、MCP 插件是否已启动？" }
    $stream.Write($bytes,0,$bytes.Length)
    $stream.Close()
    try { $response = $request.GetResponse() }
    catch [System.Net.WebException] {
        $response = $_.Exception.Response
        if (-not $response) { throw "MCP 请求失败：$($_.Exception.Message)" }
    }
    $reader = New-Object IO.StreamReader($response.GetResponseStream(),[Text.Encoding]::UTF8)
    $body = $reader.ReadToEnd()
    return [pscustomobject]@{
        Status = [int]$response.StatusCode
        Session = [string]$response.Headers['Mcp-Session-Id']
        Body = $body
    }
}

function Save-Session([string]$Session) {
    if (-not $Session) { return }
    $record = @{ session = $Session; stamp = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds(); endpoint = $Endpoint }
    $record | ConvertTo-Json -Compress | Set-Content -LiteralPath $script:SessionStore -Encoding UTF8
}

function Load-Session {
    if (-not (Test-Path -LiteralPath $script:SessionStore)) { return '' }
    try { $record = Get-Content -LiteralPath $script:SessionStore -Raw -Encoding UTF8 | ConvertFrom-Json } catch { return '' }
    if (-not $record.session) { return '' }
    if ($record.endpoint -ne $Endpoint) { return '' }
    $age = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() - [int64]$record.stamp
    if ($age -gt $SessionMaxAgeSeconds) { return '' }
    return [string]$record.session
}

function Connect {
    if (-not $NewSession) {
        $cached = Load-Session
        if ($cached) { $script:Session = $cached; return }
    }
    $handshake = Send '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"codex-melee-tools","version":"2.0"}}}' ''
    if ($handshake.Status -ne 200) { throw "initialize 失败 status=$($handshake.Status) $($handshake.Body)" }
    $script:Session = $handshake.Session
    $null = Send '{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}' $script:Session
    Save-Session $script:Session
}

function Show([string]$Body) {
    if ($Json) { return $Body }
    $parsed = $Body | ConvertFrom-Json
    if ($parsed.error) { return 'ERROR: ' + ($parsed.error | ConvertTo-Json -Compress) }
    if ($parsed.result -and $parsed.result.content) {
        return (($parsed.result.content | ForEach-Object { $_.text }) -join "`n")
    }
    return ($parsed.result | ConvertTo-Json -Depth 12)
}

function CallRaw([string]$Name,[string]$Arguments) {
    $payload = '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"' + $Name + '","arguments":' + $Arguments + '}}'
    $result = Send $payload $script:Session
    # 会话过期时服务端回 400/404；重连一次再试。
    if ($result.Status -ne 200 -and $script:Session) {
        $script:Session = ''
        Connect
        $result = Send $payload $script:Session
    }
    if ($result.Status -ne 200) { return "ERROR status=$($result.Status) $($result.Body)" }
    return Show $result.Body
}

function Call([string]$Name,[string]$Arguments) { return CallRaw $Name $Arguments }

Connect

if ($ListTools) {
    $result = Send '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' $script:Session
    if ($Json) { $result.Body }
    else { (($result.Body | ConvertFrom-Json).result.tools | ForEach-Object { "$($_.name) - $($_.description)" }) -join "`n" }
    return
}
if ($ListToolsets) { Call 'list_toolsets' '{}'; return }
if ($DescribeToolset) { Call 'describe_toolset' ('{"toolset_name":"' + $DescribeToolset + '"}'); return }

if ($BatchFile) {
    if (-not (Test-Path -LiteralPath $BatchFile -PathType Leaf)) { throw "找不到批量文件: $BatchFile" }
    $calls = (Get-Content -LiteralPath $BatchFile -Raw -Encoding UTF8 | ConvertFrom-Json)
    $index = 0
    foreach ($entry in $calls) {
        ++$index
        $name = if ($entry.tool) { [string]$entry.tool } else { [string]$entry.name }
        if (-not $name) { throw "批量文件第 $index 项缺少 tool/name" }
        $arguments = if ($entry.arguments) { $entry.arguments | ConvertTo-Json -Depth 12 -Compress } else { '{}' }
        Write-Output "===== [$index] $name ====="
        Write-Output (Call $name $arguments)
    }
    return
}

if (-not $Tool) { throw '用法: -ListTools | -ListToolsets | -DescribeToolset <名称> | -Tool <工具名> [-ArgumentsJson|-ArgumentsFile] | -BatchFile <JSON 数组>' }
if ($ArgumentsFile) {
    if (-not (Test-Path -LiteralPath $ArgumentsFile -PathType Leaf)) { throw "找不到参数文件: $ArgumentsFile" }
    $ArgumentsJson = ([IO.File]::ReadAllText($ArgumentsFile) -replace "^\uFEFF",'').Trim()
}
Call $Tool $ArgumentsJson
