# DeepSeek Flash 读图（2026-09-15）

当前会话模型只能处理文本，图片不会进入上下文。工程内的读图入口为 [Tools/deepseek-vision.ps1](../Tools/deepseek-vision.ps1)，直接调用 DeepSeek Flash 自带的图片输入通道，取回文字描述。

## 为什么不用智谱中继

个人技能 `deepseek-vision-skill`（`describe-image.js` → 智谱 GLM-4.6V）仍然可用，但你贴图时它才会触发，而且切到其他 provider 时会被白名单挡下。本工具走的是 DeepSeek 自己的图片通道：同一个 vendor、同一把 key、没有白名单，读图和当前会话是同一个 Flash 模型。

两条路都返回文字，不返回像素，可以互为交叉验证。GLM 的实测边界见技能内 SKILL.md（手部绝对坐标不可靠，角度类判断同图两次会矛盾）。

## 用法

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

## 支持的格式

JPEG、PNG、GIF、WebP，**按文件实际内容判定**（读魔术字节），不看扩展名。无法判定时退出码 6。单图超过 25 MB 拒发，超过 8 MB 告警。

## 能力边界

- 返回的是**文字描述**，不是我看过原图。追问细节必须重新调用一次。
- **一张图配一个具体问题**。多图合并判断会串扰，历史案例已确认。
- **定量几何不可信**：角度、哪端更低、是否镜像这类，必须用像素测量（alpha 掩模底边拟合、水平/垂直 IoU）做真值；读图只作为定性确认。
- **不替代用户验收**。读图结果只用于列差异、筛明显不合格候选；最终接受与否由用户拍板。
- 每次调用都会计费（含图片 token）。

## 通道现状

- 服务端：`deepseek-flash` 支持图片输入（2026-09-15 实测）。旧名 `deepseek-v4-flash-vision-exp` 已下线，同名请求仍由最新 Flash 承接。
- 客户端：`C:/Users/allan/.codex/models.json` 里 `deepseek-v4-flash` 仍标 `input_modalities: ["text"]`，所以聊天里粘贴的图片**不会**转发给模型，仍会显示 placeholder。本工具走独立 HTTP 请求，不受该开关影响。
- 若要打开客户端原生通道，需要在 `models.json` 给该 slug 增加 `"image"`，改完必须实际贴图验证；失败就回滚备份。

## 实测记录（2026-09-15，仅诊断，非项目验收）

- 合成探针图（640×320，指定文字 + 左上红圆 / 右下蓝方块）：`FPS-7-13-KX`、`vault 42 - nine` 逐字正确，形状、颜色、方位全对。
- `Docs/WeatherWorldTimeline20260912/trench-storm.png`：读图返回“黑屏，看不到游戏内容”；像素统计平均亮度 5.8/255，确认该帧本身近乎全黑。同目录 `dry.png` 平均亮度 155 属正常画面。若要用于天气文档，这张需要重拍。

## 记录规则

读图结论按事实描述写入对应案例文档，注明使用的是哪条通道（DeepSeek 自带 / 智谱中继）与提示词；不要把读图结果写成用户的视觉验收，也不要写成引擎运行测试通过。
