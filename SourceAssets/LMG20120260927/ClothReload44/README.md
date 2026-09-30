# 201 布弹箱换弹：ClothReload44（2026-09-30）

替代 ClothFeed33 的五类握把 × 普通/空仓共 10 条换弹。ClothFeed33 旧片段已经按先前整理记录归档；`apply_runtime.py --revert` 是历史工具，不再作为当前回退入口。

## 当前状态与历史版本边界

现用为 44.4b 的普通/空仓节奏和 B53 弹链衔接，再叠加 ArmHinge55 的左臂七骨修正。本文件下文按制作日期保留 v1/v2 的失败方法与旧数值，不能把历史离线指标当作当前验收。上臂采用解剖肘铰链，前臂承接旋前；不要恢复连贯掌框架驱动整条上臂的 v2 做法。

本目录 Tracks 早于后续 ArmHinge55。重新制作应在最新采集数据上合并弹链补丁，再重做左臂局部轨道；不要直接执行旧全量安装器覆盖当前资产。一次性 Diagnostics/patch*.py 已归档，最终脚本已包含其修改。见 [发布与恢复顺序](../../../Docs/Weapons/lmg201-publication-20261001.md)。

## 为什么重做

对现用 ClothFeed33 做了离线实际蒙皮排查（`Diagnostics/c33_*.json`）：

- 镜像 PKM 工作臂 + 整链平移：肘端 `lowerarm_l` 轴向扭转在 ±180° 之间翻转，肘缝混合行列式最低 0.06（idle 0.81），即肘部拧塌；
- 锁骨相对 idle 平移 26–39 cm；左臂最近距眼 2.8 cm（4.75 s 贴镜头）；肘部单帧跳动 10 cm。

## 参考视频拆解

`C:/Users/allan/Videos/NVIDIA/Delta Force/Delta Force 2026.09.28 - 22.36.59.03.mp4`（60 fps，8.65 s）。末发 1.02 s，动作约 1.35 s 起、7.9 s 静止，HUD 000→125 在 6.417 s。按 ×0.95 映射到 6.2 s：

| 源秒 | 本版 | 参考 |
| --- | --- | --- |
| 0–0.74 | 枪小幅下沉侧倾，左手松握 | 1.35–2.2 |
| 0.98–1.33 | 左手横跨从左上勾盖后沿，抬盖到 60°，松手后盖自己立起 ~86° | 2.3–2.8 |
| 1.60–1.74 | 捏出托盘上的旧弹链（空仓时无弹链，只是扫过托盘） | 2.9–3.1 |
| 2.00–3.35 | 手下到画面外托住布箱底部卸下 / 换上（2.45 旧箱隐、2.80 新箱显，均已核对完全在视锥外） | 3.2–5.0 |
| 3.82–4.78 | 左下捏起弹链端头，铺入托盘压实 | 5.0–6.5 |
| 4.98–5.22 | 抬手勾立起的盖沿拉回，平掌合盖 | 6.6–6.9 |
| 5.22–5.34 | 掌压 | 6.9–7.0 |
| 5.45–5.80 | 张手离开、回握护木；5.45–6.2 与运行时取景回位同段 | 7.1–7.9 |

## 制作方法（`author_motion.py`）

- 左手关键帧挂在被操作部件上（枪 / 盖 / 旧箱 / 新箱），跟随段用部件局部矩阵锁定接触。
- 手臂：锁骨固定，两骨解算保持骨长；上臂滚转由肘平面携带；前臂沿用 Skin07 已认可的分站扭转（肘端保持 idle 的 12.9°，辅助骨 0.273869 / 0.847869，腕端 1）。
- 手部朝向在前臂相对空间做 swing / twist 插值，限制腕部摆幅 48°、前臂绝对滚转 −100…+45°；世界空间 slerp 会让前臂转过 +270°，已弃用。
- 接触帧做肘极摆角搜索（腕部可达性、离眼距离、触达比、与上一接触的肘向连续性），肘极再做 0.07 s 高斯平滑。
- 右手随枪保持 idle 握把；动作取景让镜头靠近右肩 9 cm，锁子甲右袖曾顶到近裁面，右臂根按运行时取景权重后移 3 cm。
- 手型取自已安装 PKM 空仓换弹的对应帧（右手帧镜像）；布箱为刚体，6 段可见弹链由箱口到端头成链。

## 排查结果（`Diagnostics/compare.py c33_base r44_base_final`）

| 指标（base） | ClothFeed33 | ClothReload44 |
| --- | --- | --- |
| 左臂离眼最近 | 2.8 cm | 22.8 cm |
| 肘端扭转范围 | −180…180° | 恒 13°（=idle） |
| 肘缝行列式最低 / 中位最低 | 0.062 / 0.162 | 0.214 / 0.297（PKM 已认可 0.122 / 0.215） |
| 腕缝行列式最低 | 0.499 | 0.829 |
| 锁骨平移 左 / 右 | 26.3 / 3.5 cm | 0 / 1.4 cm |
| 骨长误差 | 0.069 cm | 0.0002 cm |
| 肘单帧位移 | 10.2 cm | 4.3 cm |
| 手臂入枪最深（绕数判定） | 0.64 cm | 0.59 cm（捏弹链指腹接触） |
| 锁子甲 / 毛衣 / 默认袖下沉最大 | 2.31 / 2.83 / 2.83 cm | 0.21 / 0.57 / 0.57 cm |
| 手套腕带外露（默认 / 黑皮 / 露指） | 1.23 / 0.09 / 0.56 cm | 0.23 / 0.01 / 0.20 cm |

其余四类握把的数值见 `Diagnostics/r44_<family>.json`。这些是离线相对指标，不是视觉验收；最终观感由用户在游戏里判断。

## 入口与落盘

- `collect.py` → `author_motion.py` → `install.py`（`run_headless.ps1 -Script ...`，批次互斥、UE 运行时不启动）→ `apply_runtime.py` → 编辑器模块构建。
- 可编辑源：`LMG201_ClothReload44_Animated.blend`（五个 Action + 接触时间标记）；轨道 `Tracks/*_tracks.json.gz`。
- UE：`/Game/Weapons/LMG201/ClothReload44/Animations/<family>/A_LMG201_<family>_reload[_empty]`，回执 `delivery.json`。
- 运行时：`LMG201WeaponAssets.h` 时点常量与动画路径、`FPSGAMECharacter.cpp` 开盖音效时点改用 `ClothCoverOpen`。
- `install.py` 会校验五个 idle 的 SHA-256；握把 idle 变动后需要按上面的顺序重跑。本次导入前，另一会话改过右手 idle，已据此重新采集并重算。

未运行游戏或 PIE；动作、音画同步和穿衣效果由用户实机检查。

## ClothReload44.2（同日返工：左臂 / 腕关节扭曲）

用户判定第一版不合格：左手手臂和腕关节扭曲。根因与改法见 `Docs/Weapons/lmg201-cloth-reload44-20260930.md` 的"第二版"一节。

- 根因：201 现用 PKM V7 裸臂，前臂权重来自 LeftArm48，五类 idle 都符合 PKM 的连贯骨段约定（`probe_coherent.py` 复现误差 ≤0.0003°）。第一版却套用旧 201 的 Skin07 分站，前臂内部偏离 50–70°，上臂辅助骨偏离 100–115°，腕部顶在 48° 限幅。
- `rig.py`：新增 `finish_coherent`。三根前臂骨共用掌宽投影得到的框架，上臂辅助骨沿肘弯传递，主上臂骨保留 IK 旋转。`tau_of` 给出肘平面框架与掌框架之差，即肩根扭转。
- `author_motion.py`（修订 `ClothReload44.2`）：
  - `pkm_rot` 读取 PKM 空仓换弹的手部朝向（去掉枪身运动，右手镜像）。
  - 换箱段改为从下托、手指沿箱朝前（依据 `probe_box_grip.py`）。
  - 接触帧腕折限 22°（勾盖 30°），过渡段限 45°。
  - 肘部在肩—腕圆上整圈搜索，关键帧之间用球面插值。
  - 右臂上臂辅助骨写回顺序已修正。
- 检查：
  - `Diagnostics/check_joints.py`：五类与连贯框架偏差都是 0.0°，腕折 ≤45°，骨长误差 0.00025 cm，肘、手离眼 ≥32 cm。
  - `diagnose.py` 的对照为 `r443_*`。
  - 毛衣、默认袖肩根下沉约 2.2 cm：毛衣带 `spine_04` 权重而皮肤没有。`probe_sink.py` 确认这些点 0 个在视锥内。
- 接入：`install.py` 按修订号新建回执，同路径覆盖，每个包都校验了写入前后的 SHA-256。本轮由后台 commandlet 保存 10/10（`commandlet-20260930-095614.log`），`delivery.json` 为 `revision=ClothReload44.2`。
- 回退：第一版十个包与回执在 `Before_v1/`（`hashes.json`），第一版可编辑 Blend 为 `Before_v1/LMG201_ClothReload44_Animated_v1.blend`。`LMG201_ClothReload44_Animated.blend` 已按新轨道重建。
- 运行时路径、时点与 C++ 未改；没有运行游戏或 PIE。

## ClothReload44.3（弹链物理对齐）

- 对照 BeltMotion49 的运行时弹链物理：第 0、5 节钉在动画上，第 1–4 节偏离不超过 0.39 cm。
- `author_motion.py` 修正了三处：捏点计算误带骨骼缩放（hand_point）；链点改用运行时的 Belt49 节中心并按弦长保持（Inputs/belt49_cells.npz，由 Diagnostics/dump_belt49.py 从 BeltMotion49/Exports/SK_LMG201_Belt49.fbx 导出）；下垂方向连续，箱口节随布箱朝向。捏住的节用 pinchcell 地标，偏移 PINCH_CELL。
- 离线复算脚本：Diagnostics/sim_belt_phys.py（FPKMSoftChain 的 Python 移植）；本轮修正后按用户规则没有复跑。
- 保存：commandlet-20260930-104527.log，delivery.json 为 `revision=ClothReload44.3`；第二版的包在 Before_v2/。

## ClothReload44.4 / 44.4b（空仓节奏、镜头抖动、BeltFit53 衔接）

- 空仓换弹去掉托盘拨链，直接去托布箱，总长仍为 6.2 s。时间节点见 `author_motion.py` 的 EMPTY_KNOTS，与运行时 LMG201WeaponAssets::ClothEventTime 一致。空仓轨道为 Tracks/<握把>_empty_tracks.json.gz（--empty-only 生成）。
- 运行时：显隐、音效、弹药提交、取景回位和新链阻尼都按空仓时间取值。201 布箱换弹的镜头抖动复用 PKM 的换弹抖动（LMG201ClothReload(Empty)，无拉栓尾段）。
- BeltFit53 衔接：`apply_b53_belt.py`。`normal` 模式把 BeltFit53 的原补丁合并到 R44.3 普通轨道；empty 模式以只读方式执行 BeltFit53 的 motion.py，新链铺入窗口按空仓时间映射。合并后的完整轨道为 Tracks/*_b53_tracks.json.gz，install.py 只写 motion.json 的 install_only 所列 9 条（angled 普通换弹保留 BeltFit53 原包）。
- 备份：Before_v3/ 为 13:43 的 BeltFit53 版十个包。保存日志 commandlet-20260930-153103.log；构建日志 Saved/BuildEditor/build-20260930-153306.log。未测试。

## 2026-09-30 ArmHinge55

十条布箱换弹的左臂 7 根骨轨道已由 SourceAssets/PKMLowpoly20260922/ArmHinge55 改为解剖铰链写法（上臂对齐肘铰链，前臂旋前）。本目录 Tracks/ 仍是改写前的源轨道。重新导入前，先在新轨道上重跑 ArmHinge55，否则会回到上臂拧转。
