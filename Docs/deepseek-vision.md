# DeepSeek Flash 读图（2026-09-15，2026-09-22 修订）

2026-09-15 起 `deepseek-v4-flash` 带 `image` 输入模态。**2026-09-22 起会话内挂载的
`read_image` 工具是交互读图的默认入口** —— 它把图交给模型直接看，能追问；
`Tools/deepseek-vision.ps1` 退为专用入口（批量 / headless / 不想让图片进上下文）。

## 两条路的分工（2026-09-22 修订）

| | `read_image`（默认） | `Tools/deepseek-vision.ps1`（专用） |
| --- | --- | --- |
| 我看得到像素吗 | 能，可直接分析、可追问 | 不能，只拿回一段文字描述 |
| 占会话上下文 | 占（原图字节留在历史里） | 不占（独立 HTTP 请求） |
| 多图 | 一次一张 | 一次可传多张，逐张单独请求 |
| 远程 URL | 不支持 | 支持 |
| 可 headless 调用 | 不能（需要我在环） | 能，后台任务/脚本可调 |
| 前置条件 | 无 | 需要 `DEEPSEEK_API_KEY`（缺失退出码 3） |

**选哪个：**
- 让**我**看图、问图里有什么、追问细节 → `read_image`
- 批量筛几十张候选、按脚本跑、或刻意不想让图片字节留在对话历史里 → 脚本

分辨率不构成选择理由：`read_image` **保留原图尺寸**（实测一张 268×163、一张 1476×858
的附件都是原生分辨率，没有二次缩放）。如果连我都看不清细节，那是原图本身不够大。

## 请求体上限与 413（2026-09-16 实测）

原生图片通道打开后，图片字节会随历史影响请求体（`disable_response_storage = true` 时不用服务端存储）。2026-09-16 蓄力左臂线程累计 26 张评审 sheet、约 49 MB 图片：请求体约 50.0 MB 时仍成功，再加一张 1.6 MB 的 sheet 涨到约 51.7 MB 就返回 `413 Payload Too Large: Failed to buffer the request body: length limit exceeded`，之后该线程每条新消息都失败，只能换新线程。

那时要让会话能看图，得先用 [Tools/shrink-for-view.ps1](../Tools/shrink-for-view.ps1) 手工缩成长边 ≤1400、JPEG q80 的副本（通常 150–400 KB）。

**2026-09-22 的状态**：harness 自己会规范化大图（工具描述写明「validates and downscales large
supported images before the next model request」），所以手工缩图不再是看图的必要前置。
但**单线程累计大图仍会顶到上限**这条没变，只是触发点未知 —— 稳妥做法仍是图片别无限往一个
线程里塞，换一版候选就开新线程。`shrink-for-view.ps1` 保留，用于两种情况：
需要控制累计体积时、以及显式指定输出副本给别的工具用。

像素测量与 alpha 拟合继续读原图，不要用缩图出定量结论。

## 为什么不用智谱中继

个人技能 `deepseek-vision-skill`（`describe-image.js` → 智谱 GLM-4.6V）仍然可用，但你贴图时它才会触发，而且切到其他 provider 时会被白名单挡下。本工程的两条路都走 DeepSeek 自己的图片通道：同一个 vendor，没有白名单，读图和当前会话是同一个 Flash 模型（脚本需要单独配置 `DEEPSEEK_API_KEY`，见下）。

脚本与中继都只返回文字、不返回像素，可以互为交叉验证；`read_image` 是唯一能让我直接看像素并追问的路。GLM 的实测边界见技能内 SKILL.md（手部绝对坐标不可靠，角度类判断同图两次会矛盾）。

## 用法

**交互读图（默认）**：直接用挂载的 `read_image` 工具读本地图片路径。图交给我看，可追问，
不需要 API key。附件与项目内的图片都可以。

**脚本（批量 / headless / 不占上下文）**：

```powershell
# 项目内相对路径（相对工程根目录）
pwsh -File Tools/deepseek-vision.ps1 "Docs/WeatherPreview20260912/storm.png" -Prompt "画面是什么天气？可见度如何？"

# 绝对路径 + 具体问题
pwsh -File Tools/deepseek-vision.ps1 -Image "D:/shots/arms-closeup.png" -Prompt "左手是否握住握把？袖口与腕背轮廓有无断裂？"

# 远程图片 URL
pwsh -File Tools/deepseek-vision.ps1 "https://example.com/ref.png" -Prompt "这件配件的接口形状是什么？"

# 结果同时落盘
pwsh -File Tools/deepseek-vision.ps1 "D:/shots/icon.png" -OutFile "SourceAssets/IconReview20260915/read.txt"
```

参数：`-Model`（默认 `deepseek-v4-flash`）、`-MaxTokens`、`-TimeoutSec`、`-ApiKey`、`-Endpoint`。多张图会逐张单独请求，不合并成一次判断。

## 密钥

按顺序取 `-ApiKey` 参数 → 环境变量 `DEEPSEEK_API_KEY`。密钥不写入工程文件，也不进仓库。缺失时报错退出，错误码 3。

**2026-09-22 状态：本机 `DEEPSEEK_API_KEY` 未设置，脚本会以退出码 3 失败。**
要走脚本这条路，先设好环境变量；只是让**我**看图则不需要 key（走 `read_image`）。

## 支持的格式

JPEG、PNG、GIF、WebP，**按文件实际内容判定**（读魔术字节），不看扩展名。无法判定时退出码 6。单图超过 25 MB 拒发，超过 8 MB 告警。

## 能力边界

- **`read_image` 路**：我看得到像素，能分析也能追问，但图片字节进会话上下文。
- **脚本路**：返回的是**文字描述**，不是我看过原图。追问细节必须重新调用一次。
- **一张图配一个具体问题**。多图合并判断会串扰，历史案例已确认。
- **定量几何不可信**：角度、哪端更低、是否镜像这类，必须用像素测量（alpha 掩模底边拟合、水平/垂直 IoU）做真值；读图只作为定性确认。
- **不替代用户验收**。读图结果只用于列差异、筛明显不合格候选；最终接受与否由用户拍板。
- 脚本每次调用都会计费（含图片 token）；`read_image` 计入会话。

## 通道现状

- 服务端：`deepseek-flash` 支持图片输入（2026-09-15 实测）。旧名 `deepseek-v4-flash-vision-exp` 已下线，同名请求仍由最新 Flash 承接。
- 客户端模态：`deepseek-v4-flash` 的 `input_modalities` 为 `["text","image"]`（同目录 `deepseek-v4-pro` 与 `kimi-k3` 都只有 `text`）。想让会话内读图退回纯文本，得改这个配置；改前备份。
- **会话内路由（2026-09-22）**：DSH 把附件规范化后存到 `E:\DSH\attachments\v1\objects\<hash 前两位>\<hash>`，
  `read_image` 直接读该路径，**保留原图尺寸**。这替代了旧 Codex 会话的 data URL 做法。
- 脚本仍走独立 HTTP 请求，不占会话预算。

## 已删除：`-Latest` 参数（2026-09-22）

脚本原有 `-Latest` 与 `Get-LatestPastedImage`（约 30 行），用于从
`C:/Users/allan/.codex/sessions/*.jsonl` 里把用户贴的图以 data URL 捞回来 —— 那是**旧 Codex
会话**的变通：当时贴的图模型收不到，只留在 transcript 里。

DSH 不存在这个问题（见上「会话内路由」），该代码永不命中，已删除。要单独读用户刚贴的图，
直接传 `E:\DSH\attachments\...` 的路径，或用 `read_image`。

## 实测记录（2026-09-15，仅诊断，非项目验收）

- 合成探针图（640×320，指定文字 + 左上红圆 / 右下蓝方块）：`FPS-7-13-KX`、`vault 42 - nine` 逐字正确，形状、颜色、方位全对。
- `Docs/WeatherWorldTimeline20260912/trench-storm.png`：读图返回“黑屏，看不到游戏内容”；像素统计平均亮度 5.8/255，确认该帧本身近乎全黑。同目录 `dry.png` 平均亮度 155 属正常画面。若要用于天气文档，这张需要重拍。

## 记录规则

读图结论按事实描述写入对应案例文档，注明使用的是哪条通道（DeepSeek 自带 / 智谱中继）与提示词；不要把读图结果写成用户的视觉验收，也不要写成引擎运行测试通过。
