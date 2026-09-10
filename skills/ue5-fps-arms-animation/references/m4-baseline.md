# M4 当前基线（2026-09-10）

这是已执行案例的定位表。复用前读宿主 `Source/FPSGAME/FPSGAMECharacter.cpp`、`Source/FPSGAME/Weapons/FPSGunplayAnimInstance.cpp` 与最新运行日志；本表不覆盖后续修改。不要把旧失败报告、候选或同名 Final 目录直接当当前状态。

## 实际运行资产

| 用途 | 已核对路径 / 合同 |
| --- | --- |
| 手与 M4 运行网格 | `/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416` |
| 普通弯弹匣非空仓换弹 | `/Game/Weapons/M4TacticalTossFinal/A_M4_HK416_reload`，2.1 s，1009 个 480 Hz 样本 |
| 普通弯弹匣空仓换弹 | `/Game/Weapons/M4SlapImpactFinal/A_M4_HK416_reload_empty`，2.7 s，1297 样本 |
| 装备/切枪拉栓 | `/Game/Weapons/M4WrapGripFinal/A_M4_HK416_equip_charge`，源 38/60 s，305 样本，运行 0.72 s |
| 装备声音 | `/Game/Weapons/M4AnimationAuditFinal/S_HK416_Equip` |
| 拍击/枪机释放声音 | `/Game/Weapons/M4AnimationAuditFinal/S_HK416_BoltRelease` |
| 其他 HK416 开火/机械声音 | `/Game/Weapons/M4HK416Audio`；具体映射查 `LoadAKMSound`，不要按文件名猜 |
| 可编辑 FK rig | `/Game/Weapons/M4ContactImpactFinal/CR_M4_ContactImpact` |
| 普通 MAT 序列 | `/Game/Weapons/M4TacticalTossFinal/LS_M4_TacticalToss_reload` |
| 空仓 MAT 序列 | `/Game/Weapons/M4SlapImpactFinal/LS_M4_SlapImpact_reload_empty` |
| 装备 MAT 序列 | `/Game/Weapons/M4WrapGripFinal/LS_M4_WrapGrip_equip_charge` |

idle/aim/fire 等以及弹鼓分支没有随本次两个换弹微调整体替换。必须按实际加载分别确认，不能把普通弹匣通过结果说成弹鼓也已验收。

## 接触、声音与时长

表中帧均为作者 60 Hz 逻辑帧，不是 480 Hz 序列的键索引。

| 动作 | 出匣 | 新匣插入 | 压实 | 末次拍击/释放 | 保持抓握 |
| --- | --- | --- | --- | --- | --- |
| 普通 | 29 / 0.483333 s | 76 / 1.266667 s | 95 / 1.583333 s | 无 | 61–98 |
| 空仓 | 21 / 0.350000 s | 54 / 0.900000 s | 80 / 1.333333 s | 130 / 2.166667 s | 43–88 |

普通和空仓均保留甩飞旧弹匣，再从镜头外取新弹匣、完整抓握插入。非空仓保持枪机闭合，直接回待机；空仓枪机在释放前保持约 35 mm 后移，130→132 帧闭合，末次挥手 126.667→130 帧为 1.5 倍速度，接触后轻震 0.17 s。

普通换弹复用空仓前段，normal→empty 对应表为 `(0,0),(8,8),(28,20),(29,21),(43,35),(61,43),(76,54),(95,80),(98,88)`；随后回接普通 98–126 帧，枪根在 98–110 帧平顺过渡。原甩匣飞离速度保留，声音按普通时钟对齐。此表只用于该两条源动作。

## 作者源与证据

以下目录均在 `D:/FPS3D/FPSGAME/SourceAssets/`：

- `M4TacticalToss20260910/`：最新组合可编辑 `M4_Hand_MAT_Editable.blend`，包含普通更新、上一版空仓与装备；`author_toss.py`、普通 FBX、导入/校验脚本、`acceptance.json`、实际游戏视频。当前普通运行使用其资产。
- `M4SlapImpact20260910/`：空仓 1.5 倍拍击和短震，`author_slap.py`、空仓 FBX、`acceptance.json`。当前空仓仍单独引用该已验证资产，不能因最新组合 Blend 在另一目录就重导所有动作。
- `M4WrapGrip20260910/`：自然抓握/拇指扫掠/前臂修正，`apply_arm_reference.py` 选原 `M4_reload` 帧 146；`wrap_fit.json`、`finger_anatomy.json`、`apply_entry_clearance.py`。这里旧普通动画已被 TacticalToss 替代，旧空仓被 SlapImpact 替代，装备仍在用。
- `M4HandMATRepair20260910/`：MAT 手册入口与实测 `mat_nudge.json`，是工具经验来源，早期候选动画不是当前发布源。

最后一次普通更新验收 `Saved/GunplayUpgrade/m4-tactical-toss/result.json` 为 50 pass / 0 fail。手/弹匣 253 个源 120 Hz 采样无相交；保存后 960 Hz 检查右手相对枪漂移约 0.160 mm、抓握约 0.122 mm。普通首尾待机仍有各 9 对手/枪身表面接触，不宣称整网格零相交。

空仓轻震更新 `m4-slap-impact` 为 50 pass / 0 fail；修改段 65 个手/弹匣采样无相交，拍击帧仍有旧基线 34 对手/枪身表面接触。装备另有 WrapGrip 的独立 21 项回归。以上都是各次运行记录，不能合并计数当作本次新测试。

两条最新完整录制各检测 11 个机械音；视频为 20 Hz 截图与同次实际混音，少量缺图沿用上一帧，详情见 Delivery/preview_manifest.json。素材波形相关、日志和实际画面合看；音频缓冲时差不等于零延迟。

## 已解决且不能恢复的做法

- 不把扳机/弹匣/枪机拆成失去父子约束的平级骨架。
- 不恢复 Cubic 旧手模作为当前 UE 外观标准；沿用当前运行网格的手与手套。
- 不用掌骨大旋转和指尖误差最小化换取扭曲“握紧”。
- 不用手还没抓住就同步抬匣、插好后直接穿匣转腕的路径。
- 不恢复非空仓左手取下旧弹匣的旧动作。
- 不把空仓拍击接触改成僵硬的穿机匣按压；保留已确认的快挥手和短受力。
- 不因短机械音时长小于某帧迟到量就直接丢弃该音效；见 [验收和事件时钟](validation.md)。
