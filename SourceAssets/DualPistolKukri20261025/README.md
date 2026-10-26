# 主手手枪 + 副手尼泊尔弯刀：待机、快速近战与副手上挑作者源 · 2026-10-25

**状态：腰射与 ADS 作者源（V2）＋ R2 握点前移与快速近战三连出刀 ＋ R3 副手上挑（主手上挑镜像共轭），已接入第一人称运行时（`Source/FPSGAME/Weapons/Kukri/OffhandKukri*`），未测试。** 记录见 [Docs/Weapons/dual-pistol-kukri-idle-20261025.md](../../Docs/Weapons/dual-pistol-kukri-idle-20261025.md)。

## 参考

Bilibili [BV1hQnh6hEio](https://www.bilibili.com/video/BV1hQnh6hEio/)（使命召唤 23 全武器检视），手枪章节 KRAIT P68 COMMANDO 满配：右手持枪、左手反握刀。待机只在检视前后各出现约 0.5 s 的静止段（文件时间 25.83–26.17 s、50.4–51.0 s，30 fps），没有可读的呼吸起伏。视频与帧图留在 `Saved/Reference/DualPistolKukriBV1hQnh6hEio20261025/`，不入库。

## 文件

| 文件 | 作用 |
| --- | --- |
| `Reference/overview.py` | 手枪章节按秒拼缩略图，定位双持段 |
| `Reference/extract_idle.py` | 按文件秒数抽帧、拼读数图（`idle_frames/fNNNNN.png`，帧号 = 秒 × 30） |
| `Reference/grid_idle.py` | 静止帧叠 NDC 网格 |
| `read_kukri_mesh.py` | 后台 Blender：从 `Kukri20261020/Kukri_Editable.blend` 读 `SM_Kukri`，输出握点坐标系网格 `kukri_mesh.npz` |
| `v9_surface.py` | 把 `BareSkinV9M4_20261017/Work/install_payload.json` 的 V9 位置、逐角 UV、权重覆盖和 JC_ 矫正形状按位置对应到 `SK_M4_BareArmsV7`（副手层实际用的手臂网格，旧位置误差 0 cm）。不含 pose4 的 JC_Pose_* |
| `pose_controls.json` | 制作控制（相机系 X 前 / Y 右 / Z 上，cm）；`fit` 为拟合结果，`ads` 为 ADS 控制块，`shoulder_roots` 为固定的视模手臂根部 |
| `grip_fit.py` → `grip.json` | 在 VRE 拳型里拟合反握弯刀：刀柄体素距离场（0.08 cm）内不得有皮肤，五指都贴住刀柄；变量是刀在拳中的偏移/旋转和每根手指的弯曲比例 |
| `export_runtime.py` → `Source/FPSGAME/Weapons/Kukri/OffhandKukriAuthoredPose.h` | 运行时数据：五指局部旋转、`KukriInHand`、腰射/ADS 站姿（左腕相对右手、左手朝向、双肩与肘方向点）、腰射 `HipFraming` |
| `contact_check.py [_ads]` | 在最终蒙皮网格上复核刀柄接触（负值 = 皮肤进入刀柄） |
| `fit_idle.py [--ads]` | 在原生骨长下拟合构图（`--ads` 拟合 ADS）：右腕保持 M1911 源腕部关系，左腕不超屈伸/偏斜限位，左前臂在右前臂下方（屏幕上被遮挡）且骨段间距 ≥ 6 cm，左手背朝眼，左拳在持枪手右侧且不被遮挡，两前臂屏幕角度接近参考，刀身朝前 |
| `author_idle.py [--ads]` | 解算双臂并蒙皮，输出 `arms_camera.npz`、`gun_camera.npz`、`kukri_camera.npz`、`candidate.json`（骨骼矩阵、`kukri_in_hand`、枪的构图变换与诊断） |
| `quick_view.py` | 快速平涂检查（`--sides` 把左臂染蓝），输出 `Work/quick_*.jpg` |
| `render_idle.py [-- --ads]` | 后台 Blender：玩家眼点 `idle[_ads].png`、眼点窄视角握持特写 `-grip.png`、掌侧 `-palm.png`、斜侧 `-detail.png`、可编辑 `DualPistolKukri_IdleCandidate[_ads].blend`（贴图外部引用，不打包） |
| `compare.jpg` / `ads_vs_hip.jpg` / `grip_contact.jpg` | 参考与腰射对照 / 腰射与 ADS / 握持特写 |
| `author_strike.py [--tween]` → `Work/strike/strike_keys.json` | 快速近战单次突刺逐键姿态（18 键，0.633 s：左腕偏移、左手朝向、肩/极点、锁骨份额、枪身取景），按三轮参考刀循环（帧 1178–1261）：左臂从左缘水平扫入、上臂抬起、肩根出拳时上抬；首尾键 = 待机位姿。读 `thrust_fit.json`；`--tween` 按运行时插值求解补间预览 |
| `fit_thrust.py` → `Work/strike/thrust_fit.json` | 保持参考拳位，拟合各键刀向/指节/手肘/肩偏移，腕部限位（桡偏 ≤ ~16°、尺偏 ≥ −30°、屈伸 ±40°）、刀身朝远处、刺击段手肘在画面左缘 0.05–0.30 高度 |
| `render_strike.py` | 后台 Blender：突刺关键帧与补间眼点预览 `Work/strike/strike_tXXX.png`（XXX = 毫秒） |
| `Reference/curve_thrust.py` → `thrust_curve.json` | 突刺窗口（帧 1210–1230）的参考相机配准 21 采样 + 背景模糊包络（归一化沿用整段刀花） |
| `export_strike.py` → `Source/FPSGAME/Weapons/Kukri/OffhandKukriAuthoredStrike.h` | 运行时数据：姿态键表、挥声/接触帧（单次）、21 采样相机曲线（yaw/pitch/roll/FOV）与背景模糊包络 |
| `diag_grip.py` / `diag_wrist.py` | 上挑握刀/手腕审计：剪辑矩阵缩放、镜像手部朝向误差、刀柄挂点、手指镜像约定、指节对照剪辑；左腕签名对照主手剪辑、上臂近肩蒙皮半径 |
| `diag_upper_arm.py` / `diag_elbow.py` / `diag_upper_skin.py` / `diag_clavicle.py` / `diag_clavicle_view.py` | 副手上挑审计：伸展度/手肘弯曲方向对照剪辑、上臂蒙皮半径对照绑定、锁骨朝向、锁骨权重顶点是否入画 |
| `author_upper.py` → `Work/upper/offhand_upper_keys.json` | 副手上挑逐键姿态（77 键）：把主手弯刀 `Kukri20261020/Clips/Uppercut.json`（BV1CeYUeSE7b #9 106.20–107.30 s）按镜像共轭（mesh→cam 基变换 × 网格 X 取负）换到左手相机空间，逐键枪身取景同步镜像实现右手避让；正握窗口 0.120–1.050 s 内 19 根手指骨套用正握拟合。V2：肩根随挥刀权重移到镜像剪辑肩位（手肘与剪辑重合），锁骨跟随上臂形变 70%（`CLAV_SHARE`，消除上臂近肩段变细） |
| `render_upper.py` | 后台 Blender：副手上挑预览帧/回放图（检查刀路、右手避让与手指贴合） |
| `export_upper.py` → `Source/FPSGAME/Weapons/Kukri/OffhandKukriAuthoredUppercut.h` | 运行时数据：姿态键表、挥声/接触/打击帧、40 采样镜像刀路丝带站；全长 1.2667 s |
| `gen_integration_patches.py [host ...]` | 按 `Docs/Publication/DualPistolKukri20261025/integration-prerequisites.json` 的前置/结果哈希重建全部 17 份集成补丁：逐文件文本回退本轮编辑、sha256 逐级校验、`diff -u` 后按约定转 CRLF 载荷、回环验证后写入 `Integration/` |

## 姿势要点

- 右手：M1911 Contact 已认可握持原样不动，枪+手作为整体移到画面中线偏右，逆时针侧倾约 20°，右臂重解。右腕与源动作接近（掌屈 23.6°/源 15.2°，尺偏 −23.9°/源 −22.4°，扭转 13°/源 15°）。
- 左手：已认可的 M4 VRE 垂直握把拳型，`grip_fit.py` 微调五指弯曲（拇指 1.07，其余 0.93–0.95）和刀在拳中的位置（拳心在刀柄 −8.3 cm，偏转 ≤ 14°）。弯刀反握：刀身从小指侧朝前伸出，刃口朝掌根；尾端带钩的刀柄末端从拇指侧露出。最终网格复核：刀柄内最深 0.01 cm（体素误差约 0.1 cm 以内），五指与刀柄表面的距离都在 ±0.011 cm 内（拇指 −0.011 最深）；掌心与刀柄留约 0.65 cm（掌侧，玩家视角不可见）。
- 交叉：左前臂从右前臂下方穿过，左拳露在持枪手右侧，手背朝镜头；Blender 光线追踪染色检查确认遮挡顺序。
- 手臂根部：`shoulder_roots` 固定为用户 2026-10-25 认可构图时的视模手臂根部（上臂留在画面外），拟合只允许 ±2 cm。早期拟合每轮会把上次的偏移再叠加一次，已改为相对固定根部。
- ADS（无参考，设计稿）：准星在视线上（照门距眼 42 cm、垂直 FOV 55、不侧倾）；左腕交叉托在右腕下方（两手腕骨点距 6.8 cm、左腕低 ≥ 3.5 cm）；弯刀朝前偏下，刀和左拳都在画面中心下方 0.3（NDC）以外。右肩为够到瞄准位前移约 15.6 cm（解算器按 94% 伸展跟进），左肩 2.2 cm。

## 重建

```powershell
$blender='E:\Program Files\Blender Foundation\Blender 5.1\blender.exe'
& $blender -b --factory-startup --python read_kukri_mesh.py
python -I grip_fit.py --accept      # 刀柄接触，约 30 s
python -I fit_idle.py --accept      # 腰射构图，约 1–2 分钟
python -I fit_idle.py --ads --accept
python -I author_idle.py; python -I author_idle.py --ads
python -I contact_check.py; python -I contact_check.py _ads
& $blender -b --factory-startup --python render_idle.py
& $blender -b --factory-startup --python render_idle.py -- --ads
python -I export_runtime.py         # 改姿势后重新生成运行时头文件，再构建
```
