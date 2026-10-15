# 陨星熔核：精细模型与熔岩发光

锻钢战锤 `ue_steel_warhammer` 专属传说锤头，选项 `meteor_core`，槽位 `hammer_heads`。按用户认可的 概念图（本机文件 `SourceAssets/SteelWarhammerLegendaryHeads20261014/MeteorCore/ConceptV1/meteor-core-design.png`，不随 Git 发布） 于 2026-10-15 制作；概念目录日期沿用首次设计日期。

## 外形与实际接口

一个模块成对替换左右锤头；原装中央锤座、颈环、长柄、握持与配重继续使用现有模块。原装锤头连接颈取自 `SteelWarhammer20261014/ModulesV1/Warhammer_Modular_Editable.blend`，保留实际 X ±4 cm 安装面至 ±7.5 cm 的原装几何、面角 UV 和自定义法线；外套连接环覆盖裁切端。模块原点、朝向和 Z 92.5 cm 装配偏移保持原接口。

- 八棱锤面具有多层收肩、实体倒角、浅凹锤面和青铜细嵌边。
- 每侧锤面有 8 道长短交替的星纹浮雕，中央为青铜环与深色圆芯。
- 双侧共 32 个实际透空窗口，保留框壁厚度、转角、纵向承力筋和实体固定销。
- 每侧青铜符箍有 24 枚周向浅刻纹，以同一参数域制作凹刻法线、底色与粗糙度；两侧共 48 枚。边缘另有实体包边。
- 内核为粗糙且不透明的桶形陨石，起伏与裂隙凹陷落实为网格，表面具有一致的 PBR 和发光遮罩。
- 双侧合计 81,661 三角面、5 个材质分区；保存 141 个具名可编辑层件及合并运行副本。近景细节用于实体厚度、窗框倒角、星纹、销钉与核心轮廓，没有进行帧率或性能验收。

可编辑源 `MeteorCore_Detailed_Editable.blend`，FBX 为 `Export/SM_WarhammerHeads_MeteorCore_V1.fbx`。隐藏的 `Editable component layers` 集合保留独立制作件；可见对象为成对运行模块。`author_geometry.py` 与 `author_textures.py` 可重建当前制作。

## 熔岩材质

`M_MeteorLavaCore` 使用 2048×2048 的 BaseColor、Normal、ORM 和 Heat 图。Heat 的 R 是稀疏熔岩裂隙，G 是空间相位，B 是全部凹陷裂隙。发光只出现在内部核心的裂隙，冷却表面保持暗色且不透明。

`lava_emission.hlsl` 以固定表面遮罩、材质时间和空间相位计算缓慢流动与脉动；发光强度 5.5，脉动速度 0.85 rad/s，流动速度 0.70 rad/s，暗橙向局部亮橙过渡。三个参数和两种发光色均保留材质参数入口。没有新增 CPU Tick、点光源或透明外壳；网格引用同一材质可用于装备、改造预览和掉落显示。游戏中的泛光程度仍取决于当前渲染设置，未运行视觉验收。

钢材沿用当前战锤与通用锤头的保存材质；新增普通青铜、符箍青铜与熔岩核心三份不透明材质。青铜贴图 1024²，周向符箍 512×2048；OpenGL 法线导入 UE 时翻转绿色通道。所有新材质使用静态网格用途，支持项目当前 Substrate 输出。

## 正式图标与接入

图标从最终模型的单侧实体制作，锤面向左、连接端向右，保持实际三维视角。`MeteorCore_IconSource.blend` 与 `IconSources/meteor_core.png` 保留灰阶制作源；彩色运行材质不受图标去色影响。正式图标由内置 image_gen 按 `icon-prompt.txt` 和现有认可框母版合成，专属加载键为 `ue_steel_warhammer_hammer_heads_meteor_core`。

运行包目录 `/Game/Weapons/SteelWarhammerLegendaryHeads20261014/MeteorCore/BuildV1`。独立选项写入 `warhammer-gunsmith.json` 的锤头本地选项列，模型映射写入 `warhammer-modules.json`，不会加入通用锤头库。`GunsmithModificationTier.h` 仅对锻钢战锤、锤头槽和该 ID 返回传说品质。

初次建模只制作外形和发光，回执保留当时的中性数值。后续已配置 [BalanceV1](../BalanceV1/README.md)：物理伤害 +40%、攻击速度 −15%、攻击体力消耗 +25%、韧性伤害 +40%。又按用户要求加入 [震荡扩散](../ShockwaveRangeV1/README.md)：重击与冲刺攻击冲击波半径 +50%，当前 3 m → 4.5 m。外形注册入口继续保留正式目录中的数值与特效文案，熔岩材质效果保持原样。

后台 commandlet 已保存 15 项 UE 资源：10 张 PBR/Heat 贴图、3 个新材质、1 个成对锤头网格和 1 张专属图标。钢材只读复用原包。`import_receipt.json` 为 `complete=true`，`commandlet_receipt.json` 为退出码 0，`registration_receipt.json` 记录正式选项和模型映射。首次导入的 Substrate 发光引脚名称错误已按当前引擎源改为 `Emissive Color`，随后从已保存资产之后继续完成；失败日志保留在 `ImportAttempt1`，不作为完成回执。

必要原生构建的最终状态见 `delivery.json` 及本目录 Game/Editor 构建回执。

按用户规则不启动游戏，不进行自测、额外预览或验收渲染；正式 UI 图标属于制作资产。实际装配与视觉效果由用户测试。
