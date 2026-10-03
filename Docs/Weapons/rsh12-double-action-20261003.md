# RSH-12 双动重制与接入（2026-10-03）

> 用户已否定本版握持与动作。本页保留历史制作和保存记录，不能作为合格动作母版。当前改为 [恢复 715 原生动作](rsh12-native715-20261003.md)，视频仅参考镜头抖动。

用户恢复制作并将设计改为双动，参考 [BV1vh4HejEUF](https://www.bilibili.com/video/BV1vh4HejEUF/) 的 0–22 秒。此次先制作握持与位置，再制作开火、ADS、换弹、音效和枪口表现。旧单动拨锤方案已被本次设计取代，不应继续按旧暂停记录恢复拨锤。

源码、制作源和新 UE 资产均已保存，`FPSGAMEEditor Win64 Development -Module=FPSGAME` 后台构建成功。未运行游戏、试听、测试、截图或验收渲染；实际观感与接触效果由用户测试，不能据此声明 100% 还原。

## 本次实现

- **握持与构图**：沿用 V7 裸手及最新枪体／机械轴注册；用完整混合蒙皮求食指与扳机、护圈的相对位置，保存单持和左右双持握持。单持腰射与 ADS 共用握点；腰射组件位置与旋转按视频前后瞄点、弹巢构图做透视拟合，保留腕部在镜头前方的约束。ADS 继续使用枪械机瞄校准。
- **双动开火**：重制单持腰射、ADS、双持左右开火；不再在射后进行拇指拨锤，不再因拨锤强制退出 ADS。扳机、击锤和五发转轮使用同一短机械段，开火恢复源时长为 0.4 秒。长按射击方式仍服从现有半自动输入规则。
- **后坐与镜头**：作者动画承担主要枪口上跳和回落，降低单持运行时弹簧叠加；RSH 单独调整镜头抖动、腰射／ADS 的 FOV 冲击。开火动作不再被旧拨锤权重压低。
- **单持换弹**：新增五发速装器几何和普通／空仓完整换弹动作，包含开巢、竖枪、左手退壳、取速装器、压入、释放、抽离、甩回闭巢和回握。普通时长约 4.167 秒，空仓约 4.333 秒；退壳、补弹、闭巢和声音统一使用源动作时钟。最后一版退壳手掌按当前枪体坐标修正，已再次导入保存。
- **声音与视觉**：八段声音从用户指定视频混音裁切、滤波及调整增益，包含开火和七个换弹接触声；移除射后拨锤声。现有枪口特效池为 RSH 调整闪焰尺寸、热量与余烟，不新增常驻特效循环。
- **数据接入**：新网格延续裸手和装备外观映射；RSH 物品及枪匠描述改为双动，更新开火间隔、普通／空仓换弹基础时长。其他武器保持原有分支。

参考片段是单持双手动作。**双持与法杖副手使用新握持、双动开火，换弹继续保留单手逐发装填**，没有套用需要另一只空手操作的五发速装动作。

## 资产与落盘记录

新根目录：`/Game/Weapons/RSH12/DoubleAction20261003`。实际保存 25 个资产：3 个骨骼网格、10 条动画、3 个私有握持 profile、8 个 SoundWave 和 1 个速装器材质。旧网格／动画目录保留作为历史，不再是本次运行时默认。

| 分支 | 保存内容 |
| --- | --- |
| `single` | `SK_RSH12_Manny`；idle、aim、fire、aim_fire、reload、reload_empty |
| `r` / `l` | 左右网格，各自 idle 与 fire |
| `Profiles` | `DA_RSH12_base`、`DA_RSH12_r_base`、`DA_RSH12_l_base` |
| `Audio` | Fire、Open、Eject、Retrieve、Insert、Release、Withdraw、Close |
| `Materials` | `M_RSH12_Loader` |

制作目录：`SourceAssets/RSH12DoubleAction20261003`，含 Blender 制作脚本、固定骨长解算、握持 JSON、可编辑 Blend、FBX、参考帧和音频裁切清单。其他装备／奔跑／检视动作继续复用 715 并应用私有 profile。

- `import_receipt.json`：`revision=double-action-v1`、`complete=true`，逐项记录已保存资产。`final_reload_contact_revision=gun-relative-extraction-palm` 及两条 FBX 散列记录最终换弹重导入。
- `build_receipt.json`：`status=Succeeded`，基础 DLL 为 `Binaries/Win64/UnrealEditor-FPSGAME.dll`，保存时间 `2026-10-03T14:12:08.5970974Z`，大小 21,100,032 字节。
- 构建日志：`Saved/BuildEditor/rsh12-double-action-20261003.log`。
- 导入使用项目后台 commandlet 和现有互斥；本轮未主动打开或重启 UE 编辑器。

## 制作入口与边界

`author_double_action.py -- single grip` 先保存握持，`-- single motion` 使用该握持烘焙动作和网格；`r`、`l` 为左右分支。`author_audio.py` 制作八段声音。`import_assets.py` 导入保存整组，`import_reload_contacts.py` 保存最后的单持换弹修订；`publish_catalog.py` 在资产已保存后更新 RSH 数据。后台构建入口为 `build_editor.ps1`。这些入口用于后续制作，不是自动验收脚本。

视频提供的是二维画面和混合音轨。看不到的手掌背面、三维深度及与本地模型不同的比例均按本地骨架适配；新动作并非原游戏动画文件。视频声音含环境混音，八段衍生音频的裁切来源及处理记录在 `Audio/manifest.json`，公开分发许可尚未建立。

当前交付是已接入、已保存、已构建的实现；握持穿插、机瞄构图、换弹接触、抖动强度和音画观感尚无本轮游戏实测结论。
