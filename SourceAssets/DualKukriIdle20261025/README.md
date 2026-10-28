# 双持尼泊尔弯刀：待机／走／跑作者源 · 2026-10-25

**状态（2026-10-26）：待机、行走、冲刺 R4 用户已确认。双持三连击 `A_Kukri_DualAttack`／`DualAttack2`／`DualAttack3`（R5–R10）和双持重击（R11）已导入、接入第一人称运行时，Editor 与 Game 目标已构建，待用户实机确认，待办见 `Docs/Backlog.md`。**

## 参考

Bilibili [BV19dUqBJECT](https://www.bilibili.com/video/BV19dUqBJECT/)（Apex 通用传家宝「绝命二重奏」全动作展示），章节「握持姿势」：
- 站立握持：文件 2.0–4.15 s（2.0–2.3 s 是拔刀收尾），静止帧 3.50 s（`f00105`）。双手各持一把弯刀交叉成 X。
- 奔跑：文件 16.75–18.4 s，读数帧 17.50 s（`run_frames/f00525`）。右拳举在画面右上角、前臂沿右缘竖直，刀朝正前方（屏幕上的刀线经过画面中心，所以看起来像朝左）；左拳在下方中间、刀朝左上。

视频与帧图留在 `Saved/Reference/DualKukriBV19dUqBJECT20261025/`，不入库。

## 文件

| 文件 | 作用 |
| --- | --- |
| `Reference/extract_idle.py` | 下载 1080p30 视频，抽 0–8 s 缩略拼图和 1.9–4.4 s 逐帧（帧号 = 秒 × 30）；奔跑帧的 ffmpeg 命令写在 `track_run.py` 里 |
| `Reference/grid_idle.py` | 参考帧叠 NDC 网格（每 0.1），可裁切放大，读屏幕目标 |
| `Reference/track_idle.py` / `track_run.py` | 模板匹配量待机呼吸、奔跑摆动（双拳、刀、背景） |
| `dual_rig.py` | 双刀解算：右臂用 `Kukri20261020/kukri_rig.py` 的已认可锤握；左臂在镜像空间按右臂解，再把世界旋转镜像到左链（骨架左右对称，绑定检查 0 处不符），左拳 = 认可右拳的镜像，左刀 = 右刀绕刀面镜像（刀身对称到 0.13 cm） |
| `fit_idle.py` → `pose_keys.json` | 待机握持：双臂 14 个参数拟合参考屏幕目标；`--refine` 从第 10 轮出发，只加真实网格刀间距 ≥1.5 cm（第 11 轮）；R16 `--hunter` 从第 11 轮出发，按猎手刀身包络间距 ≥2.5 cm、两刀前倾、长刀身避开对侧手，手腕带收紧（第 16 轮，采用） |
| `fit_run.py` → `run_keys.json` | 奔跑姿势：每条手臂单独拟合 5 个手臂参数 + 3 个锁骨角，随机起点。右手试两种反握翻法（`dual_rig` 的 `flip`），左手试正握和两种反握；左肘在胸前外侧。皮肤扭转限 ±70°、解剖旋转限 ±85°。R3 采用第 11 轮的左手 + `Work/right_wrist_r12.py` 的右手（腕部限 25°，翻法 'y'），合成 `Work/fit_run_r12.json` |
| `fit_run_r4.py` → `run_keys.json` 右臂 | R4 冲刺右臂：刀朝正前方（与 (1, 0, 0.07) 的夹角）、拳在 (0.90, −0.50)、前臂沿右缘竖直、掌侧朝镜头，前臂旋转限 ±60°、腕限 20°。三种握法都试，反握 'y' 最好。左臂沿用 R3（`Work/fit_run_r12.json`）。结果 `Work/fit_run_r4.json`；变体脚本在 `Work/r4/` |
| `fit_run_r4_left.py`、`Work/r4/left_guard_scan.py`、`Work/r4/left_polish.py` → `run_keys.json` 左臂 | R4 冲刺左臂：正握、刀身向前。随机起点拟合单独跑会收敛到刀竖起的解，采用的是扫描（seed 32）加细化的 pA，结果 `Work/fit_run_r4l.json`；骨架限制与命令见 `fit_run_r4_left.py` 说明 |
| `author_dual_attack.py` → `Clips/DualAttack.json`、`Clips/DualAttack2.json` | 双持三连击前两段（`STAGES` 配置）：右刀 = 单持该段（`Kukri20261020/Clips/Attack.json` / `Attack2.json`），劈完沉到垂手位；左刀先让开（第一段：镜像蓄势到左上画外；第二段：从右刀上滑开、沉到垂手位），再挥镜像的同一段，分别晚 56/120、60/120 s（运行时 `KukriRhythm::DualSweepOffsets`）；首尾都是 `DualIdle` 第 0 帧。`--preview` 写 `Work/render/<clip>.json`；`--set=段.参数=值` 调参。穿插检查 `Work/r4/dualattack_clear.py <clip>`、`Work/r4/dualattack_sdf.py <clip>` |
| `fit_dual_thrust.py` → `thrust_keys.json` | R8 双刀刺入：左右手的蓄势、打击、抽出各自拟合（左手在镜像空间按右手解）。R10：两拳从画面下角沿刀身直刺，前臂正对前方，刀离正前方约 48°、向上斜指准星，左右完全镜像（两刀间距用 `Work/r4/thrust_pair_gap.py` 检查，游戏视角对比用 `Work/r4/thrust_pair_preview.py`）；手腕限伸屈 −15～30°、尺偏 0～28°（打击位 0～25°），扭转 ±50°。回收 = 蓄势腕点后移 3 cm，过冲 = 打击腕点前移 2.5 cm。调参用 `Work/r4/thrust_fit_one.py`（单键、可覆盖目标）和 `Work/r4/thrust_assemble.py`（按变体合成）；R7 版本在 `Work/r4/fit_dual_thrust_r7.py` |
| `author_dual_attack.py DualAttack3` → `Clips/DualAttack3.json` | 按 `THRUST` 时间表插值 `thrust_keys.json`（左右手各自的键，刺出 u² 缓入、过冲缓出），握姿→动作→垂手位→握姿，2.05 s，命中窗 0.54–0.72 |
| `Reference/camera_thrust.py` / `Reference/curve_thrust.py` | 参考 2518–2565 帧背景配准（ORB + 仿射 RANSAC）→ `Saved/Reference/.../thrust_camera.json`；按 `WARP` 把 R8 的阶段时间映射回参考时间，换算成 62 点镜头曲线（输出到标准输出，R8 存为 `Work/r4/curve_thrust_r8.txt`），贴进 `KukriRhythm::DualThrust*` |
| `fit_dual_heavy.py` → `heavy_keys.json` | 双持重击关键姿势：蓄力 `CHARGE`（open/up/load/deep，左手镜像）；R15 出手 `RELEASE_R`／`RELEASE_L`（over/cross/x/low/end，按参考拳位等速排时间，画外键用放宽的关节范围 `OFF`，相机坐标、每只手单独给目标，左手带与右手同时刻的胶囊间距约束 `fit_pair`）。调参 worker：`Work/r4/heavy_fit_one.py`（蓄力）、`heavy_fit_cam.py`（出手单手）、`heavy_fit_pair.py`（左手带间距），合成 `heavy_assemble.py` |
| `author_dual_heavy.py` → `Clips/DualHeavyCharge.json`、`Clips/DualHeavyRelease.json` | 关键姿势按手臂参数 PCHIP 插值；蓄力 2.0 s（0–0.10 从握姿打开），出手 1.0 s（R15：交叉 X 斩，C2 样条等速，0.167 起全部出画，画外分开，0.70–1.00 从下方回握姿）；画面里有没有手臂和刀 `Work/r4/dual_clip_visible.py <clip>`。`--preview` 写 `Work/render/dualheavy*.json`；两刀间距 `Work/r4/dual_clip_gap.py <clip>` |
| `Reference/camera_heavy_x.py` / `Reference/curve_heavy_x.py` | 参考第 2338–2385 帧背景配准 → `heavy_x_camera.json`；换算成蓄力 13 点、出手 31 点镜头曲线（`Work/r4/curve_heavy_x.txt`），贴进 `KukriHeavyRhythm::DualCharge*` 和 `KukriRhythm::DualHeavy*` |
| `author_dual_rift.py` → `Source/FPSGAME/Weapons/Kukri/KukriDualRiftRibbons.h` | 双持重击的空间扰动带：R15 起是眼前 55 cm 处两条笔直的带，组成 X（右上→左下、左上→右下），0.045–0.125 s 展开 |
| `import_dual_heavy.py` | 只导入 `A_Kukri_DualHeavyCharge`、`A_Kukri_DualHeavyRelease` |
| `import_dual_attack.py`、`import_dual_attack2.py`、`import_dual_attack3.py` | 只导入 `A_Kukri_DualAttack`／`A_Kukri_DualAttack2`／`A_Kukri_DualAttack3` |
| `view_run.py` | 冲刺拟合的对照：参考 17.50 s／本作／叠图（`Work/view_<tag>.jpg`）和右侧、左上方两个外部视角（`Work/view_<tag>_side.jpg`） |
| `import_dual_run.py` | 只重导 `A_Kukri_DualRun`，待机和行走不动 |
| `kukri_sdf.py`；`KUKRI_SDF_VARIANT=hunter`（R16）改用原装整刀 ∪ 猎手刀身的并集（最长刀身的保守包络，缓存 `Work/kukri_sdf_hunter.npz`），所有检查脚本都认这个环境变量 | 整把 `SM_Kukri` 的体素距离场（0.1 cm，缓存 `Work/kukri_sdf.npz`）和表面采样，算刀与刀、刀与点的有符号距离；`KUKRI_SDF_VARIANT=hunter`（R16）改用原装整刀 ∪ 猎手刀身的并集（最长刀身的保守包络，缓存 `Work/kukri_sdf_hunter.npz`），所有检查脚本都认这个环境变量 |
| `read_hunter_mesh.py` | 后台 Blender 读出猎手刀身网格（`KukriHunterBlade20261027`）到 `Work/hunter_blade_mesh.npz`，握点坐标系 |
| `author_dual_equip.py` → `Clips/DualEquip.json`、`Source/FPSGAME/Weapons/Kukri/KukriDualEquipBlade.h`、`Work/dual_equip_left.json` | R17 双持拔刀 0.917 s：右手单持 `Equip`，左手镜像晚 0.067 s，两拳 IK 外移 6 cm、接刀前后左拳前移 6 cm／右拳后移 3 cm（环境变量 `DUAL_EQUIP=外移,右深,左深,延迟` 可调），0.53／0.60 s 起进握姿；左刀相对 `hand_l` 的飞行表 60 Hz。检查 `Work/r4/dual_equip_check.py`（刀与刀、刀与对侧手臂、两臂胶囊）、几何 `Work/r4/dual_equip_geom.py` |
| `import_dual_equip.py` | 只导入 `A_Kukri_DualEquip` |
| `import_dual_all.py` | 一次导入全部 9 条双持动作（改握姿后用） |
| `contact_dual.py` | 按烘焙同样的采样逐帧复核：刀与刀，刀与对侧手臂蒙皮（`render_idle.py --skin` 在 Blender 里蒙皮读回），写 `Work/contact_<clip>.json` |
| `author_clips.py` → `Clips/Dual{Idle,Walk,Run}.json`、`left_kukri.json` | 烘 120 fps 循环（格式同 `Kukri20261020/Clips/*.json`）：待机 3.0 s、走 0.9 s、跑 2/3 s；左刀相对 `hand_l` 的固定关系写进 `left_kukri.json` |
| `import_dual_kukri.py` | 调 `Kukri20261020/import_kukri.py` 导入三条 clip（读本目录 `Clips/`，回执写本目录 `import_receipt.json`） |
| `render_idle.py` | 后台 Blender：V7 FrostArms 可编辑骨架 + 两把 `SM_Kukri`，游戏机位（垂直 75°）或指定细节机位；`--hunter` 叠上猎手刀身。输出目录要给绝对路径 |
| `render_views.py` | 出 `Previews/`：玩家眼点、左右握持特写、俯视、外侧、仰视，参考对照 `compare.jpg`、叠图 `overlay.jpg`、细节拼图 `details.jpg`；`--blend` 另存可编辑 `hold_eye.blend` |
| `quick_view.py` | 拟合中途的快速对照（`Work/view_<tag>.jpg`） |

## 重建

```powershell
python -I Reference/extract_idle.py
python -I fit_idle.py --accept            # 约 10–15 分钟（48 个起点）
python -I fit_idle.py --refine --accept   # 加真实网格刀间距（第 11 轮）
python -I fit_idle.py --hunter            # R16 猎手刀身包络（第 16 轮；结果在 Work/fit_idle.json，写入 pose_keys.json）
python -I fit_run.py --accept             # 约 15 分钟（R3；R4 右臂改用下一行）
python -I fit_run_r4.py                   # 约 15 分钟，右臂 R4 → Work/fit_run_r4.json
python -I Work/r4/left_guard_scan.py 32 50000
python -I Work/r4/left_polish.py Work/r4/dS2.json pA grip=-0.52,0.78 depth=38 elev=28 conv=15 flat=0.35
#   dS2 = guard3_scan_32 筛选后的候选（见 Work/r4/design_sel.json）；pA 复制为 Work/fit_run_r4l.json，再合成 run_keys.json
python -I author_clips.py --preview
python -I fit_dual_thrust.py              # R8 第三段关键姿势 → thrust_keys.json
python -I author_dual_attack.py --preview  # R5–R10 双持三连击三段
python -I fit_dual_heavy.py; python -I author_dual_heavy.py --preview; python -I author_dual_rift.py   # 双持重击
python -I Reference/camera_heavy_x.py; python -I Reference/curve_heavy_x.py  # R11 重击镜头
python -I author_dual_equip.py --preview  # R17 双持拔刀（同时生成 KukriDualEquipBlade.h，改了要重新构建）
python -I Reference/camera_thrust.py; python -I Reference/curve_thrust.py   # R7 镜头曲线
python -I contact_dual.py                 # 穿插复核
python -I render_views.py --blend
& 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' D:\FPS3D\FPSGAME\FPSGAME.uproject `
  -run=pythonscript -script=D:\FPS3D\FPSGAME\SourceAssets\DualKukriIdle20261025\import_dual_kukri.py -unattended -nosplash -nop4
```

## 要点

- 左右手都是已认可的锤握（刃口在指节一侧），左手是右手的镜像，所以两只手和刀柄的接触都是已认可的那一套。
- 运行时第二把 `SM_Kukri` 挂在 `hand_l` 上：`kukri = left_kukri.json 的 rel × hand_l`（网格空间 cm、单位缩放；运行时按骨骼 100 倍导入缩放写成 位置/100、缩放 0.01，见 `KukriWeaponComponent.cpp` 的 `OffhandHandToBlade`）。骨架只有一条武器链（`WPN_root` = 右刀）。
- 待机呼吸只平移双腕（刀随拳刚性移动），镜头不动。走路把整套手臂刚性平移（单持走路同档的起伏／左右／前后），两刀关系和待机一样。跑步沿用单持跑步 2/3 s 的步频，摆幅按参考像素换算。
- 跑步：右手反握（刀在同一拳型里绕握柄 Y 轴转 180°，`run_keys.json` 的 `flip: "y"`），R4 起刀朝正前方、拳离眼约 19 cm；左手 R4 正握、拳在左下、刀尖指向画面里（向上约 36°），运行时右刀在进入 `DualRun` 时先等 0.08 s，再用 0.36 s 在拳里转一圈半（540°），离开时用 0.18 s 转半圈回正握（`KukriWeaponComponent::UpdateDualFlip`）；左刀不转。
