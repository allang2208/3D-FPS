# 尼泊尔弯刀（Kukri）作者源 · 2026-10-20

单手近战武器 `ue_kukri` 的模型处理、第一人称动作作者源与后台导入脚本。说明与运行时接入见
[Docs/Weapons/kukri-20261020.md](../../Docs/Weapons/kukri-20261020.md)。**未做实机测试。**

## 来源与许可

| 项 | 值 |
| --- | --- |
| 原始资产 | Fab「Kukri」，作者 powers28，listing uid `0a08e297-e2d0-472b-b572-53077a548196`（发布 2026-07-07，标签 Machete/Weapon/Melee/Knife） |
| 本机原件 | `D:\FPS3D\VaultCache\FabLibrary\Kukri-0a08e297\fbx\kukri_extracted\`（`Model/kukri.fbx`，`Textures/Unreal/*` 2048 ORM 套，`Textures/PBR/*`） |
| 许可 | 以 Fab 购买条款为准；再分发许可未审核——原始 FBX/贴图与派生 `Content/Weapons/Kukri20261020` 二进制不公开提交 |
| 动作参考 | Bilibili [BV1CeYUeSE7b](https://www.bilibili.com/video/BV1CeYUeSE7b/)（Apex 班加罗尔传家宝全动作展示）；只取节奏、方向与构图，帧图在 `Saved/Reference/KukriBV1CeYUeSE7b20261020/`，不入库 |

## 文件

| 文件 | 作用 |
| --- | --- |
| `author_kukri_model.py` | Blender：导入 FBX，×1.65 放大（无挂绳 38.6 cm），拟合握柄中线，变换到握点坐标（原点=右拳握心，+Z 刀身，+X 刃口），导出 `Export/SM_Kukri.fbx`、`Kukri_Editable.blend`、`Icons/ue_kukri.png`（256×768，1×3 格）、`model.json` |
| `kmath.py` / `kukri_rig.py` | 纯 Python 变换与解算：共享剑臂骨架、右拳—刀柄锁定、伸手圆上选肘、前臂扭转按 V9 约定分给 twist_01 100% / twist_02 50%、左臂下垂出画；解剖诊断（ρ 旋前/旋后、背伸/掌屈、尺偏/桡偏） |
| `author_kukri_clips.py` | 七条 120 fps 作者动作：Idle 3.0 / Walk 0.9 / Run 0.667 / Equip 0.70 / Attack 1.267 / Attack2 1.267（V11）/ Attack3 1.267 s（V12 单手戳刺；长度均落在 30 fps 重采样网格），输出 `Clips/*.json` 与 `clips.json` 诊断摘要；V1 的 Slash1/Slash2/Pommel 已退役到 trash |
| `fit_upper.py` → `Work/upper/upper_keys.json` | **上挑（技能 swordUppercut）**：参考 106.20-107.30 s（近战动作（滑铲）#9 上撩）逐帧拟合右臂关键参数；上撩 0.300-0.367 s 限拳深（`maxd`）、刃口朝外，收势 0.40-0.67 s 前臂贴镜头扫出左上（`hide`），尾段沿用第一段抬回；`--resume[=t]`、`--accept`。采用第 2 轮，3-5 轮为什么否决写在文件注释里 |
| `author_kukri_upper.py` | 右臂按 `upper_keys.json`；左手按 `LEFT_HAND_NDC`（参考手心位置与深度 → 腕位）关键帧张手平衡，走 `kukri_rig.left_hand_explicit` 逐帧解扭转/屈伸/偏斜；烘 `Clips/Uppercut.json`（38/30 s，接触 0.300-0.433）；`--compare` 出 `Work/upper/cmp_upper_*.jpg` |
| `import_kukri_uppercut.py` | 只导入 `Uppercut` 一条 clip 的包装脚本 |
| `fit_heavy.py` → `heavy_keys.json` | **重击（技能 heavyStrike）**：参考 115.60-117.00 s（近战动作（跳跃）#12 ↙）逐帧拟合右臂：V2 蓄力段（抬刀 0-0.17 s 沿用 V1，0.20-0.40 s 抡锤式后扳把刀压到右肩后、刀把朝前，0.40-2.00 s 再往肩后收）与出手段（从肩后直接回砍：刀翻过顶、劈过准星到下方正中、画外、由右下抬回）；在 `fit_sprint.SprintFitter` 上加 `bladeabove`（拳在画内、刀身在画面上方之外）、`headclear`（刀身/刀把离头部中心 ≥16 cm）、`lensband`（离镜头不到 10 cm 的点必须在画外）；默认保留 V1 的抬刀键，`--full` 全部重拟，`--release` 保留蓄力只重拟出手 |
| `author_kukri_heavy.py` | 由 `heavy_keys.json` 烘 `Clips/HeavyCharge.json`（2.0 s）与 `Clips/HeavyRelease.json`（35/30 s，接触 0.10-0.20）；左手按 `CHARGE_LEFT`（抬刀时张手平衡）、`RELEASE_LEFT`（抬回时左拳露在左下角）在 `kukri_rig.left_hand_explicit` 上解；`--compare` 出 `Work/heavy/cmp_heavy_*.jpg` |
| `import_kukri_heavy.py` | 只导入 `HeavyCharge`、`HeavyRelease` 两条 clip 的包装脚本 |
| `render_preview.py` / `preview_tools.py` | 作者期构图预览：用 V7 FrostArms 可编辑骨架在游戏机位（垂直 FOV 75、16:9）渲染关键帧，非实机验收 |
| `fit_reference.py` → `attack_keys.json` | **V2 单段横挥**：按参考 1:27.00-1:28.27 每帧屏幕目标（拳心/刀尖/刀把/前臂）在解剖参数上逐帧拟合（连续性、扭转走廊、腕限位、肘不挡视线、刀不贴/穿镜头），`--accept` 写出关键参数；`author_kukri_clips.py Attack` 读取并烘成 `Clips/Attack.json` |
| `Reference/` | 参考帧抽取、网格读数图、背景配准测镜头运动的脚本：第一段 `camera_atk2.py` → `atk2_camera.json`；V11 第二段 `extract_atk1.py`（1:24.0-1:26.2 逐帧 + `grid_atk1_*` 读数图）、`camera_atk1.py` → `atk1_camera.json`、`curve_atk1.py`（换算平滑后打印 `KukriRhythm::Diag*` 曲线）；V12 第三段 `extract_atk3.py`（94.0-98.0 s 逐帧 + `grid_atk3_*`／`big_atk3_*` 读数图）、`track_atk3.py`（逐帧光流链 + 左侧远景直接配准）、`contact_atk3.py`（只用左上远景、多起点粗搜后细化，写 `atk3_camera.json` 的 `far`）、`curve_atk3.py`（打印 `KukriRhythm::Stab*` 30 Hz 曲线与 `StabPush`）；上挑 `camera_upper.py`（同 `contact_atk3.py` 的远景直接配准）、`curve_upper.py`（手调关键值后打印 `KukriRhythm::Upper*` 30 Hz 曲线）；重击 `extract_heavy.py`（113.5-119.5 s 逐帧、带标注的 NDC 读数图 `heavy_px_*`）、`camera_heavy.py` → `heavy_camera.json`、`curve_heavy.py`（打印 `KukriHeavyRhythm::Charge*` 与 `KukriRhythm::Heavy*`）；视频与帧图本身留在 `Saved/Reference/`，不入库 |
| `make_kukri_textures.py` → `Textures/T_Kukri_*.png` | 刀面钢材重做（Fab 刀面原为非金属中灰 + 强锤纹，游戏里呈白色颗粒）；保留 UV 与锤纹，刀身岛改为金属钢，法线减弱；导入脚本按纹理修订号就地重导 |
| `author_kukri_rift.py` → `Source/FPSGAME/Weapons/Kukri/KukriRiftRibbons.h` | 挥砍剑气弧形带：从三段 clip、上挑与重击出手 的作者姿态采样刀身（挥砍）或刀尖前方一点（戳刺）在打击窗口里的轨迹，写成视模网格空间（cm）的 C++ 表；运行时 `KukriRift.cpp` 组成动态网格，材质复用双手剑 `M_RuneRift`。改动作或窗口后重跑 |
| `repair_kukri_material.py` | 只把 `SM_Kukri` 的材质槽赋回 `M_Kukri` 并只保存这个包（2026-10-22 白色马赛克修复；编辑器关闭时走 commandlet，开着时走 `mcp_call_codex.ps1 -PythonScript`） |
| `import_kukri.py` | UE commandlet：贴图（BaseColor sRGB / Normal / ORM masks）、Substrate 材质 `M_Kukri`、`SM_Kukri`（自动简单碰撞）、七条 `A_Kukri_*`（AnimDataController 直写骨骼轨，骨架 `SK_AzureRunesword_Manny_Skeleton`，预览网格 `SK_FrostSword_Arms`），写 `import_receipt.json` |
| `dump_sword_rig.py` | UE 端骨架/剑动作数据导出 → `Work/ue_sword_dump.json`（86 MB 中间件，`kmath.load_dump`/`render_preview` 的输入，不入库，可由本脚本重生成） |
| `Work/` | 仅 `ue_sword_dump.json` 常驻；fit/预览等其余输出按需生成、不入库。旧搜索脚本、日志、对比图与各版 key 备份见 `trash/kukri-20261020-closeout/` |
| `Previews/` | 终审关键帧拼图（本地文件，不入库）：`cmp_v6_strike`、`sheet_Attack`、`sheet_attack2_v7`、`sheet_Attack3`、`sheet_attack3_v10` 、`cmp_attack3_v12`／`sheet_attack3_v12`（第三段戳刺对照） |

## 重建

```powershell
$blender='E:\Program Files\Blender Foundation\Blender 5.1\blender.exe'
& $blender -b --factory-startup --python author_kukri_model.py
python make_kukri_textures.py                                             # 刀面钢材贴图
$env:PYTHONPATH=(Get-Location).Path; python fit_reference.py --accept     # 第一段水平横劈逐帧拟合（VARIANT=chop，约 3 分钟）
python fit_reference.py --attack2 --accept                                # V11 第二段：参考 1:24.33-1:25.60 近战 #1 斜劈逐帧拟合（REF_DIAG，从架势起，约 7 分钟）
python fit_reference.py --attack3 --accept                                # V12 第三段：参考 1:34.77-1:35.97 近战(蹲) #5 戳逐帧拟合（REF_STAB，从架势起，约 7 分钟；--resume=<t> 保留上一轮 Work/fit_keys_attack3.json 到 t 为止）
python author_kukri_clips.py Idle Walk Run Equip Attack Attack2 Attack3  # 加 --preview 出关键帧图
python fit_upper.py --accept                                              # 上挑：参考 #9 滑铲上撩逐帧拟合右臂
python author_kukri_upper.py --compare                                    # 烘 Clips/Uppercut.json，出参考对照图（导入用 import_kukri_uppercut.py；剑气重跑 author_kukri_rift.py）
python fit_heavy.py --accept                                              # 重击：参考 #12 跳跃斜劈逐帧拟合蓄力与出手（约 6 分钟）
python author_kukri_heavy.py --compare                                    # 烘 Clips/HeavyCharge.json、HeavyRelease.json（导入用 import_kukri_heavy.py；剑气重跑 author_kukri_rift.py）
& 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' D:\FPS3D\FPSGAME\FPSGAME.uproject `
  -run=pythonscript -script=D:\FPS3D\FPSGAME\SourceAssets\Kukri20261020\import_kukri.py -unattended -nosplash -nop4
```

坑：

- 前臂扭转必须相对**绑定姿态**计算（`kukri_rig.solve_arm`），并逐帧展开；V1 相对剑锚点叠加，导致 twist_02 比例错误、前臂扭到 +120° 和收势翻腕（用户反馈“手部错误反转和扭曲”）。

- `-DisablePlugins=AutoFootstep` 已不能用于本工程 commandlet——`UnrealEditor-FPSGAME.dll` 现直接导入 AutoFootstep，禁用后模块加载失败（GetLastError=126）。
- 动画长度不在 30 fps 网格上（如 0.64 s、0.72 s）会触发 `Incompatible resampling frame rate` ensure，并在压缩线程崩溃；改长度后要先删掉旧包再导入。
- 用 PowerShell `Get-Content`/`Set-Content` 改含中文的 UTF-8 源文件会按 GBK 误读成乱码；源文件只用编辑工具改。
- 角色 `ExitSprintForWeapon` 等是私有接口，弯刀组件不直接调用；冲刺退出由 `FirePressed` 负责。
- 静态网格材质槽：`get_editor_property('static_materials')` 的元素在 Python 里是副本，逐个 `set_editor_property` 不会生效（槽位会留在 `WorldGridMaterial`，刀面显示为白色格子）。用 `mesh.set_material(i, mat)` 并读回。
- 参考镜头配准（V12 戳刺）：靶场靶牌外观完全相同，单帧 ORB 对静止帧会串到相邻靶牌；参考玩家有约 2 m 冲刺，近处建筑的视差会被读成放大；命中帧会锁到静止叠字。只用左上远景，每帧直接对静止帧做相似变换的归一化相关（`Reference/contact_atk3.py`），并用直接对齐的相关值检查旋转符号（错误符号的相关明显更低）。
- 画外段刀身隐藏用 `hide=2`（刀身九点）：默认三点检查时，刀身线段仍会在两个采样点之间切过画面角落。
- `D:\FPS3D\VaultCache\FabLibrary\` 在 2026-10-22 已清空：`Kukri_Editable.blend` 的贴图指向那里，作者期预览刀身显示为缺贴图紫色；重跑 `author_kukri_model.py` 需重新下载 Fab 原件。`import_kukri.py` 只读本目录的 `Textures/`、`Export/`。
