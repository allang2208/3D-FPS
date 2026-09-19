# 双手持斧待机（Kimodo 种子 + 项目 IK 落地，2026-09-19）

用 NVIDIA Kimodo 文本生成动作给伐木斧做一条**双手持斧待机**手部动画。按技能登记的规定路径落地：
Kimodo 只提供"非接触类上身氛围"（呼吸与重心摆动），双拳位置仍由项目自己的手臂解算器锁到斧柄上。

**交付状态：已接入生产路径，待用户实机测试。**

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
