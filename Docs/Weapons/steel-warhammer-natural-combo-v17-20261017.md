# 双手锤第三人称：自然衔接 V17

2026-10-17。按用户认可的方案，先完成前三项：待机与普通攻击握位一致、移动攻击腰胯联动、连击与收势衔接。SourceGripV16 待机和八方向步态继续作为用户认可的基线。独立持锤步行及启停素材属于后续阶段。

## 资产范围

为 Slash1、Slash2、Slash3 制作三份独立动画，只替换普通三连击及对应 Recover 的六项配置。重击、上挑、冲刺、旋风、格挡、快速近战仍保持各自原资源。

旧普攻的支撑手在主握手下方，V16 待机则在上方。新普攻沿用 V16 的握持顺序与沿柄间距，允许支撑手绕柄转握；左右手共享一根刚性锤柄。保留原普攻躯干、腿部、头颈轨道、武器旋转方向及原始接触时刻。

手臂适配使用实际骨长和源肘平面。以锤柄的共同平移和支撑掌绕柄转角作为接触变量，约束手腕弯曲；不交换左右骨骼旋转，不增加第一人称轨迹。身体轨道保留，但因握持顺序改变，部分帧需要共同移动两手及锤柄；具体制作数据见 `authoring-report.json`，这些数据不代表视觉验收。

新动画带 `NativeWarhammerContinuousGrip` 标记。完全进入动画时使用烘焙手臂，过渡中只修正支撑手与锤柄的接触，使用当前肘平面且不拉伸骨段。

## 移动时的腰胯

移动仍使用 V16 的普通攻击腿部混合规则。新动画另从原普攻骨盆相对开场的转动提取小幅发力曲线，转角分量限制为 3°、2°、7°，首尾平滑退出。运行时仅在站立地面移动普攻中使用，并按攻击、移动及状态权重缩放。

腰到胸按不同权重衔接：下腰保留较多步态，中腰逐渐增加攻击影响，上胸保留原挥击朝向。仅改变脊柱旋转，保留骨段长度。骨盆的小幅转动后保留当前脚踝目标和膝盖弯曲平面，避免把移动脚步转成攻击素材的固定踏步。

## 连击与收势

普通攻击入口使用最近的可见身体姿态，短过渡延续最近两帧的上身角速度，外推旋转限制为 12°。仅新标记的双手锤普攻启用，其他武器和特殊动作保留既有逻辑。

退出普攻时，短暂延续同一原素材并逐渐减速，以 0.14 秒平滑淡回当前持握。既有攻击判定、攻速、命中回收进度保持权威；新增表现逻辑不发伤害事件。头部继续沿用稳定规则。

## 落盘与构建记录

作者目录：`SourceAssets/WarhammerThirdPersonSevarog20261016/NaturalComboV17/`。

入口：`author_combo.py` → `save_natural_combo_v17.py` → 正式 Editor 构建及 `record_build.py` → `publish.py`。

三个独立动画包：`/Game/Characters/JasonPlayer20261003/WarhammerSevarog20261016/NaturalComboV17/Animations/`。

以 `assets-saved.json`、保存 commandlet 正常退出、`completed-build.json`、`assets-published.json` 分别记录保存、构建和六项引用切换。按用户规则未运行游戏、测试、截图或渲染，由用户自行体验效果。

三份动画已保存，保存 commandlet 于 23:36 正常退出（退出码 0）。用户保存并关闭编辑器后，正式 Editor 构建 `Saved/BuildEditor/build-20261017-234402.log` 返回 `Result: Succeeded`。构建记录已保存到 `completed-build.json`，普通三连击与对应回收的六项引用已由 V8 切换到 V17，`assets-published.json` 已落盘。V16 待机和步态保持现状。

编译期间修正了本轮支撑握点局部变量与 `FControls::Grip` 的同名冲突，并为 `TemperateHillsBackdrop.cpp` 补充缺失的 `Components/VolumetricCloudComponent.h`，解除整工程构建的完整类型错误；没有改变天气逻辑。失败尝试保存在 `build-editor-first.log`、`build-editor-second.log`，最终成功记录为 `build-editor.log`。完成后未启动编辑器或游戏。
