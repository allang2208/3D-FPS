# 尼泊尔弯刀第三人称旋风

2026-10-25，按用户要求继续制作旋风。Jason、Kaitlin 各保存起势、旋转、收势三个原生动画，替换各自 `Kukri.FullBody.Whirlwind.Start/Loop/End`，共六个资产、六个配置字段。

后续状态：用户否定本版姿态的自然度，要求持刀臂外伸、另一只手架在胸前。修订见 [WhirlwindGuardV5](kukri-third-person-whirlwind-chest-guard-20261025.md)。本文保留为 V4 制作记录，不代表用户认可。

## 动作与时序

本地 CC0 Quaternius UAL2 `Sword Regular C` 提供转身躯干发力和收势。源整体转向在骨盆层剥离一次，保留相对胸肩运动；动作不再拼接旧 Kwang 下身与 KayKit 静态手臂。右臂按原生握点适配右侧持刀横扫，并保留 C 的部分带刀节奏，左手使用已有原生握拳护手。

角色继续执行配置中的 -720 度转向。作者脚步使用 `RuneSwordWhirlwindFeel.h` 的同一角度相位：加速段 0.12、减速段 0.18，两圈安排八次交替支撑。支撑脚的目标点与朝向在世界空间保持，抬脚沿外侧弧线前往下一落点，随后换算回角色局部空间保存。后脚蹬地围绕脚掌修正脚踝，膝部由各自原生骨长求解；起势和收势分别准备、撤回双脚。

源 C 的全局旋转不再叠加到角色旋转。现有技能进度和顿帧共同驱动分段采样，未增加独立运行时旋转时钟。当前配置的准备、旋转、恢复时长分别为 0.5、32/30、0.52 秒；三个动画资产分别为 0.5、32/30、32/60 秒，通过现有分段进度映射。旋转资产以 120 fps 保存完整两圈，其余两段为 60 fps。三段首尾使用同一份完整姿态，收势末帧回到当前待机。

## 资产与制作源

资产目录为 `/Game/Characters/JasonPlayer20261003/Kukri20261024/ComboV3/<Jason或Kaitlin>/Animations/WhirlwindV4`，已经包含在现有 Cook 目录内。每套身体包含：

- `A_Kukri_Whirlwind_Start_TurningStep`
- `A_Kukri_Whirlwind_Loop_TurningStep`
- `A_Kukri_Whirlwind_End_TurningStep`

制作目录 `SourceAssets/KukriWhirlwind20261025` 包含 `prepare.py`、原始 `source-c.json`、`author.py`、两套 `*-actions.json`、`save_assets.py` 和 `publish.py`。依赖 ComboV3 的原生身体与握点数据、ThrustHand 的原生握拳适配，以及 Heavy 作者文件的旋转插值函数；这些制作依赖应保留。

共享配置通过 `Tools/PlayerBody/config_transaction.py` 按六个明确字段写入。`authoring.json` 记录角度时钟和源范围；`assets-saved.json`、`published.json`、`delivery.json` 记录保存、本地接入和交付。

## 交付状态

后台 commandlet 已保存六个资产并正常退出，配置已接入。本次没有 C++、第一人称或玩法规则修改，无需新增原生构建。未启动可视编辑器或游戏，未进行渲染、自测或视觉验收。支撑脚设计的实际观感由用户在 F6 第三人称／固定第三人称中体验。
