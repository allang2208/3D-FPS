# M4 枪托砸击（快速进战·步枪版，2026-09-18）

用户 2026-09-18 指定「只做 M4」。上一版（2026-09-17 V1/V2 程序化姿态层）实机否决后已退役，
本轮按废案记录建议的路线重做：**先在 Blender 里按参考视频做对位预览，动作本体走作者源 clip**
（与已接受的手枪 DW715 握把砸击 V9/V10 同一条路线），不再有运行时程序化姿态层。

2026-09-18 晚：用户实测第一版（A 版，抬枪口再往下扫）判定不符预期；改为 B 版（抬枪托）后用户指正
**"是横向枪托攻击"**——不是上下劈，是**整枪在水平面内横扫**。据此定为 **C 版（默认）**：
俯仰基本不动、偏航做大，整枪横躺在画面里自左向右扫过（见下方"动作表"）。

## 参考读谱

参考：`D:\FPS3D\test\uzi_ref\uzi_ref.mp4`（B 站 BV13K421e7Rw，COD4 模组展示），1:05–1:07 的 AK47 枪托近战段。

- 抽帧：`Reference/dense_frames/f_001..f_044`（64.80–67.67 s，1/15 s 一帧，640×360）与
  `Reference/f30/f_0001..f_0165`（63.0–68.5 s，**1/30 s 一帧，1280×720 原生分辨率**）。
  3×3 读谱大图在 `Reference/Sheets/`；夜景提亮读图在 `Reference/Bright/`
  （口径 out=clip(2.4·in+40)，与旧读谱一致）。
- 两个完整周期（64.80–65.87 / 66.00–67.07），单周期约 0.9–1.07 s。读到的动作语言：
  常态低持 → 整枪横过来（枪身几乎横躺在画面里）向一侧蓄势 → **水平横扫过画面中心** → 回位。
  与用户口述的"横向枪托攻击"一致：不是上下劈，是左右横扫。
  双手全程持枪（右手握把、左手护木），不是手枪那种松左手。
- **只用动作语言，不取资产**：COD4 动画素材有版权，未提取任何帧数据进资产管线。

## 作者源 clip（本目录）

- `author_quickcombat.py`：按 profile 打开对应 M4 可编辑源 → 采样该 profile 的待机帧 →
  以 **整枪刚体搬运写在 `WPN_` 骨上、双手由握把关系带动** 的约定逐帧 120 Hz 烘焙
  `M4_QuickCombat_<profile>` → 导出 `Animations/A_M4_QuickCombat_<profile>.fbx`。
  关键不变量：`|WPN_root − hand_r|`、`|WPN_root − hand_l|` 全程恒定（作者源自检逐帧打印）。
- 动作表（`animation.json`，**C 版＝默认**）：总长 **0.72 s**、接触 **0.348 s**（0.348→0.383 为 3 帧接触顿帧）。
  起手 0–0.058（整枪前推 5 cm，开始偏航）→ 蓄势顶点 0.20–0.26（**yaw +46°**：枪口甩到画面左侧、
  整枪横躺）→ 横扫 0.26–0.348（yaw 从 +46° 扫到 **−12°**，枪身横过画面中心命中）→
  跟随 0.383/0.511（yaw −22°/−36°，继续向右侧带出）→ 回位 0.72。俯仰只有 5°~−4°，整段基本水平。
  参数可用 `tune_motion.py C` 离线核对屏幕轨迹（枪口 u：0.54→0.21 蓄势 →0.60 接触→0.75 跟随）。
  A/B 两个上下劈的候选仍保留在脚本里（`--variant A|B`）。
  参考单周期约 1.0 s（含镜头摆动），本工程取更干脆的一档；改节奏只改这张表，
  运行时常数按 **clip 总长比例**换算，不需要同步改代码。
- **写参数前先跑 `tune_motion.py`**：它把「枪根刚体搬运」换算成枪托/枪口在画面里的位置
  （相机按游戏口径：垂直 75° FOV、视模相对相机右 7 cm/下 7 cm），不开 Blender 也能看框景、
  避免又出现「枪托顶到镜头前把画面糊住」这类问题。`python tune_motion.py solve` 可按目标屏幕位置反解参数。
- 六个 profile（与战术冲刺同一套）：**Base / Drum / Angled / Vertical / Canted / Prism**。
  每个 profile 用自己待机源的握把关系，所以换握把不会脱手。Base/Drum 沿用战术冲刺的
  12 mm/32 mm 前移发布口径。
- `render_preview.py` + `make_preview_strip.py`：从视模视点渲染对位胶片，输出
  `Preview/<profile>_strip_vs_reference.png`（上=本工程 clip，下=参考帧）。相机口径与游戏一致：
  **垂直 75° FOV（13.2 mm/36 mm 传感器）**，位置 = 骨架原点「左 7 cm、上 7 cm」
  （对应 UE 里 `M4HipViewmodelLocation=(0,7,-7)`cm）。用错 FOV/位置会误判框景。

## 导入

- `import_quickcombat.py`：骨架取 `/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416`，
  压缩沿用 `BC_M4Viewmodel`，落到 `/Game/Weapons/M4StockMelee20260918/<profile>/`。
  编辑器在跑时用远程执行（`Tools/AssetPipeline/ue_python_exec.py --script ...`），
  编辑器关闭时用 commandlet（`-run=pythonscript`，不起第二个进程）。
  B 版重导读回 **6/6、length=0.7167**。
- **变体切换**：`author_quickcombat.py -- Base --variant A|B|C`（默认 **C＝横向横扫**；B＝抬枪托的上下版；A＝抬枪口的旧版）。

## 运行时接线

- `AFPSGAMECharacter::TriggerRifleStockMelee()`：M4 在手且非忙碌时按 profile 选 clip 播放，
  状态走既有 `EAKMWeaponState::QuickCombat`；`ResolveRifleGripProfile()` 与战术冲刺共用同一解析。
- `UFPSQuickCombatComponent`：新增步枪样式（`ConfigureForRifle`）——同一套时钟/冷却/修炼/
  击退眩晕合同，只换命中探针（`GetRifleStockMeleeProbe`：枪口沿枪轴回撤 12 cm 的枪身前段，
  读当前动画姿态而不是入场快照）与镜头常数（`QuickCombatRifleMotion.h`，动作镜头 ×1.6、冲量同级偏重）。
- `UColdSteelStatusModel::TriggerQuickCombat()`：剑 → 配重锤 / 手枪 → 握把砸击 / 步枪 → 枪托砸击。
- 修炼走 `rifleMastery`（`Shot.bRifle=true`）；音效沿用快速进战同一枚起手音与钝器命中音。

## 未做

## 状态：暂停待办（2026-09-18 收尾）

用户实机后判定 C 版仍不符预期，要求暂停并记为待办（见 `Docs/Backlog.md` M5 行与
`Docs/Weapons/m4-stock-melee-20260918.md` 的「恢复入口」节）。

- A/B 两版只存在于 `author_quickcombat.py` 的参数表里，**没有产生需要移到 trash 的文件**；
  同名 FBX/blend 是 C 版覆盖写的。
- 引擎侧 uasset 按仓库规则只在本机保留（`.uasset` 在 .gitignore 内）。
- 未实机判读的项：横向幅度/节奏、命中探针手感、六个握把的遮挡与穿模。
