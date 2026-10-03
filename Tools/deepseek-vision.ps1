<#
.SYNOPSIS
  Use the DeepSeek Flash vision input to read an image and return a text description.

.DESCRIPTION
  Sends a local image file or an http(s) image URL to DeepSeek Flash's image input
  channel and prints the returned description. This is the project's own route and
  does not depend on the Codex skill relay that goes through Zhipu GLM-4.6V.
  Image format is detected from the file's actual bytes (PNG / JPEG / GIF / WebP).

  The output is a factual text description only. It never replaces the user's own
  visual acceptance, and quantitative geometry questions (angles, which end is
  lower, mirrored or not) must be settled by pixel measurement instead.

.PARAMETER Image
  One or more local image paths, or http(s) image URLs. Pass with -Image or as
  positional arguments. Relative paths resolve against the project root.

.PARAMETER Prompt
  A specific question. Use one image with one concrete question per call; avoid
  mixing several images into a single judgement.

.NOTES
  Interactive reading no longer needs this script: the harness exposes a mounted
  read_image tool that hands the pixels to the model directly, so you can look at
  an image and ask follow-up questions. Use this script when you specifically want
  one of: batch over many images, a remote URL, a headless/scripted call, or a read
  that deliberately keeps image bytes out of the session history.

  The former -Latest switch was removed on 2026-09-22. It scraped pasted images out
  of C:/Users/allan/.codex/sessions/*.jsonl, a workaround for the old Codex session
  where pasted images never reached the model. Under the current harness attachments
  are normalized to E:/DSH/attachments/v1/objects/<hash> and read directly, so that
  code path could never fire.

.EXAMPLE
  powershell -NoProfile -File Tools/deepseek-vision.ps1 "Docs/WeatherPreview20260912/storm.png" -Prompt "画面是什么天气？可见度如何？"

.EXAMPLE
  powershell -NoProfile -File Tools/deepseek-vision.ps1 "D:/shots/icon.png" -OutFile "SourceAssets/IconReview20260915/read.txt"
#>
param(
    [Parameter(Position = 0)]
    [string[]]$Image,

    [string]$Prompt = '客观描述这张图片：主体、构图、颜色与画面中的文字。只陈述看得见的内容，不做推测。',

    [string]$Model = 'deepseek-v4-flash',
    [int]$MaxTokens = 1200,
    [int]$TimeoutSec = 120,
    [string]$OutFile,
    [string]$ApiKey = $env:DEEPSEEK_API_KEY,
    [string]$Endpoint = 'https://api.deepseek.com/chat/completions'
)

$ErrorActionPreference = 'Stop'

function Get-ImageMimeType {
    param([byte[]]$Bytes)
    if ($Bytes.Length -ge 4 -and $Bytes[0] -eq 0x89 -and $Bytes[1] -eq 0x50 -and $Bytes[2] -eq 0x4E -and $Bytes[3] -eq 0x47) { return 'image/png' }
    if ($Bytes.Length -ge 3 -and $Bytes[0] -eq 0xFF -and $Bytes[1] -eq 0xD8 -and $Bytes[2] -eq 0xFF) { return 'image/jpeg' }
    if ($Bytes.Length -ge 6 -and $Bytes[0] -eq 0x47 -and $Bytes[1] -eq 0x49 -and $Bytes[2] -eq 0x46 -and $Bytes[3] -eq 0x38) { return 'image/gif' }
    if ($Bytes.Length -ge 12 -and $Bytes[0] -eq 0x52 -and $Bytes[1] -eq 0x49 -and $Bytes[2] -eq 0x46 -and $Bytes[3] -eq 0x46 -and
        $Bytes[8] -eq 0x57 -and $Bytes[9] -eq 0x45 -and $Bytes[10] -eq 0x42 -and $Bytes[11] -eq 0x50) { return 'image/webp' }
    return $null
}

if (-not $Image -or $Image.Count -eq 0) {
    Write-Error '用法: powershell -NoProfile -File Tools/deepseek-vision.ps1 <图片路径或 URL> [-Prompt "具体问题"] [-OutFile 输出文本]' -ErrorAction Continue
    exit 2
}

if (-not $ApiKey -or $ApiKey -eq 'YOUR_DEEPSEEK_API_KEY_HERE') {
    Write-Error '缺少 DEEPSEEK_API_KEY。设置环境变量，或用 -ApiKey 传入；密钥不写入工程文件。' -ErrorAction Continue
    exit 3
}

$projectRoot = Split-Path -Parent $PSScriptRoot
$results = New-Object System.Collections.Generic.List[string]


foreach ($item in $Image) {
    $isUrl = $item -match '^https?://'
    $label = $item
    $imageUrl = $null

    if ($isUrl) {
        $imageUrl = $item
    }
    else {
        $path = $item
        if (-not [IO.Path]::IsPathRooted($path)) { $path = Join-Path $projectRoot $path }
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            Write-Error "找不到图片: $path" -ErrorAction Continue
            exit 4
        }
        $info = Get-Item -LiteralPath $path
        if ($info.Length -gt 25MB) {
            Write-Error "图片超过 25 MB，拒绝发送: $($info.FullName)" -ErrorAction Continue
            exit 5
        }
        if ($info.Length -gt 8MB) {
            Write-Warning "图片 $([math]::Round($info.Length / 1MB, 1)) MB，较大，可能被接口拒绝。"
        }

        $bytes = [IO.File]::ReadAllBytes($info.FullName)
        $mime = Get-ImageMimeType -Bytes $bytes
        if (-not $mime) {
            Write-Error "无法从文件内容判定图片格式（仅支持 PNG/JPEG/GIF/WebP）: $($info.FullName)" -ErrorAction Continue
            exit 6
        }

        $label = $info.FullName
        $imageUrl = "data:$mime;base64," + [Convert]::ToBase64String($bytes)
        Write-Verbose "[deepseek-vision] $($info.Name) $mime $([math]::Round($info.Length / 1KB, 1)) KB"
    }

    $payload = @{
        model      = $Model
        max_tokens = $MaxTokens
        messages   = @(
            @{
                role    = 'user'
                content = @(
                    @{ type = 'text'; text = $Prompt },
                    @{ type = 'image_url'; image_url = @{ url = $imageUrl } }
                )
            }
        )
    }

    $json = $payload | ConvertTo-Json -Depth 12 -Compress
    $body = [Text.Encoding]::UTF8.GetBytes($json)

    try {
        # Windows PowerShell 5.1 会按 Latin-1 解码 JSON 响应体，这里显式按 UTF-8 读原始字节。
        $webResponse = Invoke-WebRequest -Uri $Endpoint -Method Post -ContentType 'application/json' `
            -Headers @{ Authorization = "Bearer $ApiKey" } -Body $body -TimeoutSec $TimeoutSec -UseBasicParsing
        $responseText = [Text.Encoding]::UTF8.GetString($webResponse.RawContentStream.ToArray())
        $response = $responseText | ConvertFrom-Json
    }
    catch {
        $status = ''
        try { $status = [string]$_.Exception.Response.StatusCode.value__ } catch { }
        $detail = ''
        try {
            $reader = New-Object IO.StreamReader($_.Exception.Response.GetResponseStream(), [Text.Encoding]::UTF8)
            $detail = $reader.ReadToEnd()
        }
        catch { }
        Write-Error "DeepSeek 读图请求失败 status=$status $($_.Exception.Message) $detail" -ErrorAction Continue
        exit 7
    }

    $text = $response.choices[0].message.content
    if (-not $text) { $text = $response.choices[0].message.reasoning_content }
    if (-not $text) { $text = '(接口返回空内容 finish_reason=' + $response.choices[0].finish_reason + ')' }

    $block = @()
    $block += "===== $label ====="
    $block += "[模型 $($response.model)]"
    $block += $text.Trim()
    $results.Add(($block -join [Environment]::NewLine))
}

$final = $results -join ([Environment]::NewLine + [Environment]::NewLine)
Write-Output $final

if ($OutFile) {
    $outPath = $OutFile
    if (-not [IO.Path]::IsPathRooted($outPath)) { $outPath = Join-Path $projectRoot $outPath }
    $outDir = Split-Path -Parent $outPath
    if ($outDir -and -not (Test-Path -LiteralPath $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
    $header = "# deepseek-vision $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') model=$Model`n# prompt: $Prompt`n"
    Add-Content -LiteralPath $outPath -Value ($header + $final) -Encoding UTF8
    Write-Output "写入: $outPath"
}
