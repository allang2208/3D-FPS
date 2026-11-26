# 符文长剑专属材质：寒晶

2026-11-01，按用户要求接续剑身材质试点。改造入口为符文长剑 → 剑身材质 → 寒晶；目录 ID 为 `frost_crystal`，材质模式为 6，品类为专属。只开放给 `ue_rune_sword`。

## 外观

从寒晶双手剑实际剑身模块 `SM_FrostSword_Blade_factory` 的现役材质 `M_FrostCrystalSword_SeamlessBronze` 读取来源。沿用其寒晶表面的 BaseColor、Normal、Roughness、Metallic 四路原始贴图，排除皮革与青铜区域，按正反面几何映射重新烘焙到符文长剑 UV0；法线细节通过供体与目标的切线坐标转换。没有替换模型或动作。

四张 2048 贴图保存于 `/Game/Weapons/AzureRunesword20260913/FrostFinish20261101`。原生普通／金色符文两套主材质增加模式 6 分支，继续使用整段剑身覆盖遮罩；剑身、护手剑根承接面连续覆盖，宝石、护手外翼、原生符文发光、Substrate 和湿润链路沿用原规则。其他材质分支与原厂模式 0 保留。

选项图标复用已存在的寒晶剑身灰阶金属框图，保存为独立的 `ue_rune_sword_blade_material_frost_crystal` PNG 和 Texture2D。

## 被动与数值

安装“寒晶”后获得与寒晶双手剑原生侵蚀相同的附加魔法伤害：智力×50%＋精神×50%（2026-11-01 按用户要求由各10%上调）。制作脚本直接从 `items.json` 的寒晶剑原生系数字段读取，再写入现有改造系数 `rune_intelligence` / `rune_wisdom`，通过既有 `WeaponDamagePanel::Evaluate` 进入武器伤害和攻击快照。沿用攻击倍率、魔法伤害加成与目标魔防结算，不提升角色全局魔法攻击力。

材质不占符文槽，能够与侵蚀符文的附伤相加，也能与其他符文组合。更换材质时移除这份附伤，符文长剑原有被动保留。没有新增寒冷、冻结或减速。寒晶剑专属的精神迸发仍只对原寒晶剑开放。

沿用现有剑身材质范围：G 飞剑在计算武器贡献前排除 `blade_material`，因此不获得本项附伤。没有新增每帧 JSON 读取、伤害事件或全局属性修改。

改造台以绿色“寒晶侵蚀”特效段描述机制，不额外列攻击分段或附伤拆分卡。目录只合并新选项，未重跑会清空其他材质属性的旧初始化脚本。

## 存档与外观同步

继续使用 `gunsmith_parts.blade_material`。持握、改造预览、掉落与世界装备沿用已有装配；第三人称描述已有的 `BladeFinishMode` / `bBladeFinishGuardRoot` 字段携带模式 6。原生源码只将模式上限从 5 扩展至 6，没有新增复制字段或存档迁移。

## 制作入口与交付边界

作者目录为 `SourceAssets/RuneSwordFrostMaterial20261101`：

- `read_source.py` 读取现役供体材质，结果见 `source-material.json`。
- Blender 后台运行 `extract_source.py` 提取供体几何、UV 和切线；Python 运行 `bake_transfer.py` 制作目标贴图，结果见 `transfer-receipt.json`。
- `install_catalog.py` 合并两份正式目录，结果见 `catalog-receipt.json`。
- `run_asset_task.ps1 -Script install_materials.py` 实际导入贴图、修改主材质并保存图标；结果见 `material-receipt.json` 与 `install_materials-process.json`。
- `build.ps1` 后台构建 Editor 模块；最终状态见 `build-receipt.json`。

重建顺序：已有基础材质／大马士革／陨铁／最终数值表／整段剑身覆盖完成后，再运行本目录的制作和安装入口。纹理来源沿用原 Meshy 寒晶剑资产，不在本任务扩大源资产分发许可。

本次不启动图形编辑器，不执行游戏、联机、截图或视觉验收。资产保存与编译完成不代表实战及画面通过；由用户自行测试。

必要构建首次遇到 `WarhammerSlamFXSubsystem.cpp` 与 `ThunderHammerFX.cpp` 的匿名命名空间 `Capacity` 在 Unity 编译中重定义。仅将前者的池容量常量改名为 `SlamFXCapacity`，值仍为 8，相关逻辑不变；本项为构建解阻。

最终交付：两份目录、四张贴图、两套主材质和图标已实际保存。`FPSGAMEEditor Win64 Development` 后台构建成功，日志为作者目录的 `build-editor-20261101-135520.log`；未运行游戏测试。

后续数值调整：`set_coefficients_50.py` 将寒晶剑本体与符文长剑寒晶材质同步改为各50%，同步寒晶剑特性及精神迸发合计说明。精神迸发保留原来的自带侵蚀×2，因此寒晶剑装备后为智力×100%＋精神×100%。本次仅改目录，无需重编译或重导材质，未运行游戏测试。旧寒晶剑物品沿用正常档案加载时更新原生系数的既有迁移。
