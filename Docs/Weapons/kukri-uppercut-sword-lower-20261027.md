# 单手刀剑上挑：双手剑下半身与端正躯干

后续更新：单持主手已由 [主手肩肘与手腕重做](kukri-single-uppercut-arm-20261027.md) 接替；该版本保留本文下半身与躯干。本页的四资产记录为当时交付，双持入口仍使用本文版本。

按用户要求，将双手剑上挑的下半身动作适配到当前单手刀剑上挑。覆盖 Jason、Kaitlin 的 `Kukri.FullBody.Uppercut` 和 `Kukri.FullBody.Dual.Uppercut`，各保留当前单持或双持的肩臂、腕部局部关系和握刀指形。

## 制作

从当前配置读取实际已接入的 `Melee.FullBody.Uppercut`：Jason 使用 `J_Kwang_Uppercut`，Kaitlin 使用其原生 WeaponContacts 派生。原生双手剑动作长约 1.4667 秒，Contact 为 0.292006 秒、Release 为 0.371644 秒。按单手剑现有 0.350 秒接触、0.433 秒收势对齐，最终仍为 120 Hz、153 帧、38/30 秒。

双手剑运行时还使用 `Unarmed.Jog.Fwd` 前冲步幅，因此也读取两套原生步幅。在现有单手剑 0.24–0.37 秒前冲窗，使用其最后一段 R→L 接触相位；保留胶囊的位移权威，去掉动画根位移，不将整段多步跑步压进一次上挑。起势与收势的左右落脚错开，前冲后接回双手剑上挑的站姿恢复，最后回到各自单手／双持待机。

骨盆居中于两脚支撑范围，保留压低、抬升的高度变化，主动阶段去掉骨盆侧倾。脊柱依次分配有限轴向转体，前后倾幅度软限制为约 4 度，并去掉主动侧倾；颈与头轻度跟随。骨盆回正后重解双腿目标与膝弯平面，重建腿部 twist 辅助骨。原有肩臂链整体随新胸廓搬运，不独立掰腕或更换指形。

`FPSBodyKukriMotion.h` 仅修改上挑的移动提交权重：上挑前冲时不再随速度把作者下半身权重削减到约 40%；入场、恢复和现有空中／翻越等分层仍按既有规则处理。第一人称、技能时长、命中、伤害、前冲距离和其他攻击不改。

## 文件与资产

作者目录：`SourceAssets/KukriUppercutSwordLower20261027/`。

- `prepare.py`、`prepare_stride.py`：通过现有编辑器互斥桥提取两个当前下半身来源。
- `author.py`、`*-actions.json`、`authoring.json`：原生姿态制作与时间映射。
- `save_assets.py`、`save_all.py`：保存四个新动画包。
- `publish.py`：通过共享配置事务，只替换上述四个角色键。
- `assets-saved.json`、`published.json`、`delivery.json`：分别记录保存、配置与交付状态。

新资产目录为 `/Game/Characters/JasonPlayer20261003/Kukri20261024/ComboV3/{Jason|Kaitlin}/Animations/UppercutSwordLowerV1/`，分别命名 `A_Kukri_Uppercut_SwordLowerUpright` 与 `A_Kukri_Dual_Uppercut_SwordLowerUpright`。原动画保留。

已完成四个新动画资产保存与四个配置入口切换。正式 `FPSGAMEEditor Win64 Development` 构建于 2026-10-27 19:25 成功，退出码 0；后台 `save_all` commandlet 于 19:26 完成，退出码 0。源码权重调整已链接进入 Editor DLL。

本轮使用当时已运行的编辑器读取来源；保存前该编辑器自行退出，原 MCP 保存请求未执行，因此随后采用后台正式构建与无界面 commandlet 保存。没有主动启动或关闭图形编辑器，没有运行游戏、测试、截图、预览渲染或视觉验收，效果由用户测试。未打包、提交或推送。
