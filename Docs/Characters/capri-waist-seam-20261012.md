# 七分裤腰部漏空修复

用户截图显示裸上身与烟灰七分裤之间透出背景。读取当前装备确认正在使用七分裤高筒靴版本、皮靴和背包；皮肤材质已绑定。

七分裤沿用了长裤的身体遮挡区段 `[8,10,12,14,16]`，没有像小腿一样补回自身腰口所需的原生皮肤。腰口附近隐藏的是整块身体三角面，且裤装与身体各自蒙皮；动作后裸上身的可见边界和裤腰之间缺少皮肤覆盖。这是穿戴网格的缺面覆盖问题。

## 制作

- 从当前 `ArmoredBoots20261004/SK_Jason_Base` 中提取被七分裤隐藏、延伸到参考空间 Z=90 cm 以上的腰部原生三角面。只补被裤装隐藏的区域，保留原位置、逐角 UV、法线和骨骼权重；补片下沿延伸到裤腰内部。
- 将补片追加到七分裤现有皮肤材质槽 5。普通版和高筒靴版均使用相同的原生腰部，骨骼按名称映射。裤装本身、已焊接的裆缝、小腿和衣料材质保持原样。
- 沿用现有三档 LOD、边界锁定和骨骼边界约束。无新增运行组件、Tick、材质或贴图。
- 补片源为 `SourceAssets/SmokeGreyCapri20261004/native_waist.json`，两份穿戴源 JSON 同步更新；`prepare_runtime.py` 接入补片，后续重制保留修复。图标和地面掉落仍使用纯衣物模型。

## 保存范围

- `/Game/Characters/ModularOutfit20260924/SmokeGreyCapri20261004/SK_Jason_SmokeGreyCapri`
- `/Game/Characters/ModularOutfit20260924/SmokeGreyCapri20261004/SK_Jason_SmokeGreyCapri_HighBootsFit`

制作入口：`Tools/SmokeGreyCapri/save_waist_repair.ps1`；执行脚本为同目录的 `save_waist_repair.py`。原始穿戴包和源 JSON 已归档到 `trash/player-presentation-retired-20261012/SourceAssets/PlayerWaistSeam20261012/Before/`。

本次没有修改 C++，无需重编译原生模块。资产保存状态以 `SourceAssets/PlayerWaistSeam20261012/saved.json`、最终 `save-bridge-02.txt`（失败尝试日志已移入本轮 trash） 为准；不主动启动编辑器界面或游戏，不进行截图或运行验收，最终画面由用户测试。

两种穿戴资产均已保存，每种补入 1,096 个原生腰部三角面并重建三档 LOD，两份制作源 JSON 已同步。普通版由后台命令保存，高筒靴版在用户结束 PIE 后经已有编辑器桥保存，最终批次 `save-bridge-02.txt` 返回 `CAPRI_WAIST_REPAIR_COMPLETE`；保存回执为 `saved.json`。未运行游戏或视觉测试。
