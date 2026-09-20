# 双手持斧待机（Kimodo 种子 + 项目 IK 落地，2026-09-19）

用 NVIDIA Kimodo 文本生成动作给伐木斧做一条**双手持斧待机**手部动画。按技能登记的规定路径落地：
Kimodo 只提供"非接触类上身氛围"（呼吸与重心摆动），双拳位置仍由项目自己的手臂解算器锁到斧柄上。

**当前制作版本：横持 H3（斧刃朝外、抓握位置微调），已导入生产待机，见文末。用户认可 H2 的整体方向，要求继续修正刃向与轻微穿模；H3 尚待用户测试。下方竖版、横持 H1 为历史记录，不作为用户已接受的握姿。**

## 接入方式（2026-09-19，用户指定"只接待机"）

用户决定先只换待机做实测。接入做法是**就地替换**生产待机资产，不动代码、JSON 与重编译：

- 游戏装备斧头后播放的 Idle 由 `tool_animation_prefix + "Idle"` 在运行时拼出
  （`ProductionToolComponent::RefreshHeldTool` → `HarvestMotionPath`），即
  `/Game/Items/ProductionTools/GripMotion20260913/A_Harvest_Axe_Idle`。
- `Tools/Production/replace_axe_idle.py`（编辑器内通道执行）把双手片段导入覆盖该路径：
  3.0 s、150 fps 采样、压缩档 `BC_M4Viewmodel`、绑定 `SK_Harvest_Axe_Skeleton`。
- 旧版 1.6 s 单手待机备份在 `SourceAssets/KimodoAxeIdle20260919/Before/A_Harvest_Axe_Idle.uasset`
  （SHA-256 见 `idle-replacement-backup.json`），用同一个脚本指向该 FBX 即可还原。

**其余四条（Walk / Equip / Swing / HitRecover）仍是单手**，它们与双手待机的一致性没做，属于玩法和接触动作范围。

## 生成（Kimodo）

| 项 | 值 |
| --- | --- |
| 模型 | `kimodo-soma-rp-v1.1-f32.gguf`（动作）+ `Llama-3-Kimodo-Q8_0.gguf`（文本） |
| backend | Vulkan（RTX 3080 Ti），90 帧 / 30 步 |
| seed | **4242**（复现必须同 seed） |
| prompt | `A person stands still with both hands gripping the handle of a large two-handed axe, holding it diagonally in front of the body with the head of the axe resting near the right shoulder, keeping the upper body relaxed, breathing subtly with a calm idle stance.` |
| 产物 | `D:\FPS3D\kimodo.cpp\output_fp\fp_axe_idle2h\`（`animation.glb`、`animation.bvh`、原始 f32 缓冲） |

输出是整身 30 关节 SOMA 骨架、30 fps、带根位移；**无手指关节、无接触约束**——这正是它只能
做氛围层的原因。检查：双手（LeftHand/RightHand）全程保持刚性间距，胸部姿态最大偏转 3.51°、
位置摆动 2.9 cm，确认为"抱着一个刚体轻微呼吸"的动作。

## 落地（项目解算）

`SourceAssets/KimodoAxeIdle20260919/build_two_hand_axe_idle.py`：

1. **起始姿态**取已验收的 `A_Harvest_Axe_Idle` 第 0 帧（右手既有握点、手指姿态原样保留）。
2. **左手上柄**：把右手姿态**跨工具局部 X 轴（左右轴）镜像**，再沿柄上移 10 cm。
   - 试过两种错解并已排除：**跨"手腕偏移方向"镜像**会把左手翻到柄的另一侧（实测离轴 15.6 cm）；
     **绕柄轴转 180°** 会让左拇指朝下。正确的是解剖学镜像——两手同在柄后方、拇指同朝上。
   - 脚本内自检：左手必须与右手离轴距离相同、X 分量反号、Y 分量一致（`left_hand_check`）。
3. **持握向身体中线平移**：左肩与右肩相距 0.4 m，单臂展长只有 0.55 m，原单手位置左手够不到柄。
   脚本按 5% 步长搜索"能同时让两臂留出 4 cm 余量的最小平移"，取到 `(-0.12, -0.08, -0.004) m`
   （左臂余量 4.8 cm、右臂 20.0 cm、双手间距 13.1 cm）。**这是几何限制，不是审美选择。**
4. **氛围层**：提取 Kimodo 胸部的逐帧位置/旋转增量，做左右手坐标系转换（Kimodo 面朝 -Y / 右为 -X
   → 视模面朝 +Y / 右为 +X），位置 ×0.60、旋转 ×0.55，两端用 `sin²` 包络归零使片段可循环。
5. **烘培** 150 fps（3.0 s = 450 帧），四元数符号连续化，导出仅含骨架的动画 FBX。

量化对比（同机位，`compare_with_single_hand.py`）：

| 指标 | 单手版（现有） | 双手版（本次） |
| --- | --- | --- |
| 工具位置包络 | — | 0.80 / 1.48 / 0.31 cm |
| 右手离柄轴 | 7.84 cm | 7.84 cm |
| **左手离柄轴** | **46.4 cm（垂在身侧）** | **7.84 cm（握在柄上）** |
| 双臂过伸 | 0 | 0 |

## 导入与验收

生产资产：`/Game/Items/ProductionTools/GripMotion20260913/A_Harvest_Axe_Idle`（3.0 s，150 fps 采样，
压缩档 `BC_M4Viewmodel`，绑定 `SK_Harvest_Axe_Skeleton`）。替换回执 `idle-swap.json`。

新进程读回（`Tools/Production/verify_replaced_idle.py`）：Idle 长 3.0 s、前臂旋转摆幅 4.86°、
左手 1.94°（确认片段含真实动画而非空轨）；同组 Walk 0.8 / Equip 0.32 / Swing 0.68 / HitRecover 0.44 s
与矿镐五条全部保持原样（文件时间戳 09-13 未变）。

（早先还导过一份候选副本 `KimodoAxeIdle20260919/A_Harvest_Axe_Idle2H`，内容已覆盖到生产路径，该副本已删除。）

**游戏内表现未测试**，需要用户实机判断构图与力度。Blender 预览（游戏口径：垂直 75° FOV、
视模在相机右 7 cm 下 7 cm）在 `Build/Preview/`。

## 重建入口

1. 在 Kimodo 检出目录（本机 `D:\FPS3D\kimodo.cpp`）按 `INSTALL-WINDOWS-NOTES.md` 设 PATH，跑 `kmd-generate.exe`（参数见上表）。
2. `python scripts/export_glb.py --motion-dir output_fp/fp_axe_idle2h --output …/animation.glb`。
3. `SourceAssets/KimodoAxeIdle20260919/extract_sway.py` → `sway.json`。
4. `build_two_hand_axe_idle.py` → 作者源 blend + 动画 FBX。
5. `Tools/Production/replace_axe_idle.py` → 覆盖生产待机资产。

依赖：`BattleAxeReplace20260919/Viewmodel/BattleAxe_SingleHand_Editable.blend`（斧头视模作者源）、
Kimodo 权重与两个 exe。

## 第二版：横向持握重抽（2026-09-19，用户要求"横向、斧头向外、左手在下右手在上靠金属"）

用户否定第一版（竖直斜持），要求改为**横向持握**。已重抽并替换生产待机。

**生成**：新 prompt（"holding a heavy two-handed tool horizontally in front of the chest…"），
tested seeds 2025 / 8888 后取 **seed 8888**（每帧位移峰值 0.36 cm、旋转 1.5°/帧，比 2025 更平滑；
首版 prompt 的 seed 7777 胸部转了 30°+，像转身，已弃）。
Prompt 留在 `kimodo.cpp/prompts/fp_axe_horiz_calm.txt`，产物 `output_fp/fp_axe_horiz_s8888/`。

**姿势构造**（`build_horizontal_axe_idle.py`，与竖版同一套解算器）：

- 手柄轴重新定向：`WPN_root` 局部 Z 原本指向斧头，改成指向玩家右侧 + 前倾 -0.10 + 上抬 14°。
- 右手沿柄移到 **+0.26 m**（约柄上 52 cm，紧邻金属头下方）；左手在该点**下方 0.12 m**（约 40 cm）。
  两手仍用已验收的包握（左手为解剖学镜像），沿柄平移而非重新拟手型。
- 持握整体位移 **(-0.25, 0.42, 0.24) m**：这是按**游戏相机画面框**迭代出来的——相机在
  `(-0.07, 0, 0.07)` 朝 +Y，竖版的居中位置会让横向的斧身捅穿近裁剪面并出画，最终位置让
  柄端/手握/斧头在帧内 x −0.11…+0.46、y −0.09…−0.43。
- 双臂零过伸（右余量 0.30 m、左 0.086 m）。

**量化**：右手离柄轴 0.075 m、左手 0.075 m（一致）；两手间距 0.14 m；工具位移包络 ≤1.3 cm。
UE 读回：3.0 s、前臂旋转摆幅 5.12°、左手 3.94°，其余四条与矿镐时间戳未变。

**回退**：竖版两手持握备份 `Before/A_Harvest_Axe_Idle_vertical2H.uasset`（散列见
`vertical2H-backup.json`）；更早的单手版仍在 `Before/A_Harvest_Axe_Idle.uasset`。

## 第三版：横持 H2，修正接触与腕臂（2026-09-19）

用户反馈现有待机持握不符合预期，本轮先修正待机基础姿态；保持采集时序，其他四条动作待基础持握确定后继续统一。未启动游戏、未渲染、未执行测试或验收。

### 原因与修改

- H1 转动斧柄后，双手只沿新柄轴平移，没有带上同一个旋转。H2 在工具局部空间建立两只手的接触关系，所有帧均以 `hand = tool_frame × grip_local` 求值。
- 左手按工具平面反射位置，同时通过左右骨骼的 rest 坐标映射姿态；不再把工具反射矩阵直接用于任意骨骼坐标的旋转共轭。
- H1 的平移搜索与最终应用混用了工具局部空间和骨架空间。H2 使用单一骨架空间持握原点，取消该搜索；两骨求解使用自然向下、向外的肘部方向。
- 新握位从战斧实际网格截面取得柄心、局部切向和粗细差异，整手沿切向适配，保留原有手指骨长、局部关节位置和抓握弯曲。整手绕柄角度只在基础姿态求解一次，呼吸期间不重新选角。
- 前臂由掌面方向直接构造完整骨段旋转，twist 辅助骨随所属骨段保留完整 rest-local 关系，取消主骨完整旋转、辅助骨分数旋转的混用。
- 作者场景相机原点改为 `(0, 0, 0)`，对应当前工具组件非冲刺时的零相对位移；旧预览假定的右 7 cm、下 7 cm 不再沿用。只保存机位，没有输出预览。

### 制作参数

参数集中在 `SourceAssets/KimodoAxeIdle20260919/horizontal_idle_v2.json`，供后续按用户反馈调整：

| 参数 | H2 |
| --- | --- |
| 待机长度 / 烘焙 | 3.0 s / 150 fps |
| 柄轴抬角 | 8°，斧头朝玩家右侧，并略向前 |
| 刃口 | 朝下并向身体外侧前倾 25° |
| 右握位 | 相对旧握点沿柄 +30 cm，再适配实际截面 |
| 左右握位沿柄间距 | 22 cm（不是双腕空间距离） |
| 工具原点 | 骨架空间 `(-0.14, 0.43, -0.21) m` |
| 肩带初始支撑 | 前送 2.5 cm、下沉 1.5 cm |
| 呼吸位移 / 旋转系数 | 0.10 / 0.08，保留原 3 秒包络 |

这些是制作参数，不是视觉或人体工学校验结论。H1 原文的“双臂零过伸、双手间距约 14 cm”与其 `BuildH/*-build.json` 不一致：该生成记录为双腕间距 7.52 cm、求解超出可达范围补偿右 8.283 cm / 左 10.475 cm。旧文字不能作为后续优化基线。

### 作者与接入入口

- 制作脚本：`SourceAssets/KimodoAxeIdle20260919/build_horizontal_axe_idle_v2.py`；后台运行即生成 Blend、动画 FBX 和制作参数记录，不调用渲染或测试。
- 可编辑源：`SourceAssets/KimodoAxeIdle20260919/BuildH2/A_Harvest_Axe_Idle2H_H2_Editable.blend`。
- 动画导出：`SourceAssets/KimodoAxeIdle20260919/BuildH2/Export/A_Harvest_Axe_Idle2H_H2.fbx`。
- 导入：`Tools/Production/replace_axe_idle.py` 当前指向 H2，替换生产 `/Game/Items/ProductionTools/GripMotion20260913/A_Harvest_Axe_Idle`，不改物品 ID、网格、声音或采集参数。
- H1 生产待机与替换记录备份：`SourceAssets/KimodoAxeIdle20260919/BeforeH2/`；原 `BuildH/` 作者源和 FBX 保留。

本轮只调整 Idle。Walk / Equip / Swing / HitRecover 仍为旧单手动作；切换时的姿态衔接未在本轮处理，后续以用户确定的待机为基准接续。采集总长 0.68 s、接触 0.24 s 不变。导入状态以 `idle-swap.json` 中的 H2 回执为准；游戏表现由用户测试。

## 第四版：横持 H3，斧刃朝外与毫米级接触微调（2026-09-19）

用户反馈 H2「方向对了」，继续要求斧刃朝外而非朝下，并微调双手与斧柄的轻微穿模。

- 刃向参数从相对向下前倾 25° 改为 90°，指向玩家前方外侧；柄轴仍抬 8°、沿柄握位间距仍为 22 cm，整体持握原点与呼吸参数不变。
- 从 `BuildH2/authoring.json` 的两手接触矩阵保留 H2 腕向，不重新搜索整手绕柄角度。转斧刃后，按新截面切向及径向粗细重新放置两手；只对弯柄切向差异做小幅腕向适配。
- 接触退让量：右手沿柄心至手腕的径向外移 3.5 mm，左手 3.0 mm；手指姿态、关节局部位置、骨长和缩放保持原样。此处是制作调整量，不宣称已经消除所有穿模。
- 参数：`SourceAssets/KimodoAxeIdle20260919/horizontal_idle_v3.json`。重建：`build_horizontal_axe_idle_v2.py -- horizontal_idle_v3.json`（Blender 的 `--` 后传配置文件）。不带参数仍重建 H2。
- 可编辑源与 FBX：`BuildH3/A_Harvest_Axe_Idle2H_H3_Editable.blend`、`BuildH3/Export/A_Harvest_Axe_Idle2H_H3.fbx`；H2 作者产物保留，替换前生产待机备份在 `BeforeH3/`。
- 经当前编辑器内 Python 通道导入并保存生产 `A_Harvest_Axe_Idle`，回执 `idle-swap.json` 的版本为 H3。只替换 Idle，其余动作与采集时序不变。

未渲染、未启动 PIE、未测试或验收；由用户实机确认刃向及抓握接触。

## 后续攻击制作

2026-09-19 接续制作双手右上蓄势、向左挥砍，保留本页 H3 待机与抓握，更新 Swing / HitRecover 及斧头时序；见 [伐木斧双手攻击 V1](axe-two-hand-attack-20260919.md)。上文“其他四条仍为旧版”描述的是当时的待机交付范围，当前只有 Walk / Equip 尚未统一。
