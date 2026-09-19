# 蛋糕塔喷泉 V9：循环水声、湿石材和局部模型精修

用户已确认 V8 水体达到预期，随后授权继续精修，并要求做好声音循环衔接。
本轮保留 V8 盆水、随机溢流、落点飞沫及既有距离分级。未启动游戏、试听、截图、渲染或性能测试；由用户体验。

## 循环水声

用两层持续的 SoundWave 替代随机脚步水花占位声：

2026-09-19 用户反馈整体基本达到预期，但水声偏小：两条 SoundWave 的播放音量均由 `1.0` 调到 `3.0`（线性增益三倍，约 +9.54 dB）。两层比例、音源采样、循环衔接、距离衰减和并发设置不变；未试听，由用户体验。

| 层 | 成品时长 | 首尾重叠 | 播放范围 | 内容 |
| --- | --- | --- | --- | --- |
| `S_FountainBed_LoopV9` | 约 8.8 秒 | 1.2 秒 | 32 m | 小喷泉连续流水底声 |
| `S_FountainDetail_LoopV9` | 18 秒 | 2 秒 | 16 m | 小瀑布近处落水细节 |

- 作者脚本将尾段与头段做等功率交叉淡化，文件末尾接回原录音中紧邻文件起点的采样；循环边界没有人为插入静音。
- 先转单声道、48 kHz，移除直流并作周期域低切/高切，避免滤波器启动瞬态破坏接缝。分别按 -22/-24 dB RMS 定标，峰值上限 0.82。
- 导入为 PCM16，开启 `looping`、`ForceInline`，两层原始 PCM 数据合计约 2.57 MB（2.45 MiB）；实例共用音频资产。以小幅常驻内存换取直接播放，避免每圈重新加载或定时触发。
- 两层时长不同，各座喷泉起始相位不同。一次启动后交给混音器连续循环，不在循环点改变音高或重播组件。
- 淡入 0.9 秒，离开范围淡出 1 秒；边界增加 2 m 回差。淡出中重新进入会平滑恢复音量。
- 4.5 m 内为近距离区，此后自然衰减；远处低通逐渐降至 3.5 kHz。声源跟随喷泉，不依赖是否在镜头中可见。
- 每世界共享两组并发设置，每层最多 4 个活动声源，优先最近实例；被替换声源用 0.7 秒释放淡化，释放阶段可能与新声源短暂重叠。并发拒绝后的重试最多每秒一次。
- `fps.Fountain.Quality 0`、`bEnableAudio=false` 或隐藏喷泉时淡出；销毁时停止组件。旧间隔和 `SplashCues` 字段仅留作序列化兼容，不再播放占位脚步水花。

### 来源与许可

两条音频均为 Nox_Sound 发布的 CC0 作品：

- [Ambiance_Fountain_Small_Loop_Stereo.wav](https://freesound.org/people/Nox_Sound/sounds/676173/)
- [Ambiance_Waterfall_Small_Close_Loop_Stereo.wav](https://freesound.org/people/Nox_Sound/sounds/698306/)
- [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/)

Freesound 的原始 WAV 下载需要登录；本轮使用作者公开提供的 HQ MP3 版本，并非原始 24-bit WAV。
处理结果保存为 PCM 不会恢复 MP3 丢失的信息。来源网页、下载版本、散列、处理参数保存在
`SourceAssets/RomanFountain20260917/AudioV9/sources-and-processing.json`。

## 石材和模型

- 复制现有 `M_RomanStone_V2` 图表为喷泉专用材质，保留原大理石纹理和干燥外观。
- 盘沿及落水接触区域使用不规则湿痕，适度降低亮度与粗糙度；水线附近加轻微矿物沉积。新增掩码复用 V8 的 256² 噪声纹理，不加透明叠层或额外绘制组件。
- `FountainWetness=0.85`、`FountainMineral=0.12`、`FountainFinialDetail=0.8` 可在 `MIC_FountainStoneV9` 调整。
- `SM_FountainPolishedV9` 是原模型副本。只替换底座两层台阶的独立网格壳，增加 1 cm 倒角；其余盆沿和结构沿用原几何。
- 塔尖增加轻微错列鳞片法线细节，没有几何位移。仅给新台阶生成 UV/法线，没有对整个已认可模型重新铺 UV。
- 保留原碰撞策略、占格 `(48,48,36)`、锚点与存档字段。旧主模型与共享石材保留。
- 主体几何 LOD 和独立塔尖喷射美术本轮未追加；继续沿用 V8 的水效分级与飞沫预算。没有实测帧率结论。

## 接入和制作文件

- 新资产根目录：`/Game/Props/RomanFountain20260917/PolishV9/`，音频在其 `Audio/` 子目录。
- `AColdSteelFountain` 默认加载精修模型；已有关卡实例在 BeginPlay 将原默认模型/石材迁移到 V9。显式指定的其他表面材质继续保留。
- 建造调色板仅更新 `roman_fountain` 条目的 Mesh/Surface；ActorClass、占格及其他条目不改。
- 音源制作：`SourceAssets/RomanFountain20260917/prepare_fountain_audio_v9.py`。
- 资产制作：`SourceAssets/RomanFountain20260917/build_polish_v9_20260919.py`。
- 已打开编辑器内的调色板接入：`SourceAssets/RomanFountain20260917/integrate_polish_v9_palette.py`。
- 制作回执和原生构建日志：`Saved/FountainPolishV9/`。

新增了原生音频组件和反射字段，重启编辑器后再体验本版；不把构建结果等同于实机声音或画面验收。

制作状态：模型、材质和音频资产已保存，调色板接入命令已完成；Editor 与 Game 的 Development 构建均为 `Succeeded`。
早期命令行制作遇到 MCP 端口占用、调色板被编辑器占用及 PIE 保存限制，最终在编辑器释放后完成源调色板保存。
没有结束用户的 PIE、关闭编辑器或执行实机试听/测试。
