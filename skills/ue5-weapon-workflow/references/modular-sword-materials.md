# 模块剑：连续接口、材质与改造目录

## 剑根和护手连续性

- 在连续母版上修形、生成法线后再切分可换部件；两侧独立压厚会形成台阶或反光接缝。移除旧封口面，保留同一接口位置、截面、边界法线和真实安装原点。
- 厚度统一针对金属主体，保留刃口、剑尖收薄。宝石及镶边作为完整结构归属一个部件，接口避开突出装饰；不要压平宝石来满足厚度数值。
- 先区分 UV 拉伸、贴图损坏和法线造成的碎亮反光。保留有效 UV、材质槽与纹样；按最终几何重建表面法线，导入时可由 UE 重建 MikkTSpace 切线。不要对所有面强制平滑。
- 当前高地母版为 `SourceAssets/HighlandClaymoreMeshy20260922/JunctionBlendV5_20260927`；棱脊刃用 `RidgePiercerRootV2_20260927`。V5 仍写入名称含 `SurfaceRepairV4_20260927` 的现役 UE 包，不能仅凭路径版本号将其归档。

## 有选项但模型不变／白膜

- 改造选项目录与装配模型目录要在同一生命周期刷新。`ModularSwordVisual` 的进程级静态缓存曾让新握柄持续退回 factory；由 `LoadMeleeCatalog()` 同步调用 `ResetCatalogCache()`。新增字段或模型时仍沿用 `gunsmith_parts` 保存合同。
- 共用外形不代表共用安装变换。两款通用握柄分别制作符文剑、寒晶剑、高地剑的接口适配，保留各宿主端点与手握区；案例 `SourceAssets/SharedSwordGrips20260927/read_mounts.py`。
- 开启 Substrate 的工程里，传统 BaseColor／Normal 接口有节点不等于材质已接通。握柄修复使用 `MaterialExpressionSubstrateShadingModels` 连接 `FrontMaterial`，并接入基色、法线和 ORM；配方见同目录 `grip_materials.py`、`repair_materials.py`。透明灵体使用 Unlit BSDF 的透射路径，见 [飞剑](rune-blade-burst.md)。

## 效果作用域

- 共用剑类组件中的专属效果必须在出手时按武器定义快照，不能把 `IsEquipped()` 当成符文长剑身份。命中减冷却只属于 `ue_rune_sword`，同挥一次；高地剑不继承。
- 第三段、重击、快速近战的韧性倍率分别进入对应快照，不能乘进全部攻击。概率流血只在有效命中后每目标抽一次，复用已有层数系统；范围配重改造只改变命中目标数量，不放大原判定半径和距离。
- 图标用当前实际模块源，按 [灰阶规范](attachment-icons.md) 制作。后台制作与资产保存不代表游戏验收，默认交由用户测试。

## 整段剑身材质与符文的组合（2026-11-01）

剑身材质按实际几何和 UV 归属覆盖，不能仅按改造栏位或组件名筛选。符文长剑在 Z=12.5 cm 切分，剑根承接面属于护手；原厂、通用和 Meshy 护手均需保留其原生映射。当前打包遮罩 R=剑身刻纹、G=剑根刻纹、B=剑根覆盖；剑身与护手分别设置 `BladeFinishGuardRoot=0/1`，保留宝石、外翼、封口及发光的独立区域。此范围是该母版合同，不能复制到其他剑的 UV。

先选择原生金银符文材质，再设置 `BladeFinishMode` 和区域参数；先设置参数再换材质会丢失 MID 状态。恢复原厂必须显式写入模式 0。持握、预览和观察者共用材质应用函数，材质单独变化也进入装配缓存键。Substrate、湿润、法线和发光链路继续保留，不以只调基色代替完整材质接入。

纯外观升级为数值改造后，旧 `install_catalog.py` 只是初始化配方；最终目录以已批准的数值表为准，不能重跑旧空 stats 覆盖当前配置。大马士革的近战暴击率／暴击伤害进入实际武器命中快照，不写角色全局魔法暴击；G 飞剑的武器输入单独排除 `blade_material`。详见工程 `Docs/Weapons/sword-full-blade-finish-20261101.md` 和 `SourceAssets/SwordBladeMaterialStats20261031/install_stats.py`。
