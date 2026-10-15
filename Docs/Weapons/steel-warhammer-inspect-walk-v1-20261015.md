# 战锤行走检视 V1：只转锤半段，速度与力度 ×3

**归档（2026-10-16）：** 被替代的 `InspectWalkV1/`、`InspectWalkWristV2/` 和 `InspectWalkSpeedV3/Before/` 已移入 `trash/warhammer-inspect-combo-retired-20261016/`，清单见 [归档清单](../Publication/WarhammerInspectCombo20261016/archive-manifest.json)；当前作者源为 `InspectWalkSpeedV3`（不读取旧版目录）。

**音效更新（2026-10-15 稍后）：** 用户认为效果不理想，只保留风声。两条钢铁层（`S_MeleeBlock_02`、`SW_ForgeHammerImpact`）已从 `author_cues.py` 的 `DESIGN` 移除并重新生成 `WarhammerInspectWalkCues.h`，预加载随之只剩风声；下表中两条钢铁音效已不再播放。该改动已由 18:28/18:29 的 Editor/Game 构建编入（随后本轮构建 up to date、`Result: Succeeded`，二进制中已无钢铁音效路径）。未试听。

## 当前修订 SpeedV3 + 钢铁/空气音效（2026-10-15）

用户要求移动中触发的检视转速再加倍，并加入钢铁、挥动空气的音效。L 检视不变。

- 转速：在 WristV2 基础上再 ×2（V1 的 6 倍）。出手 **2520°/s**，拨转驱动 0.019 s，自由转动 0.167 s，从蓄势到握住转满一圈 **0.185 s**（WristV2 0.371 s）；抓住时余速 630°/s，双手随锤卸力 22°。右手甩过角度保持 12°，回滚压缩到 0.097 s 以在合指前回位；右腕最大弯折 29.7°。总时长 1.29 → **1.107 s**。
- 音效（`PlayInspectCues`，按片段时钟触发，只在行走检视中播放；中途打断则后续音效不再触发）：

| 片段时间 (s) | 音效 | 音量 / 音高 | 对位 |
| --- | --- | --- | --- |
| 0.255 | 战锤挥舞风声 `S_Warhammer_NormalSwing` | 0.30 / 1.35 | 最响 10 ms 落在出手后 35 ms（转速最高处） |
| 0.323 | 钢铁清鸣 `S_MeleeBlock_02`（用户提供的格挡音） | 0.223 / 1.30 | 起音落在出手瞬间，余响贯穿转动 |
| 0.430 | 钢铁重击 `SW_ForgeHammerImpact`（用户提供的打铁音） | 0.179 / 1.20 | 起音落在双掌合拢抓住瞬间 |

  对位与电平由源音频包络测量得出（`InspectWalkSpeedV3/Audio/source_profile.json`、`cues.json`；钢铁层分别比风声峰值低 8 / 5 dB），未试听。三条资产均在已有 AlwaysCook 目录内，随战锤装备异步预加载，触发时不读盘。
- 文件：动画 `SourceAssets/SteelWarhammer20261014/InspectWalkSpeedV3/`（`Before/` 为 WristV2 正式资产与参数）；音效作者脚本 `Audio/author_cues.py` 生成 `Source/FPSGAME/Production/WarhammerInspectWalkCues.h`。
- 动画已导入保存（revision `InspectWalkSpeedV3_20261015`，`complete=true`）。Editor 构建实际编译了 `ProductionBluntInspect.cpp`、`ProductionToolMotion.cpp`、`ProductionToolComponent.cpp`；Game 构建中这三个文件已由排在前面的构建编入，本轮链接成功；两者均 exit 0、`Result: Succeeded`（16:56 / 17:06），两个二进制中均含行走检视与音效路径。未运行游戏、未试听、未测试。

## 修订 WristV2（2026-10-15）

用户反馈右手腕甩得别扭，要求减小角度。右手出手后甩过的角度由 24° 减为 **12°**（右手掌绕柄最大 +40° → +28°），停手时长按同一不回摆曲线缩为 0.019 s；右腕相对待机最大弯折 42.5° → **29.8°**（L 检视为 33°）。出手 1260°/s、转一圈 0.371 s、抓住卸力、总时长 1.29 s 及其余参数不变。

- 作者源：`SourceAssets/SteelWarhammer20261014/InspectWalkWristV2/author_inspect_walk.py`；替换前的正式资产与参数在同目录 `Before/`。
- 已后台导入并覆盖保存同一资产 `A_Warhammer_InspectWalk`（`import_receipt.json` `complete=true`，revision `InspectWalkWristV2_20261015`）。代码未改，无需重新编译。未测试。

以下为 V1 原始记录，其中"甩过 +24°""右腕 42.5°"已被 WristV2 取代。

用户确认 [L 检视 V1](steel-warhammer-inspect-v1-20261015.md) 方向正确，要求装备战锤移动时像双手剑一样自动播放检视；行走版只播放转锤的后半段，转动速度和力度都翻三倍。L 手动检视保持 V1 原样不变。

## 触发（与双手剑一致）

- 装备后 2–3.5 s、每次检视后 5–8 s 随机间隔；倒计时只在普通地面行走（速度 > 20 cm/s，非冲刺、跳起、滑铲、闪避、翻越）时推进，站立暂停计时。
- 任何动作、冲刺拖持过渡、左手施法、面板占用时不触发；起播失败 1–2 s 后重试。
- 打断规则与 L 检视相同：行走中继续，其他动作和输入立即接管。按 L 仍播放完整 V1。

## 动作（1.29 s，300 fps）

去掉 V1 的举起停留、双手来回拧和错峰抬指，只保留转锤：

| 时间 (s) | 内容 |
| --- | --- |
| 0–0.32 | 快速举到 V1 同一展示位，0.10 s 起双手同时蓄势拧到 −16°；左手 0.24 s 起松成环握 |
| 0.32–0.357 | 右手拨转 −16° → +16°，出手 **1260°/s**（V1 420°/s 的 3 倍），驱动时长按同一速度曲线压缩到 1/3 |
| 0.357–0.69 | 松握中自由转动，只减速；从蓄势到握住共 0.371 s 转满一圈（V1 1.14 s）。右手出手后甩过 **+24°**（V1 8° 的 3 倍）在 0.04 s 内停住再滚回 |
| 0.69–0.76 | 双掌在锤仍有 315°/s 时合拢抓住，手与锤一起再顺势转 11° 卸力 |
| 0.76–1.29 | 补回剩余角度并放回待机；末帧等于待机首帧 |

- 转轴、握持、松握手掌绕柄公转、肘部与手指规则全部直接复用 V1 作者脚本中的函数，展示姿态读取 V1 `authored.json`；手柄中线与 V1 不一致时脚本拒绝生成。
- 制作量化（非游戏验收）：腕部相对待机弯折变化最大 左 22.0° / 右 42.5°（右手 3 倍甩腕所致，V1 为 33°）；骨长误差 < 0.001 mm；锤体到眼最近 0.476 m；手臂表面到眼最近 0.215 m；转动全程锤头 100% 在画框内；从蓄势到卸力结束角度单调不回摆。

## 接入

- 资产：`/Game/Weapons/SteelWarhammer20261014/InspectV1/A_Warhammer_InspectWalk`（1.29 s），随战锤装备加载；缺失时只是不自动播放。
- `BeginInspect(bool bWalking=false)` 选择 `Inspect` / `InspectWalk`；`TickWalkInspect` 在本地手部表现更新中推进，节奏函数 `ScheduleWalkInspect`、`IsWalkInspectStride` 照搬双手剑（`Production/ProductionBluntInspect.cpp`）。
- 两个检视片段进出都使用 0.14 s 衔接，离开时手掌沿锤柄圆周交接。第三人称与远端没有单独的检视身体姿态，但双手与锤体按代码路径随第一人称采样显示（复核更正，未实机验证）。

## 文件

- 作者源：`SourceAssets/SteelWarhammer20261014/InspectWalkV1/author_inspect_walk.py`（`-- --plan` 只出量化）；可编辑 `Warhammer_InspectWalk_Editable.blend`；导出 `Export/A_Warhammer_InspectWalk.fbx`；参数与量化 `authored.json`。
- 导入：`import_assets.py` 等，回执 `import_receipt.json`（`complete=true`，commandlet exit 0）。构建：`build.ps1`、`build_receipt.json`。

## 交付状态

动画已后台导入、压缩并保存。本轮 Editor 与 Game 构建实际编译了 `ProductionBluntInspect.cpp`、`ProductionToolMotion.cpp`、`ProductionToolComponent.cpp`，均 exit 0、`Result: Succeeded`（2026-10-15 16:19 / 16:20）。按用户规则未启动编辑器、未运行游戏或渲染预览，未测试；行走触发频率、转速力度观感和握持由用户体验确认。
