# 战锤第三人称 V8：蓄力、挥击衔接与快速近战肩部空间

2026-10-17。用户要求适当微调僵硬感，排查蓄力静止和快速近战手臂进入肩膀，并检查挥舞姿势。延续已生效的 Kwang / KayKit 第三人称全身动作与上一轮加快后的攻击节拍。

## 原因与修改

- 蓄力原先执行 `Seconds=min(Contact*0.5, Seconds+Delta)`，约 0.1 秒即永久停在同一帧。现在先举锤，再随蓄力进度小幅收紧；满蓄力在很小的原素材范围内持续起伏。释放从上一帧的实际蓄力姿态开始，不跳回固定姿态。冲刺举锤也采用渐进过程。
- 原播放曲线在准备结束、惯性结束处反复降至零速度。现在保留少量过渡动量，最后收势才停下。游戏 Contact / Release 节点、伤害、攻速和第一人称动作不变。
- 原双手适配约束了腕部角度与最大伸展，没有约束快速近战的手肘内折和肩胸空间。新版本保持同一刚性锤柄的双手关系，将快速近战手肘放在胸廓外侧、肩线前方，手腕保持在身前，并约束前臂到两侧肩关节的距离。
- 三段普通挥击和快速近战的手臂轨道使用 1.15 帧（约 19 ms）尺度的轻微平滑，再以原骨长重新拟合双手握持，并让肘部修正连续。躯干、下肢、头颈轨道不改写。没有使用第一人称动作轨迹。

## 本次明确要求范围内的离线检查

使用 Jason 原始蒙皮权重和实际身体表面，去掉已经在正式身体资产中删除的代理/重复面部材质区域，查看快速近战准备、接触与回收的正面、侧面和背面。预览仅用于肩臂姿态检查，不含运行时独立头部、装备手指覆盖、衣物和武器渲染。

以原始 60 Hz 采样计算，手肘相对胸部的最大相邻帧位移如下；这个指标用于辨别手臂跳变，不等同于运行时挥击速度：

| 动作 | 右肘 V7 → V8（cm） | 左肘 V7 → V8（cm） |
| --- | --- | --- |
| 普通第一段 | 24.72 → 11.97 | 11.46 → 7.13 |
| 普通第二段 | 7.30 → 4.52 | 7.22 → 5.49 |
| 普通第三段 | 5.42 → 5.09 | 11.45 → 8.98 |
| 快速近战 | 7.32 → 6.00 | 7.59 → 3.21 |

快速近战前臂中心线到肩关节的最小距离：右侧 14.48 → 23.40 cm，左侧 16.22 → 22.69 cm。这是骨架几何间距，不是衣物表面间隙。新输出的双手相对位置误差在导出精度内小于 0.001 cm；躯干、下肢、头颈采样与 V7 完全相同。局部蒙皮对比见 `SourceAssets/WarhammerThirdPersonSevarog20261016/RefinementV8/quick-clearance-review.png`。

## 接入范围

新建四个 `RefinementV8/Animations/J_Hammer_Refined_*` 包：Slash1、Slash2、Slash3、QuickMelee。普通三段、三个命中回收、重击蓄力/释放、冲刺举锤/释放、上挑、快速近战共 12 处角色动作引用使用新包。格挡、旋风素材维持现有版本。

源码变更：`Source/FPSGAME/Characters/FPSBodyWarhammerMotion.h`。保留本地与远端正确的 `warhammer` 武器身份、世界模型隐藏额外第一人称手臂、原生双手握持不再次被 IK 改写以及头部稳定逻辑。

制作与检查来源：`RefinementV8/author_refinement.py`、`inspect_skin.py`、`pose_review.py`、`authoring-report.json`、`pose-review.json`。后台保存入口：`save_refinement_v8.py`；配置发布入口：`RefinementV8/publish.py`。

正式 Editor 构建成功：`Saved/BuildEditor/build-20261017-082543.log`，结果 `Succeeded`；本批输出为 `RefinementV8/build-editor.log`。

后台 commandlet 已于 08:34 完成，退出码 0，四个动画包全部保存（`RefinementV8/assets-saved.json` 的 `complete=true`）。随后已切换 `Content/ColdSteelData/player_body.json` 中 12 处动作引用，发布记录为 `RefinementV8/assets-published.json`，其中保留原引用。源码、构建产物、动画资产与配置均已落盘。未启动 UE 编辑器、PIE 或游戏，最终实机观感与衣物表现由用户体验。
