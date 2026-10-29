# 尼泊尔弯刀第三人称重击

2026-10-25，按用户确认的复用方案制作：以本地 CC0 Quaternius UAL2 `Sword Regular B` 和 `Sword Regular B Rec` 为动作基础，适配现有重击的右肩后蓄刀、快速向左下回砍和较慢收势。Jason、Kaitlin 各保存一段蓄力和一段释放，共四个原生动画。

保留源动作的躯干下压和回收时序，收住原动作的大幅转身；按各自原生骨长适配肩肘腕和刀刃安装坐标。前脚承重、后脚蹬地，回收分开调整双脚。左手蓄力时合拢成护拳，重击结束后放松。蓄力末帧与释放首帧使用同一份完整姿态，包含手指及辅助骨。

时序沿用既有执行器：蓄力作者长度 2 秒、60 fps；释放作者长度 35/30 秒、120 fps。Contact 标记为释放后 0.075 作者秒，Release 标记为 0.133 作者秒。实际播放速度仍由现有武技时钟决定。蓄力姿势在 0.80 作者秒进入保持段；释放带完整收势，最后回到当前待机。根运动关闭，沿用既有身体混合及副手所有权。

新资产位于已有 Cook 动画目录内，各身体均有：

- `.../ComboV3/Jason/Animations/HeavyV4/A_Kukri_HeavyCharge_ShoulderBack`
- `.../ComboV3/Jason/Animations/HeavyV4/A_Kukri_HeavyRelease_Diagonal`
- `.../ComboV3/Kaitlin/Animations/HeavyV4/A_Kukri_HeavyCharge_ShoulderBack`
- `.../ComboV3/Kaitlin/Animations/HeavyV4/A_Kukri_HeavyRelease_Diagonal`

上述前缀为 `/Game/Characters/JasonPlayer20261003/Kukri20261024`。共享 `player_body.json` 通过字段事务仅替换 Jason 和 Kaitlin 的 `Kukri.FullBody.Charge`、`Kukri.FullBody.Heavy`，共四个角色字段。普通连击、上挑、待机、第一人称、伤害及体力规则保持当前版本。

作者入口与保存脚本位于 `SourceAssets/KukriHeavy20261025`，依赖 `KukriThirdPerson20261024/ComboV3/author.py`、`inputs.json` 和 `KukriThrustHand20261025/author.py` 的原生骨架及握拳适配。`authoring.json` 记录源时间映射；`assets-saved.json`、`published.json`、`delivery.json` 分别记录保存、本地接入与交付。

后台 commandlet 已保存四个资产，退出码 0；四个配置字段已接入。本次没有 C++ 修改，无需新增原生构建。未启动可视编辑器或游戏，未进行渲染、自测、联机或视觉验收，由用户通过 F6 第三人称／固定第三人称体验。
