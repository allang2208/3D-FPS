# M4 枪托砸击（快速进战·步枪版，2026-09-18）

范围：只做 M4（用户 2026-09-18 指定）。上一版步枪枪托砸击（2026-09-17 V1/V2）实机否决后退役，
本轮按 [废案记录](../Rejected/rifle-stock-melee-20260917.md) 的恢复入口重做。

## 与上一版的路线差别

| | 2026-09-17 V2（已废） | 2026-09-18（本轮） |
| --- | --- | --- |
| 动作来源 | 运行时程序化姿态层（`ApplyRifleStockMeleePose` + 手写偏移） | **作者源 clip**（Blender 逐帧 120 Hz 烘焙，整枪刚体搬运写在 `WPN_` 骨上） |
| 参数落地 | 拍脑袋参数/拟合曲线直接进 DLL | 关键帧表留在 `SourceAssets/RifleStockMelee20260918/animation.json`，可编辑源可复现 |
| 视觉比对 | 没有，交付即实测 | 交付前先出 Blender 对位胶片（`Preview/Base_strip_vs_reference.png`） |
| 换握把 | 假设"相对当前 idle"，实际未验证 | 六个握把配置各一条 clip，握把关系取各自待机源 |

作者源路线与已获用户确认的手枪握把砸击（DW715 V9/V10）同族：**枪的运动写在 `WPN_root` 上，
手由握把关系带动**，因此"枪不跟手/漂移/缩放"这一类问题在构造上不成立。步枪版与手枪版的差别是
双手全程持枪（右手握把 + 左手护木都随枪刚体走），不松手、不开指。

## 参考读谱

参考 `BV13K421e7Rw` 1:05–1:07 的 AK47 枪托近战（本机留档 `D:\FPS3D\test\uzi_ref\uzi_ref.mp4`，
不入库）。逐帧 1/15 s 抽帧 44 张（64.80–67.67 s），两个完整挥击周期。

读到的动作语言（**2026-09-18 晚按 30 fps 原生帧 + 夜景提亮重读，并按用户口述修正**）：
常态低持 → 整枪横过来向一侧蓄势（枪身几乎横躺在画面里）→ **水平横扫过画面中心** → 收势回低持。
全程双手持枪。
**只借动作语言，未提取 COD4 任何动画资产。**

### 方向修正 A → B → C（2026-09-18 晚）

第一版（**A**：抬枪口 → 整枪越过竖直往下扫）经用户实机判定不符预期。按 1/30 s、1280×720 原生帧、
提亮口径 `out=clip(2.4·in+40)` 重读后出了 **B 版（抬枪托的上下版）**；
用户随后指正 **"是横向枪托攻击"**——不是上下劈。定为 **C 版（默认）**：
**俯仰基本不动（5°〜−4°）、偏航做大（+46° → −12° → −36°）**，整枪在水平面内横躺扫过画面，
接触 0.348 s 时枪身横过画面中心。A/B 作为对照参数保留在脚本里（`--variant A|B`）。

两点过程教训（已写进作者源目录 README）：

1. **预览相机口径要对齐游戏**：游戏为垂直 75° FOV、视模相对相机 (右 7 cm, 下 7 cm)
   （`M4HipViewmodelLocation=(0,7,-7)`cm）。之前预览用 90° 水平 + 相机在骨架原点，框景偏窄，
   把"枪托离镜头近"误判成严重穿模。
2. **枪托离镜头有下限**：视模原点在骨架上时枪托离相机只有 15 cm，任何"把枪托抬到镜头前"的写法都会糊住画面；
   B 版靠"先前推、再抬托"把枪托稳定保持在 0.4 m 外，并可用 `tune_motion.py` 离线看屏幕坐标。

## 实现

- **作者源**：`SourceAssets/RifleStockMelee20260918/author_quickcombat.py`，六个握把 profile
  （Base/Drum/Angled/Vertical/Canted/Prism）；**C 版（横向横扫）**总长 0.72 s、接触 0.348 s、
  0.348→0.383 为 3 帧接触顿帧（时间轴：起手 0.058 / 蓄势 0.20–0.26 / 接触 0.348 / 跟随 0.511 / 收势 0.72）；
  自检不变量 `|WPN_root − hand_r|`、`|WPN_root − hand_l|` 全程恒定（帧表见 `animation.json`）。
  运行时常数按 clip 总长比例换算，改节奏只重出作者源、不用改代码。
- **对位预览**：`render_preview.py`（视模视点：垂直 75°／13.2 mm，相机 = 骨架原点左 7 cm 上 7 cm）+ `make_preview_strip.py`
  → `Preview/<profile>_strip_vs_reference.png`（上：本工程 clip 关键帧；下：参考同段帧）。
- **导入**：`import_quickcombat.py`（编辑器在跑走 `ue_python_exec.py` 远程执行，关闭时走 `-run=pythonscript`），
  骨架 `SK_M4_FoldingSights_HK416`、压缩 `BC_M4Viewmodel`、落点 `/Game/Weapons/M4StockMelee20260918/<profile>/`；
  C 版重导读回 6/6、`length=0.7167`。
- **接线**：
  - `AFPSGAMECharacter::TriggerRifleStockMelee()`（新）+ `ResolveRifleGripProfile()`（与战术冲刺共用解析）
    + `RifleQuickCombatClip()`（按 profile 惰性加载六条 clip）；状态复用 `EAKMWeaponState::QuickCombat`。
  - `UFPSQuickCombatComponent::ConfigureForRifle()`：同一套时钟/冷却/修炼/击退眩晕，只换
    命中探针与镜头常数；探针 `UFPSCastingMeshComponent::GetRifleStockMeleeProbe()` 取**当前动画姿态**的
    枪身前段（枪口沿枪轴回撤 12 cm），与画面同源；步枪冲量/镜头常数在 `Skills/QuickCombatRifleMotion.h`。
  - 路由：`UColdSteelStatusModel::TriggerQuickCombat()` 增步枪分支；修炼走 `rifleMastery`（`Shot.bRifle=true`）。
  - 起手音/命中音沿用快速进战同一枚（`S_QuickCombatSwing` / `S_MeleeHit_Quick`）。
- **数值**：伤害/距离/眩晕/冷却完全沿用 `quickCombat` 技能定义，未为步枪开新数值合同。

## 编译

- Game 目标（`Build.bat FPSGAME Win64 Development`）**Result: Succeeded**，日志
  `Saved/BuildEditor/game-build-console.log`（本轮改动的四个 cpp 均在其中编译）。
- Editor 目标未跑完整 UBT（编辑器被并行会话占用）。改为编辑器内 Live Coding 编译，
  `Saved/Logs/FPSGAME.log` 12:33:14 `Live coding succeeded`。
  重启编辑器后由 UBT 补一次完整 Editor 构建，`Binaries/Win64/UnrealEditor-FPSGAME.dll` 才与源码同版。

## 未测试范围

## 状态：暂停待办（2026-09-18 收尾）

用户实机后判定 C 版仍不符预期，要求**暂停并记为待办**。当前落地状态（可随时继续）：

- 作者源、六握把 clip、接线、编译、导入、文档齐全；A/B 两版只作为脚本里的对照参数，**没有产生需要归档的废案文件**
  （同名 FBX/blend 已被 C 版覆盖；2026-09-17 那批旧废案已在 `Docs/AssetArchives/rifle-stock-melee-retired-20260917.json` 记录）。
- 引擎侧资产（`Content/Weapons/M4StockMelee20260918/*.uasset`）按仓库规则只在本机保留，不公开提交。

### 恢复入口（下次从这里开始）

1. 改参数：`SourceAssets/RifleStockMelee20260918/author_quickcombat.py` 的 `MOTION_C`（时间轴 `TIMES` 与六个握把共用）。
2. 先看数值：`python tune_motion.py C`（打印枪托/枪口的屏幕坐标与到相机距离，别直接进 Blender 试）。
3. 出对位胶片：`render_preview.py`（已按游戏口径：垂直 75°、相机在骨架原点左 7 cm 上 7 cm）+ `make_preview_strip.py Base --reference`。
4. 覆盖导入：编辑器在跑用 `Tools/AssetPipeline/ue_python_exec.py --script import_quickcombat.py`；关闭时用 `-run=pythonscript` commandlet。
5. 参考帧：`SourceAssets/RifleStockMelee20260918/Reference/`（`dense_frames` 1/15 s、`f30` 1/30 s 原生 1280×720、`Bright` 提亮读图、`Sheets` 3×3 读谱）。

### 未判读 / 待解决

- 横向横扫的**幅度与节奏**仍与参考有差距（本轮只对齐了方向与动作语言）；需要真机逐项比对，不适合继续盲调。
- 命中探针取枪身前段（半径 34 cm）在实机距离下是否打得中、击退/眩晕与 12 s 冷却的手感。
- 六个握把配置（含弹鼓/垂直握把）横扫时的遮挡与穿模都还没判读。
