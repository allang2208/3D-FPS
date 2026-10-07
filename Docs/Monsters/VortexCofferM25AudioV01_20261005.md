# M-25 涡电匣音效 V01（2026-10-05）

按用户要求为涡电匣制作并接入全套音效，策略优先复用本地已筛选素材：有机层全部来自 M-10 沉匣音效工作已下载的 CC0 freesound 源（`SourceAssets/M10ChenXia20261003/AudioScout`），电极电声层（噼啪、嗡鸣、放电扫频、雷裂）全部由 numpy 本地程序合成，未新增外部素材与许可负担。发布文档已声明本轮不加音效；本轮为随后的独立授权制作。

## 声音与动作合同对应

| 事件 | 资产 | 时长 | 触发合同 |
|---|---|---:|---|
| 待机共鸣 | S_M25_Idle | 3.6 s 循环 | 存活常响（躯干 body_05，1400 cm 衰减） |
| 爬行 | S_M25_Crawl | 2.6 s 循环 | 着地且速度 >4 cm/s（1500 cm） |
| 背部电极 | S_M25_Crackle | 4.0 s 循环 | BackElectric 可见放电期间，音量随电弧峰值 |
| 撕咬 | S_M25_Bite | 0.8 s | Bite 状态激活边沿，合咬峰值 0.33 s 对位 0.30–0.38 s 实机接触窗 |
| 闪电蓄力 | S_M25_Charge | 0.6 s | Magic 进入 Lightning 相位（0.55 s 蓄力），打断即停 |
| 雷枪蓄力 | S_M25_LanceCharge | 1.7 s | ThunderLance 相位（1.6 s 蓄力 + 瞄准锁定） |
| 雷枪释放 | S_M25_LanceRelease | 1.8 s | MulticastImpact 雷枪分支（普通闪电保留 S_LightningCast1） |
| 受击 | S_M25_Hit | 0.75 s | StartHitPresentation（Combat 复制镜像，各端播） |
| 死亡 | S_M25_Death | 3.0 s | OnRep_Death，塌落点 1.35 s、电极断电尾音 |

## 实现位置

- 声音属性集中在 `AVortexCofferM25` `M25|Audio`（九个 `EditDefaultsOnly`），组件经 `Monster` 引用读取；BP 写入走 CDO。
- 循环：`IdleVoice`/`CrawlVoice`（actor Tick 驱动 `UpdateLoopAudio`）、BackElectric `CrackleVoice`（socket_electric_00，随可见性启停）。
- 一次性：`PlaySoundAtLocation` + 运行时 `USoundAttenuation`，专用服务器全部跳过。
- 制作源与许可：`SourceAssets/M25VortexCoffer20261004/AudioV1/`（`prepare_audio.py` 确定性合成，`Records/audio_source.json` 逐源记录）。

## 状态

已完成：双 target 构建通过，9 个 SoundWave 落盘 `Audio/AudioV1`（Idle/Crawl/Crackle 循环、FORCE_INLINE），`BP_VortexCofferM25` CDO 写入 9 个声音引用；回执在 `SourceAssets/M25VortexCoffer20261004/AudioV1/`。游戏内试听未验证，待用户确认。
