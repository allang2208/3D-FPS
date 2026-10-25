# 战术弹匣腰带：精细模型交付

本批交付模型、材质、男女原生骨架绑定及导出文件。沿用 `Reference/approved-concept.png` 的炭黑腰带、灰色扣具、橄榄灰加固织带与四个插槽设计。

## 模型内容

- 双层承载腰带、分段网眼缓冲垫、双道实体缝线、包边、模块织带环、折返固定带。
- 分体扣具、穿带窗口、凹入式释放片、铆钉与制造倒角。
- 两个步枪弹匣槽、两个手枪弹匣槽，均具有实际开放槽口、内壁、底托、外层织物、弹性束带、加固带与背部安装结构。
- 两种独立游戏弹匣外观模型：弧形步枪款、直身手枪款；外壳、握持肋、分型线、独立底板和封闭端部。四个插槽各有单独可选的装入实例。
- 弹匣与插槽使用同一份造型包络参数。男女款共用附件尺寸，只改变腰带曲面及附件安装位置。

## 男女适配

`inputs.json` 记录了本批读取的 ST6 战术裤资产路径、已保存包的 SHA256、几何缓存和原生身体权重来源。此批以这些裤装为穿戴基准。

每个身体沿裤腰取 256 个方向、9 个高度层，建立独立腰线和环形曲面；保持实际前后高低变化。插槽安装位置另使用其完整高度和宽度覆盖的裤腰／髋部外表面确定避让距离，安装织带再绕回该身体的腰带曲面。

柔性腰带使用身体邻近表面的插值权重，扣具、插槽及装入弹匣各自使用统一的局部锚点权重，并保留原生骨架。原生参考姿态中的弹匣座位、局部轴和锚点权重写在 `Authored/*_attachments.json`。

后续新增身体或换用另一款裤装时，应读取对应裤装的已保存几何，重新建立腰带曲面和安装座距离；附件尺寸不随身体整体缩放。此批没有覆盖所有裤装或厚外套组合，也未进行动作测试。

## 文件

| 内容 | 路径 |
| --- | --- |
| 男性完整可编辑源 | `Exports/TacticalBelt_Jason_Editable.blend` |
| 女性完整可编辑源 | `Exports/TacticalBelt_Kaitlin_Editable.blend` |
| 两款空槽整体 | `Exports/TacticalBelt_{Jason,Kaitlin}_Empty.glb` |
| 两款装入弹匣整体 | `Exports/TacticalBelt_{Jason,Kaitlin}_Loaded.glb` |
| 腰带原生绑定三档 LOD | `Exports/SK_TacticalBelt_{Jason,Kaitlin}_LOD{0,1,2}.fbx` |
| 独立步枪弹匣外观 | `Exports/RifleMagazine.glb`、`Exports/SM_RifleMagazine_LOD{0,1,2}.fbx` |
| 独立手枪弹匣外观 | `Exports/PistolMagazine.glb`、`Exports/SM_PistolMagazine_LOD{0,1,2}.fbx` |
| 原生厘米坐标、权重及角点 UV／法线 | `Authored/TacticalBelt_{Jason,Kaitlin}.json` |
| 制作记录 | `authored.json`、`Authored/*_production.json` |

Blender 源中保留独立部件、隐藏的 LOD、原生参考、物理表面高模和插槽锚点。独立弹匣母版位于男性源的 `05_MAGAZINE_MASTERS` 集合；女性款使用相同造型。

## 材质与后续接入

9 组物理尺度 PBR 表面，共 36 张 BaseColor／Normal／ORM／Height 贴图，另有实体缝线材质。网眼、尼龙、织带、弹性织物、聚合物及涂层金属分开制作；法线和高模位移源自相同高度场。平铺尺度为 4 cm，法线为 OpenGL，后续 UE 导入需翻转绿色通道。`Textures/HIGH_*.npz` 保留原始高度场。

当前导出保留 10 个材质槽。三档 LOD 分别保留近景实体细节、缩减缝线与曲面分段、移除微小实体缝线；面数仅记录模型复杂度，不代表运行性能已验收。

运行 `Tools/TacticalMagazineBelt/run.ps1` 可使用冻结的输入重新后台制作；`-RefreshInputs` 更新输入来源，`-RebuildTextures` 重做表面图。几何基础函数已冻结到本任务目录，来源写在 `primitive_provenance.json`。

## 游戏接入

装备名称为「战术弹匣腰带」，Definition 为 `ue_tactical_magazine_belt`，使用已有的 `belt` 腰带栏（槽 10）及 2×1 背包占格。

UE 资产保存于 `/Game/Characters/ModularOutfit20260924/TacticalMagazineBelt20261024`。包括男女独立原生骨架的装载／空槽版本、两种独立弹匣道具、掉落模型、写实背包图标及材质。穿戴版本沿用现有异步换装和 Leader Pose，覆盖世界身体与本人低头身体；槽 10 使用已有装备同步数据，换装缓存键包含腰带。

目录注册由 `Tools/TacticalMagazineBelt/publish.py` 按本物品字段写入 `items.json` 和 `modular_outfits.json`，保留其他物品及身体设置。F6 的物品列表读取同一目录：进入游戏后，在「F6 → 基本调参 → 生成物品」选择「装备 → 腰带 → 战术弹匣腰带」。目录在新游戏实例／角色 BeginPlay 读取。

本轮默认穿戴与掉落外观带四个弹匣。它们当前为外观道具，尚未实现可操作的弹匣库存、容量或取弹动画。2026-10-25 已按用户要求追加换弹速度加成及强化，见下方；价格、防御及强化防御仍为 0，未修改其他装备属性或套装。

`saved_assets.json` 记录实际资产保存，`build_receipt.json` 记录 Editor／Game 构建，`published.json` 记录本地目录接入。首次交付没有启动游戏测试；后续应用户要求进行的专项检查另记在下方及 `Review20261024`，不能仅凭构建回执推断运行结果。继续制作／接入入口为 `Tools/TacticalMagazineBelt/integrate.ps1`。

本轮因 D 盘写满，将本任务两份旧 `.blend1` 备份及独立图标场景保留到 `E:/FPSGAMEAssetCache/TacticalMagazineBelt20261024`；当前男女可编辑母版仍在本目录。`Delivery` 是指向该目录中可重建中间数据的目录联接，路径记录在 `storage.json`。

## 2026-10-24 至 25 日专项检查

范围为本次战术弹匣腰带的制作、目录接入、男女穿戴和联机生命周期，不代表所有历史服装均重新验收。

已修复两处问题：

1. 女性装载版腰带的骨骼网格在加载时修正构建数据，但修正结果没有落盘，导致新进程重复构建。导入流程现先完成三档渲染 LOD 再保存；已修复现有资产。独立进程重新读取的 77 项资产检查全部通过，未再次出现该构建警告。
2. 通用掉落物 `OnRep_SharedItem` 重建物品外观时关闭客机物理，可能覆盖先到达的运动复制状态。客机腰带曾停在生成高度，主机已落地，因而拾取目标不一致。回调现恢复已收到的物理复制状态及位置目标；保留原有服务器距离、视线和库存校验。Editor 和 Game 构建均成功。修复后的双端落地、聚焦拾取及重新装备均已通过。

最终联机记录为 `Review20261024/Network_20261025-000750/summary.json`，13 个阶段、24 份双端状态全部通过。覆盖男女互换、穿脱、本人／远端网格与 Leader Pose、单穿腰带、丢弃、正常聚焦拾取、Pawn 重建后的装备恢复、断线重连和存档恢复。最后一轮主客机落地位置差为 0.378 cm，双方速度均为零；重连时在测试脚本再次操作之前已从独立存档恢复装备。完整范围与矩阵见 [review_summary.json](Review20261024/review_summary.json)。

证据位于 `Review20261024/assets.json`、`build-cache-validation.json`、`pickup-replication-fix.diff`、`native_build_receipt.json` 和各次 `Network_*/summary.json`。失败尝试保留原始记录，不能当作通过记录。

联机测试使用外置插件、两个后台游戏进程、独立存档、独立 UDP 端口，每端模拟 60 ms 延迟与 3% 丢包。插件不安装到正式项目。UE 5.8 未烘焙 `-game` 模式加载新动画曲线元数据时会调用空的编辑器事务对象；测试进程先以非事务方式载入现有曲线名，避免这一环境问题，不保存或修改正式骨架与动作资产。

该次专项检查时尚未实现可操作的弹匣库存、容量、取弹动画及数值加成。数值加成随后按下节请求追加。当前腰围基准为男女 ST6 战术裤；未完成所有服装组合、完整动作穿模、画面与性能、跨机器网络、专用服务器或打包版本验收。

## 2026-10-25 换弹速度与强化

目录新增 `bonusStats.reloadSpeed=0.025`、`bonusPerEnhance.reloadSpeed=0.005`、`enhancement.maxLevel=15`。强化等级从 +0 开始，每次成功强化增加 0.5 个百分点，+15 时为换弹速度 +10%。沿现有换弹速度公式除以速度倍率，不将速度加成当成等额耗时缩减。

强化入口支持该物品单独配置的上限，不提高其他护甲的全局上限，也不为了允许强化而增加防御。成本和成功规则沿用现有强化系统。装备属性计算、物品摘要、详情以及强化前后预览读取相同的基础值、成长及有效等级。

旧物品在既有目录迁移中补齐基础加成、每级成长及强化设置，保留实例 ID、位置、强化等级和附魔；联机客机配置、服务器影子配置与镜像接收使用现有迁移路径。需使用新构建启动新的游戏实例后生效。本次 Editor／Game 构建成功；未启动游戏或追加联机测试，前次专项检查结果不代表本次数值已经运行验收。回执为 `ReloadBonus20261025/catalog_receipt.json` 和 `ReloadBonus20261025/build_receipt.json`。
