# Renders a static design mockup of the building panel (material / prefab picker).
# Tokens are taken from Docs/UI/ui-cold-steel-design-system.md:
#   GlassTint #1A1A1AF8  HeaderTint #64646416  Content #121212EB  StatusCard #252525E8
#   TextPrimary #E8E8E8  TextSecondary #B7B7B7  TextTertiary #919191
#   Accent #D6D6D6  Border #DEDEDE2E  ButtonPressed #181818F0
#   panel radius 10 px, card radius 8 px, button radius 6 px, outline 1 px
Add-Type -AssemblyName System.Drawing

$out = Join-Path $PSScriptRoot "panel_mockup.png"
$W = 1280; $H = 720
$bmp = New-Object System.Drawing.Bitmap $W, $H
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = 'AntiAlias'
$g.TextRenderingHint = 'ClearTypeGridFit'

function Brush($hex) {
    $a = [Convert]::ToInt32($hex.Substring(0,2),16)
    $r = [Convert]::ToInt32($hex.Substring(2,2),16)
    $gg = [Convert]::ToInt32($hex.Substring(4,2),16)
    $b = [Convert]::ToInt32($hex.Substring(6,2),16)
    return New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb($a,$r,$gg,$b))
}
function Pen2($hex,$w=1) {
    $a = [Convert]::ToInt32($hex.Substring(0,2),16)
    $r = [Convert]::ToInt32($hex.Substring(2,2),16)
    $gg = [Convert]::ToInt32($hex.Substring(4,2),16)
    $b = [Convert]::ToInt32($hex.Substring(6,2),16)
    return New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb($a,$r,$gg,$b)), $w
}
function RoundRect($x,$y,$w,$h,$rad) {
    $p = New-Object System.Drawing.Drawing2D.GraphicsPath
    $d = $rad * 2
    $p.AddArc($x, $y, $d, $d, 180, 90)
    $p.AddArc($x + $w - $d, $y, $d, $d, 270, 90)
    $p.AddArc($x + $w - $d, $y + $h - $d, $d, $d, 0, 90)
    $p.AddArc($x, $y + $h - $d, $d, $d, 90, 90)
    $p.CloseFigure()
    return $p
}
$uiFont = "Noto Sans SC"
try { $t = New-Object System.Drawing.Font($uiFont, 12); $t.Dispose() } catch { $uiFont = "Microsoft YaHei" }
try { $t = New-Object System.Drawing.Font($uiFont, 12); $t.Dispose() } catch { $uiFont = "Segoe UI" }
$numFont = "JetBrains Mono"
try { $t = New-Object System.Drawing.Font($numFont, 12); $t.Dispose() } catch { $numFont = "Consolas" }

# --- backdrop: dim game view with a faint 20 cm voxel grid --------------
$bg = New-Object System.Drawing.Drawing2D.LinearGradientBrush ([System.Drawing.Rectangle]::new(0,0,$W,$H)), `
    ([System.Drawing.Color]::FromArgb(255,42,44,48)), ([System.Drawing.Color]::FromArgb(255,18,19,21)), 45
$g.FillRectangle($bg, 0, 0, $W, $H)
$gridPen = Pen2 "14FFFFFF" 1
for ($i = 0; $i -lt 40; $i++) { $g.DrawLine($gridPen, 0, 470 + $i * 7, $W, 470 + $i * 7 - 30) }

# --- panel --------------------------------------------------------------
$px = 190; $py = 110; $pw = 900; $ph = 500
$panel = RoundRect $px $py $pw $ph 10
$g.FillPath((Brush "1A1A1AF8"), $panel)
$g.DrawPath((Pen2 "DEDEDE2E" 1), $panel)

# header strip
$head = RoundRect ($px + 1) ($py + 1) ($pw - 2) 44 10
$g.FillPath((Brush "64646416"), $head)
$g.DrawString("建造 · 构件", (New-Object System.Drawing.Font($uiFont, 15, [System.Drawing.FontStyle]::Bold)), (Brush "E8E8E8FF"), ($px + 20), ($py + 12))
$g.DrawString("B 关闭    Tab 切换分类", (New-Object System.Drawing.Font($uiFont, 9)), (Brush "919191FF"), ($px + $pw - 190), ($py + 17))
$g.DrawLine((Pen2 "DEDEDE2E" 1), $px, ($py + 45), ($px + $pw), ($py + 45))

# left category rail
$railX = $px + 16; $railY = $py + 62
$cats = @(@("材质", $false), @("构件", $true))
$cy = $railY
foreach ($c in $cats) {
    $r = RoundRect $railX $cy 120 36 6
    if ($c[1]) { $g.FillPath((Brush "181818F0"), $r); $g.DrawPath((Pen2 "D6D6D6FF" 1), $r) }
    else { $g.FillPath((Brush "2B2B2BBE"), $r); $g.DrawPath((Pen2 "DEDEDE2E" 1), $r) }
    $col = if ($c[1]) { "E8E8E8FF" } else { "B7B7B7FF" }
    $f = New-Object System.Drawing.Font($uiFont, 12, $(if ($c[1]) { [System.Drawing.FontStyle]::Bold } else { [System.Drawing.FontStyle]::Regular }))
    $g.DrawString($c[0], $f, (Brush $col), ($railX + 18), ($cy + 8))
    $cy += 46
}

# card grid
$cards = @(
    @("罗马柱", "80 × 80 × 260", "4 × 4 × 13 格", $false),
    @("围栏整体段", "200 × 40 × 160", "10 × 2 × 8 格", $true),
    @("凉亭台基", "Ø640 × 20", "32 × 32 × 1 格", $false),
    @("凉亭额枋环", "Ø640 × 40", "32 × 32 × 2 格", $false),
    @("凉亭穹顶", "Ø640 × 320", "32 × 32 × 16 格", $false),
    @("体素石块", "20 × 20 × 20", "1 × 1 × 1 格", $false)
)
$cx0 = $px + 156; $cy0 = $py + 62; $cw = 232; $ch = 118
for ($i = 0; $i -lt $cards.Count; $i++) {
    $col = $i % 3; $row = [math]::Floor($i / 3)
    $x = $cx0 + $col * ($cw + 10); $y = $cy0 + $row * ($ch + 10)
    $c = $cards[$i]
    $r = RoundRect $x $y $cw $ch 8
    $g.FillPath((Brush $(if ($c[3]) { "414141E6" } else { "252525E8" })), $r)
    $g.DrawPath((Pen2 $(if ($c[3]) { "D6D6D6FF" } else { "DEDEDE2E" }) 1), $r)
    $g.FillRectangle((Brush "121212EB"), ($x + 10), ($y + 10), 60, 60)
    $g.DrawRectangle((Pen2 "DEDEDE2E" 1), ($x + 10), ($y + 10), 60, 60)
    $g.DrawString("模型", (New-Object System.Drawing.Font($uiFont, 9)), (Brush "919191FF"), ($x + 22), ($y + 34))
    $g.DrawString($c[0], (New-Object System.Drawing.Font($uiFont, 12, [System.Drawing.FontStyle]::Bold)), (Brush "E8E8E8FF"), ($x + 80), ($y + 14))
    $g.DrawString($c[1], (New-Object System.Drawing.Font($numFont, 9)), (Brush "B7B7B7FF"), ($x + 80), ($y + 38))
    $g.DrawString($c[2], (New-Object System.Drawing.Font($uiFont, 9)), (Brush "919191FF"), ($x + 80), ($y + 58))
    $g.DrawString($(if ($c[3]) { "已选中" } else { "可放置" }), (New-Object System.Drawing.Font($uiFont, 9)), (Brush $(if ($c[3]) { "D6D6D6FF" } else { "919191FF" })), ($x + 80), ($y + 84))
}

# right detail pane
$dx = $px + 156 + 3 * ($cw + 10) + 6; $dy = $py + 62; $dw = 190; $dh = 246
$dp = RoundRect $dx $dy $dw $dh 8
$g.FillPath((Brush "121212EB"), $dp)
$g.DrawPath((Pen2 "DEDEDE2E" 1), $dp)
$g.DrawString("围栏整体段", (New-Object System.Drawing.Font($uiFont, 12, [System.Drawing.FontStyle]::Bold)), (Brush "E8E8E8FF"), ($dx + 12), ($dy + 10))
$rows = @(
    @("尺寸", "200 × 40 × 160"),
    @("占位", "10 × 2 × 8 格"),
    @("网格", "20 cm"),
    @("材质", "石材"),
    @("碰撞", "对齐盒"),
    @("造价", "12 石材")
)
$ry = $dy + 40
foreach ($r2 in $rows) {
    $g.DrawString($r2[0], (New-Object System.Drawing.Font($uiFont, 9)), (Brush "919191FF"), ($dx + 12), $ry)
    $sz = $g.MeasureString($r2[1], (New-Object System.Drawing.Font($numFont, 9)))
    $g.DrawString($r2[1], (New-Object System.Drawing.Font($numFont, 9)), (Brush "E8E8E8FF"), ($dx + $dw - 12 - $sz.Width), $ry)
    $ry += 26
}
$g.DrawLine((Pen2 "DEDEDE2E" 1), ($dx + 12), ($ry + 2), ($dx + $dw - 12), ($ry + 2))
$g.DrawString("吸附 20 cm", (New-Object System.Drawing.Font($uiFont, 9)), (Brush "B7B7B7FF"), ($dx + 12), ($ry + 12))
$g.DrawString("可旋转 90°", (New-Object System.Drawing.Font($uiFont, 9)), (Brush "B7B7B7FF"), ($dx + 12), ($ry + 34))

# bottom control hint
$g.DrawLine((Pen2 "DEDEDE2E" 1), $px, ($py + $ph - 40), ($px + $pw), ($py + $ph - 40))
$g.DrawString("左键 放置     右键 拆除     R 旋转     Shift 关闭吸附     滚轮 切换条目     Esc 退出建造", `
    (New-Object System.Drawing.Font($uiFont, 9)), (Brush "919191FF"), ($px + 20), ($py + $ph - 30))

$g.Dispose()
$bmp.Save($out, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
Write-Output ("mockup: " + $out + "  fonts=" + $uiFont + " / " + $numFont)
