# Kimodo 文本生成动作（动作开发备选工具，2026-09-19 用户指定登记）

状态：**备选工具**。本机已可跑通（生成 + 导出 GLB），但**尚未用于任何已交付动作、也尚未做 UE 内重定向闭环**。
它不是 MAT / Control Rig 手 K 流程的替代。

## 是什么 / 本机位置

| 项 | 内容 |
| --- | --- |
| 上游 | NVIDIA `nv-tlabs/kimodo`（文本→人形动作）的 C++/GGML 移植 `localai-org/kimodo.cpp` |
| 本机安装 | `D:\FPS3D\kimodo.cpp`（源码 + `build\Release\kmd-*.exe` + `build\bin\Release\*.dll`） |
| 权重 | `models\kimodo-soma-rp-v1.1-f32.gguf`（动作 1.06 GB）；`Llama-3-Kimodo-Q8_0.gguf` / `-Q4_K_M.gguf` + `tokenizer.gguf` |
| 后端 | Vulkan（`ggml-vulkan.dll`，SDK 是免 UAC 手工装配在 `D:\FPS3D\VulkanSDK`）；`KIMODO_BACKEND=cpu` 可退回 CPU |
| 安装/命令/实测全表 | `D:\FPS3D\kimodo.cpp\INSTALL-WINDOWS-NOTES.md` |

```powershell
cd D:\FPS3D\kimodo.cpp
$env:PATH = "D:\FPS3D\kimodo.cpp\build\bin\Release;D:\FPS3D\kimodo.cpp\build\Release;" + $env:PATH
.\build\Release\kmd-generate.exe models\kimodo-soma-rp-v1.1-f32.gguf Llama-3-Kimodo-Q8_0.gguf prompts\xx.txt 90 30 4242 output_fp\xx\
python scripts\export_glb.py --motion-dir output_fp\xx --output output_fp\xx\animation.glb
```

## 输出到底是什么（决定它能/不能做什么）

- **整身 30 关节** SOMA 骨架：Hips/Spine1/Spine2/Chest/Neck1/Neck2/Head/Jaw/双眼 + Shoulder/Arm/ForeArm/Hand
  + **每只手只有 ThumbEnd、MiddleEnd 两个指端** + 腿脚；帧率按 30 fps 理解。
- GLB 是 glTF 2.0：31 节点、1 个 skin（30 关节）、1 条 `KimodoMotion` 动画，**没有角色网格/材质**（mesh 只是骨架占位），
  UE 拖入后自动建 SOMA Skeleton，再 Retarget 到目标骨架。
- 上游明确**还没做**：通用约束输入、77 关节（含手指）展开、带蒙皮网格的 GLB 导出、动作去噪模型量化。
  C API（`kimodo.dll`，ABI v1）只给 `local_rotations_xyzw` + `root_positions`。

## 视模手臂适配结论

**不能直接产出可用的第一人称手臂动画**：无独立手指关节；无约束与接触帧控制（换弹、拉栓、插匣的接触时序表达不了）；
训练分布是全身走/跑/跳/蹲/挥拳/跳舞（仓库自带 12 条 seed prompt 无持械）；输出带根位移。

**能用的是"非接触类上身氛围"**：持枪慢走的呼吸与重心摆动、受击晃动、落地缓冲、疲惫/放低武器、探头倾斜。
落地方式：IK Retargeter 里**只映射** Spine/Chest/Shoulder/Arm/ForeArm/Hand 这些链到手臂骨架（不映射腿和根），
再用既有 IK/Control Rig 把双手收回武器上；接触关键动作继续走 MAT + Control Rig。

## 已有试件与量化对照

| 试件 | 内容 |
| --- | --- |
| `output_fp\fp_aim_walk\animation.glb` | 90 帧：双手像握枪一样稳在胸前、微呼吸、缓慢前进 |
| `output_fp\fp_flinch\animation.glb` | 90 帧：受击后仰再稳住双手 |

文本编码器两档对照（同 prompt/噪声，60 帧 30 步，Vulkan，脚本 `tools\compare_text_quants.py`）：Q4_K_M 相对 Q8_0
embedding 余弦 0.99382、根位移均值 2.32 cm、世界 MPJPE 2.29 cm、**根相对（姿态）MPJPE 0.75 cm**；
仓库发布的舞蹈样本曾出现 20 cm 级根漂移 → 正式动作固定 Q8_0、预演可用 Q4_K_M，且必须固定 seed（同 seed 才是同噪声）才可复现。

性能（60 帧 / 30 步，Q8_0）：CPU 40–78 s；Vulkan 默认 8 层分块 **14.0 s**（编码 8.9 s + 扩散 3.6 s）；
32 层常驻 16.3 s——桌面已占 8.8/12.3 GB 显存时常驻反而更慢，用默认流式即可。

## 采用前必须做的验证

1. UE 内只映射上身链的一次重定向闭环 + **实机画面**（按本技能"视模动作验收必须闭环到实机画面"）；
2. 与现有手 K 版本同机位对比（sway 幅度、频率、枪口抖动），确认是"更好"而不是"在动"；
3. 记录 prompt + seed + 量化档，否则不可复现。

许可：C++ 移植 Apache-2.0；SOMA/G1 权重为 NVIDIA Open Model License（可商用）；
**SMPL-X 版本未安装**（NVIDIA 内部研发许可，不可商用、不可分发衍生模型）。

## 首个落地案例：双手持斧待机（2026-09-19，候选未接线）

用户要求用 Kimodo 做双手持斧待机。做法与"采用前必须做的验证"一致：Kimodo 只出氛围层，
双手位置由项目自己的解算器锁到斧柄上。**产物是候选片段，没有写进游戏合同**——采集工具按
"一组五条"播放（Idle/Walk/Equip/Swing/HitRecover 共用一个时钟），只换 Idle 会让切换跳帧；
证据与复现参数见 `Docs/Weapons/kimodo-two-hand-axe-idle-20260919.md`。

可复用要点：

- **读 Kimodo 输出别只看平移。** GLB 拖进 Blender 后逐帧读世界位置能确认"双手保持刚性间距"
  （本例恒定），但 UE 的 `AnimationLibrary.get_bone_pose_for_time(animation, bone, time, False)`
  返回的是**父级相对局部姿态**——FK 下局部平移本就是常量，量平移会得到 0.034° 级的假结果。
  要判"片段里有没有动画"就量**旋转**：两点四元数夹角 `2·acos(|dot|)`，或用 Python 直接算浮点
  （UE 5.8 Python 没有 `unreal.Quat` 类型，别写 `u.Quat(...)`）。
- **命令里没有的姿态求值接口**：`SkeletalMeshComponent` 在 Python 侧没有
  `refresh_bone_transforms` / `tick_animation`；`update_joints_from_animation` 是**布尔属性**不是方法。
  无头验证要么走 `AnimationLibrary` 取姿态，要么回 Blender 侧量。
- **左手握同一根柄 = 解剖学镜像，不是绕轴旋转。** 两手同握一根圆柱时：跨"手腕偏移方向"镜像会把
  左手翻到柄的另一侧（实测偏 15.6 cm）；绕柄轴转 180° 会让左拇指朝下。正确做法是跨**工具左右轴**
  （本例斧刃所在的局部 X）镜像，保持"两手同在柄后方、拇指同朝上"。镜像后要断言：两手离轴距离相同、
  左右分量反号、前后分量相同——**先断言再烘焙**，不要等渲染出来拿眼睛猜。
- **两手握柄受肩宽与臂展的几何限制。** 本例肩间距 0.4 m、单臂展长 0.55 m，单手位置的柄左手够不到；
  按 5% 步长搜索"让两臂都留余量的最小中线平移"取到 12 cm。这是几何而非审美，报告里要如实写。
- **氛围层要换算坐标系再缩放。** Kimodo 面朝 -Y、右为 -X；本工程视模面朝 +Y、右为 +X。
  位置与旋转增量都按该镜像换算，再各乘缩放系数（本例 0.60 / 0.55），两端用 `sin²` 包络归零才可循环。
- **导入走无头 commandlet 也行**（编辑器关闭时）：动画 FBX 只选 ARMATURE 导出，导入时 `options.skeleton`
  指向目标骨架、采样率 150、压缩档 `BC_M4Viewmodel`，随后新进程读回确认。

- **横向持握要按游戏相机画面框来定位置，不能沿用竖版居中。** 2026-09-19 竖向斜持的第二版改横向后，
  沿用竖版持握位置会让斧身捅穿近裁剪面并整体出画（相机在骨架空间 `(-0.07, 0, 0.07)` 朝 +Y、
  垂直 75°／16:9）。可靠做法是写一个小工具把关键点换算成帧内坐标
  `frameX = (p.x - cam.x) / (depth·tan(37.5°)·16/9)`、`frameY = (p.z - cam.z) / (depth·tan(37.5°))`，
  以 **−1…+1 为在框内**，迭代持握位移直到柄端/双手/斧头全部落在框内（本机最终取
  `(-0.25, 0.42, 0.24) m`，深度 0.76–0.93 m）。不要靠"看着差不多"——第一版横向候选五张全在框外。
- **改持握高度用沿柄平移，不要重拟手型。** 右手移到柄上 +0.26 m（紧邻金属头）、左手在其下 0.12 m，
  两手仍用已验收包握并沿柄推进；左手沿柄向下超过约 0.14 m 时会落进柄尾绳结，需要重新取截面。
- **同一 prompt 不同 seed 的动作"安静程度"差别很大**：本条 calm idle 的 seed 2025/8888 都是 12–14°
  胸部摆幅（可用），而首版横向 prompt 的 seed 7777 转了 34°（像转身，弃用）。挑 seed 时量
  **每帧位移/旋转峰值**，别只看单帧。
