# 守寝者转向与围布修正 V10

> 历史制作记录；2026-10-17 当前 V18 移动仍被用户否定并转待办。旧版本源/资产可能已归档，恢复位置与当前状态以 [收尾记录](../Publication/NightWarden20261017/README.md) 为准。

2026-10-16 用户否定 V09，明确问题为“移动方向变了，身体仍朝原方向”，并反馈布料穿模。本轮按 `ue5-monster-workflow` 的移动与长衣修复流程开展，读取实际巫婆衣摆制作代码，不追加运行游戏、截图、渲染或验收。

## 已定位原因

蓝图保存的 `CharacterMovement.RotationRate` 为 Pitch=100、Yaw=0、Roll=0；原生默认值为 Pitch=0、Yaw=100、Roll=0。移动朝向开关已开启，网格也没有绝对旋转，实际问题是旧导入脚本将 C++ 的旋转构造顺序用于 Python `Rotator`，导致水平转向速度为零。V08 制作脚本和 V10 安装均改用 `Rotator(pitch=0., yaw=100., roll=0.)` 明确命名轴。

源模型测量显示大腿表面分段半径约 14–17 cm，旧碰撞体只有 8.3–8.5 cm；巨臂前臂表面约 9–11 cm，旧碰撞体只有 6.3 cm。布料进入身体后才遇到这些偏小碰撞体。旧内衬主要跟随骨盆，也无法贴随腿根。

## 按巫婆结构制作

- 完整身体：保留原 145,849 顶点、骨架和身体源对象，作为隐藏的完整制作源。
- 贴体内衬：复制覆盖区域的真实身体表面和原始蒙皮权重，向外偏移 7 mm；内衬 10,675 顶点。运行时身体副本只移除对应内衬覆盖的 17,844 个面，完整源模型不删减。
- 可见围布：连续环形腰带、外层破布及下摆，保留巫婆下裙的骨盆单锚定；不把完整裙片同时拉向两腿。静态外形按站立与参考姿态制作，下摆通过模拟抬起和折叠，避免把攻击全过程的横向范围固化成巨大裙撑。
- 模拟代理：1,360 个点，顶部两圈共 160 点固定，其余活动量渐增至 20 cm；代理不作为可见模型。
- 身体碰撞：扩至 11 个胶囊，大腿各三段、巨臂前臂两段，配合骨盆、腹部与巨掌。分段尺寸取实际对应肢体表面的 99 百分位半径并增加 5 mm 余量。

制作使用现有待机、行走及攻击的 530 帧动作数据，保留三段动作、移动速度和近战时钟。继续使用巫婆布料资产的稳定位置/法线/切线绑定与 Chaos；不在每次变向或攻击时反复重置布料。原生代码不需要变更或重新构建。

## 文件与接入状态

可编辑源：`SourceAssets/NightWarden20261015/V10TurningCloth/Authoring/NightWarden_ClothRepair_V10.blend`。

制作脚本为 `Scripts/author_cloth_v10.py`，安装脚本为 `Scripts/install_repair_v10.py`。`Scripts/v10_install.ps1` 在现有批次互斥内接入；有编辑器时沿用桥，没有编辑器时用无界面 commandlet。旧 V08 的轴顺序错误同步修正在 `Scripts/install_movement_v08.py`。

记录目录：`SourceAssets/NightWarden20261015/V10TurningCloth/Records`。`current_inputs.json` 保存蓝图与原生转向差异，`source_measurements.json` 保存身体分段尺寸，`authoring.json` 与 `cloth_manifest.json` 保存源模型及碰撞制作参数。

2026-10-16 20:11（Asia/Shanghai）已完成实际 UE 导入和保存。用户停止试玩后编辑器已关闭，本轮没有重新打开编辑器；后台 commandlet 正常退出 0。已修正参考姿态设置和材质槽读取的 Python 属性访问方式。最终后台导入日志报告 Success，0 errors。FBX 导入出现与既有 V07 相同的绑定姿态重建提示，导入器报告重建成功；这不代替实机变形确认。

`ue_delivery.json` 状态为 `yaw_and_cloth_repair_saved`、`complete: true`，保存了以下资产：

- `/Game/Monsters/NightWarden/V09Melee/ClothRepairV10/SK_NightWarden_ClothRepair_V10`
- `/Game/Monsters/NightWarden/V07WaistStride/ClothRepairV10/SK_NightWarden_ClothProxy_V10`
- 原 V07 骨架依赖，以及 `/Game/Monsters/NightWarden/BP_NightWarden`

布料保存回执为 1,360 个代理点、160 个固定点、20 cm 最大活动量、11 个碰撞胶囊，可见布料绑定在第 2 材质区段。蓝图编译保存后的转向值为 Pitch=0、Yaw=100、Roll=0，原待机、行走、攻击资源引用保留。F6 原入口继续使用该蓝图，用户试玩时重新生成角色即可加载修正版。

V09 旧资产保留，`Records/BP_NightWarden.before_v10.uasset` 保留替换前蓝图备份。源模型、导出文件、已保存 UE 资产均已完成。

未启动游戏或渲染。制作参数和资产保存不代表实机无穿模或外观已获认可，交付后由用户试玩确认。
