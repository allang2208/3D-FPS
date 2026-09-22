<#
.SYNOPSIS
  Codex 自己的 UE MCP 桥（v4：并行准备、整批互斥接入、限长输出）。

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
    [string]$PythonScript,
    [string]$PythonNodeId,
    [string]$DescribeToolset,
    [switch]$ListTools,
    [switch]$ListToolsets,
    [switch]$Json,
    [switch]$NewSession,
    [string]$OutputFile,
    [ValidateRange(0, 2147483647)]
    [int]$MaxOutputChars = 0,
    [ValidateRange(0, 3600)]
    [int]$QueueWaitSeconds = 60,
    [int]$SessionMaxAgeSeconds = 900
)

$ErrorActionPreference = 'Stop'
$script:Session = ''
$script:SessionStore = Join-Path $env:TEMP 'codex-ue-mcp-session.json'
$script:CallFailed = $false
# 兼容旧调用：默认完整输出；限长必须同时保留可读取的完整结果。
if ($MaxOutputChars -gt 0 -and -not $OutputFile) {
    throw '-MaxOutputChars 需要 -OutputFile 保存完整结果。'
}
if ($Json -and $MaxOutputChars -gt 0) {
    throw '-Json 不支持截断；使用 -OutputFile 保存原始响应。'
}
if ($OutputFile) {
    $OutputFile = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputFile)
    $parent = Split-Path -Parent $OutputFile
    [IO.Directory]::CreateDirectory($parent) | Out-Null
    # 每次调用使用新路径，避免覆盖其他任务的结果。
    $file = [IO.File]::Open($OutputFile, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write)
    $file.Dispose()
}

function Emit([string]$Text) {
    if ($OutputFile) {
        [IO.File]::AppendAllText($OutputFile, $Text + [Environment]::NewLine, [Text.UTF8Encoding]::new($false))
    }
    if ($MaxOutputChars -gt 0 -and $Text.Length -gt $MaxOutputChars) {
        Write-Output ($Text.Substring(0, $MaxOutputChars) + "`n[输出已截断；完整结果：$OutputFile]")
    } else { Write-Output $Text }
}

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

function Connect([switch]$Force) {
    if (-not $NewSession -and -not $Force) {
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
    $parsed = $Body | ConvertFrom-Json
    $script:CallFailed = [bool]($parsed.error -or $parsed.result.isError)
    if ($Json) { return $Body }
    if ($parsed.error) { return 'ERROR: ' + ($parsed.error | ConvertTo-Json -Compress) }
    if ($parsed.result -and $parsed.result.content) {
        $content = (($parsed.result.content | ForEach-Object { $_.text }) -join "`n")
        if ($parsed.result.isError) { return 'ERROR: ' + $content }
        return $content
    }
    return ($parsed.result | ConvertTo-Json -Depth 12)
}

function CallRaw([string]$Name,[string]$Arguments) {
    $script:CallFailed = $false
    $payload = '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"' + $Name + '","arguments":' + $Arguments + '}}'
    $result = Send $payload $script:Session
    # 仅会话丢失的 404 自动重连；400/500 或结果不明的写入不自动重放。
    if ($result.Status -eq 404 -and $script:Session) {
        $script:Session = ''
        Connect -Force
        $result = Send $payload $script:Session
    }
    if ($result.Status -ne 200) {
        $script:CallFailed = $true
        return "ERROR status=$($result.Status) $($result.Body)"
    }
    return Show $result.Body
}

function Call([string]$Name,[string]$Arguments) { return CallRaw $Name $Arguments }

# 同一 Windows 登录会话、同一端口的桥调用共享锁（localhost/127.0.0.1 使用同一锁）。
# 从握手到整个批次结束持有；不跨调用保留，不在制作/模型思考阶段占用。
$endpointUri = [Uri]$Endpoint
$gate = [Threading.Mutex]::new($false, ('Local\CodexUeMcp-Port-' + $endpointUri.Port))
$gateHeld = $false
try {
    try { $gateHeld = $gate.WaitOne(0) }
    catch [Threading.AbandonedMutexException] {
        $gateHeld = $true
        throw '上次 MCP 桥异常退出，UE 操作完成状态未知；本次未发送请求，请先处理原任务状态。'
    }
    if (-not $gateHeld) {
        [Console]::Error.WriteLine('UE 接入窗口忙，桥内静默等待；不必轮询或询问其他对话。')
        try { $gateHeld = $gate.WaitOne([TimeSpan]::FromSeconds($QueueWaitSeconds)) }
        catch [Threading.AbandonedMutexException] {
            $gateHeld = $true
            throw '上次 MCP 桥异常退出，UE 操作完成状态未知；本次未发送请求，请先处理原任务状态。'
        }
    }
    if (-not $gateHeld) {
        [Console]::Error.WriteLine('UE 接入等待超时，本次未发送请求。保留批次，继续独立制作，稍后提交一次。')
        exit 75
    }

# Python asset imports use the same gate as MCP. The native MCP toolsets do
# not expose AssetImportTask or general editor Python execution.
if ($PythonScript) {
    if ($Tool -or $BatchFile -or $DescribeToolset -or $ListTools -or $ListToolsets -or $Json) {
        throw '-PythonScript 不能与其他调用模式组合。'
    }
    $scriptPath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($PythonScript)
    if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) { throw "找不到 Python 脚本: $scriptPath" }
    $clientPath = Join-Path $PSScriptRoot 'ue_python_exec.py'
    $pythonArguments = @($clientPath, '--script', $scriptPath, '--timeout', '20')
    if ($PythonNodeId) { $pythonArguments += @('--node', $PythonNodeId) }
    $pythonOutput = & py -3.11 @pythonArguments 2>&1
    $pythonExitCode = $LASTEXITCODE
    Emit (($pythonOutput | ForEach-Object { [string]$_ }) -join "`n")
    if ($pythonExitCode -ne 0) { exit $pythonExitCode }
    return
}

Connect

if ($ListTools) {
    $result = Send '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' $script:Session
    if ($Json) { Emit $result.Body }
    else { Emit ((($result.Body | ConvertFrom-Json).result.tools | ForEach-Object { "$($_.name) - $($_.description)" }) -join "`n") }
    return
}
if ($ListToolsets) { Emit (Call 'list_toolsets' '{}'); if ($script:CallFailed) { exit 1 }; return }
if ($DescribeToolset) { Emit (Call 'describe_toolset' ('{"toolset_name":"' + $DescribeToolset + '"}')); if ($script:CallFailed) { exit 1 }; return }

if ($BatchFile) {
    if (-not (Test-Path -LiteralPath $BatchFile -PathType Leaf)) { throw "找不到批量文件: $BatchFile" }
    $calls = (Get-Content -LiteralPath $BatchFile -Raw -Encoding UTF8 | ConvertFrom-Json)
    $index = 0
    foreach ($entry in $calls) {
        ++$index
        $name = if ($entry.tool) { [string]$entry.tool } else { [string]$entry.name }
        if (-not $name) { throw "批量文件第 $index 项缺少 tool/name" }
        $arguments = if ($entry.arguments) { $entry.arguments | ConvertTo-Json -Depth 12 -Compress } else { '{}' }
        Emit "===== [$index] $name ====="
        Emit (Call $name $arguments)
        if ($script:CallFailed) { throw "批量第 $index 项失败，后续未执行；已完成操作不会自动回滚。" }
    }
    return
}

if (-not $Tool) { throw '用法: -ListTools | -ListToolsets | -DescribeToolset <名称> | -Tool <工具名> [-ArgumentsJson|-ArgumentsFile] | -BatchFile <JSON 数组>' }
if ($ArgumentsFile) {
    if (-not (Test-Path -LiteralPath $ArgumentsFile -PathType Leaf)) { throw "找不到参数文件: $ArgumentsFile" }
    $ArgumentsJson = ([IO.File]::ReadAllText($ArgumentsFile) -replace "^\uFEFF",'').Trim()
}
Emit (Call $Tool $ArgumentsJson)
if ($script:CallFailed) { exit 1 }
} finally {
    if ($gateHeld) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
