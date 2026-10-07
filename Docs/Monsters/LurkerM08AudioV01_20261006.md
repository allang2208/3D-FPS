# 伏窥者 M-08 音效 AudioV01（2026-10-06）

为伏窥者补齐本体音效体系；此前仅有气炮武器音（V06 蓄力/释放、V11 预警）。复用优先：肉身层取 M-10 已下载 freesound CC0 预览源，孔膜/软骨/掌垫/呼啸全部 numpy 程序合成，未做公开渠道再搜索。

## 资产

6 个 48 kHz 单声道 WAV 在 `SourceAssets/Monsters/LurkerM08/AudioV01/Audio/`，导入 `/Game/Monsters/LurkerM08/Audio/AudioV1`：Idle 3.0 s 循环（腹鸣+背孔膜颤动）、Crawl 2.4 s 循环（湿掌垫+贴面拖行，地面与表面爬行共用）、Bite 0.95 s（颚合峰值 0.45 s）、Pounce 1.30 s（0.28 s 起跳呼啸、0.95 s 落地）、Hit 0.65 s、Death 1.90 s（侧倒 0.85 s）。制作参数与逐源 CC0 记录见 `AudioV01/README.md` 与 `Records/audio_source.json`。

## 接入

- `LurkerM08Monster.h` 新增 `M08|Audio`：Idle/Crawl/Bite/Pounce/Hit/Death 六个声音属性与 `IdleVoice`/`CrawlVoice` 循环组件（挂 `chest` 骨、衰减覆盖）。
- 新增 `LurkerM08Audio.cpp`：`UpdateM08Audio` 于 `Tick`（在 authority 死亡早退之前）轮询 `EWolfState` 边沿播一次性——单机/监听服/专用服客户端同路径覆盖，不改共享 `AWolfMonster` 基类；专用服务器跳过；`EndPlay` 停全部循环。
- Bite/Pounce/Stagger/Dying 边沿播音；Howl 未接（本怪 `bHowlOnEncounter=false`）；CrawlVoice 以实际速度门控，墙面/天花板爬行同生效。气炮音效入口不变。

## 状态

已完成：双 target 构建通过，6 个 SoundWave 落盘 `Audio/AudioV1`（Idle/Crawl 循环、FORCE_INLINE），`BP_LurkerM08` CDO 写入 6 个声音引用；回执在 `AudioV01/`。未运行游戏、编辑器或验收测试，听感由用户确认——重点：Crawl 循环在墙面爬行时的体感、Pounce 落地点对位、Bite 0.45 s 合咬与实机接触窗。
