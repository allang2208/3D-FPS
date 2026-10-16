# SUPER90 鸟笼消焰器

用户要求新增霰弹枪通用鸟笼消焰器，随后确定：减弱枪口火光，后坐力降低 15%，腰射散布降低 15%。本轮沿用已接入收束器的 SUPER90 枪口安装面，制作独立共享网格和选项。

## 模型与接入

配件 ID：`shotgun_birdcage_flash_hider`，名称「鸟笼消焰器」，槽位 `muzzle`。主体为短筒、实际纵向开槽与环形前缘，独立后端接座；三档 LOD 与四个材质区保存在 `/Game/Weapons/CommonShotgun/Birdcage20261015`。

`M4MuzzleVisual.cpp` 的 SUPER90 分支支持原厂、收束器和鸟笼三个选择；每款从自身静态网格 `Muzzle` 挂点设置特效出口。安装坐标继续使用已测量的上方枪管前端，原生枪体、骨架和动画保持原状。图标、异步资源准备、打包目录、世界挂件及既有 `gunsmith_parts.muzzle` 存档路径一并接入。

## 数值与火光

目录 `recoil_mult=0.85`、`hip_spread_mult=0.85` 沿现有属性计算、面板、玩家和服务端装备刷新生效。原厂与鸟笼的 `pellet_spread_mult` 默认 1；收束器的 0.65 保持独立，二者在同一枪口槽互斥。

`FPSWeaponFXComponent::MuzzleFlashVisualScale` 根据第一人称当前配件，或世界挂件的实际网格判断鸟笼。只缩减 Niagara 火光尺寸及发光、关闭额外侧焰、降低回退火焰与瞬时灯光，保留普通枪声、听觉噪声及原有烟雾。内部 `.35` 为美术表现系数，不表示屏幕亮度必然线性减少某个百分比。

后坐力和腰射散布百分比放在目录 stats/effects，由已有 UI 计算展示；外观描述不重复数值，消焰机制单独放入 `special_effects`。

## 制作记录

作者文件及构建/导入回执：`SourceAssets/Super90Birdcage20261015`。真实平直法线复制自现有共享收束器资产；没有使用引擎的砖墙 DefaultNormal。新资源使用独立路径，不覆盖收束器。

后台资产保存已完成，`install_receipt.json` 的 complete 为 true，网格包含三档 LOD，共保存七个资产。Game 与 Editor 常规构建最终均返回 0；初次 Game 构建遇到枪口状态 getter 缺失，在该接口补齐后重试成功，Editor 队列超时后重新提交并成功。

本轮仅制作、导入、保存及必要构建，未主动打开图形编辑器或运行游戏、联机、视觉与回归测试。实机效果由用户确认。
