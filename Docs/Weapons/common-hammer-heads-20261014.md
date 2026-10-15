# 通用锤头改造：三款

当前活动模型已继续按设计图构造成 DesignV2，见 [设计图建模构造 V2](common-hammer-heads-design-build-20261014.md)。改造 ID 保持不变；按用户本轮要求，轻量鼓锤物理伤害调整为 -10%，其他属性保持原值。当前图标以 [图标修正及中央锤座设计](warhammer-icons-and-seat-design-20261014.md) 为准。

为已拆分的双侧锤头槽制作三款不同模型与直接属性改造，当前接入锻钢战锤 `ue_steel_warhammer`。三款共用改造 ID 和属性库，其他锤类宿主可复用同一选项；新宿主仍需按自己的实际安装端适配，不宣称任意锤座无需适配即可互换。

| 名称 / ID | 外形 | 物理伤害 | 攻击速度 | 体力消耗 | 韧性伤害 |
| --- | --- | --- | --- | --- | --- |
| 重铸方锤 `heavy_forged` | 宽厚方头、阶梯收肩、大倒角 | +20% | -10% | +15% | +15% |
| 破韧棱锤 `flanged_breaker` | 八道放射棱翼、收边端面 | -5% | -5% | +10% | +40% |
| 轻量鼓锤 `light_drum` | 紧凑鼓形、环槽束腰、内凹端面 | -10% | +15% | -12% | -15% |

物理伤害作用于基础和附加物理伤害，魔法伤害不随之缩放。普通连击、重击、冲刺砸地及冲击波沿现有伤害快照读取改造后的伤害与削韧；不改变判定距离、范围、蓄力阈值、冲击波半径和攻击阶段倍率。攻击速度沿用当前普通／重击出手时钟；冲刺武技仍使用独立速度。体力倍率只结算一次，工作台草稿仅替换该倍率，不改变真实装备。

## 制作与接口

作者目录：`SourceAssets/CommonHammerHeads20261014/`。原装连接端来自 `SteelWarhammer20261014/ModulesV1/Warhammer_Modular_Editable.blend` 的 `SM_Warhammer_hammer_heads_factory`。保留中央座接口 X=±0.040 m 和其外侧原装颈部，外形重建从 X=±0.075 m 的实际截面顶点环开始，首段延续原颈法线对应的径向斜率，再过渡到各款锤体。模型仍是左右成对的一件静态网格，沿用 Z=92.500001 cm 的装配偏移和现有骨骼挂载变换。

可编辑源 `CommonHammerHeads_Editable.blend` 保留三款模型；`Export/` 为三个 FBX，`interfaces.json` 保留实际安装段边界。三角面数分别为 14,206／14,206／16,444，没有复制整把武器或手臂动画。

原装颈段继续使用原战锤 UV、材质与法线。新锤体有独立钢材基色、金属度／粗糙度、法线贴图；过渡段用顶点色在原钢材与新钢材之间渐变，保留接口处的原表面。新材质使用 Substrate，按静态附件用途导入。

三张共享图标键为 `hammer_heads_<id>`，不为当前武器再复制三张专属图。早期脚本生成的简化边框和成对主体已被用户指出不符规范，当前版本改用认可的 `muzzle_brake_framed_v2.png` 母版与实际 DesignV2 单侧锤头素材，经 imagegen 重做；正式母图在 `SourceAssets/WarhammerIconCorrection20261014/Final/`。

## 数据与实现

- `catalog.py` 是三款名称、直接属性和说明的制作源；`register_heads.py` 生成／合并 `Content/ColdSteelData/common-hammer-heads.json`，按相同 ID 更新对应模型配方，并保留其他槽位与选项。
- `warhammer-gunsmith.json` 的 `hammer_heads.options_library` 引用共享库；`WarhammerGunsmith.cpp` 合并本栏选项与共享选项，读入 `FMeleeModifiers`，沿用选中／应用／撤销和 `gunsmith_parts` 实例保存。
- `ProductionToolStats.cpp` 将锤类改造接到既有钝器伤害、动作速度、体力与削韧评估；主机、客机请求的权威攻击和冲击波继续消费同一份快照。
- 详情卡、总览、物品提示和装备比较读取实际评估值。只展示直接属性，不展开攻击分段或附加伤害金额，不编造触发特效。
- 模型与原装件复用 `ModularSwordVisual` 的同一装配入口，覆盖持握、改造台草稿、背包图标、第三人称装备捕获与掉落物。

后台制作、导入、保存与必要构建属于本轮交付；不启动编辑器界面、游戏、截图或验收。具体完成状态以 `import_receipt.json`、`commandlet_receipt.json`、`build_receipt.json` 为准，运行效果由用户测试。

本轮结果：三个网格、三张钢材贴图、一个 Substrate 材质和三个共享图标共 10 个 UE 资产保存完成，导入 commandlet 返回 0，三个选项已写入正式目录。Editor 与 Game 常规后台构建均返回 0。本轮未运行游戏、视觉或联机测试。
