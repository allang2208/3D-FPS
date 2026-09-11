# Gunplay 发布检查（2026-09-11）

本次只发布准心/腰射散布、ADS 水平后坐力及数值显示、收益颜色、命中提示、枪口发射点、曳光和 V5 烟火的代码与文档。共享源码按块暂存；AKM 装配、附魔、滑铲、背包等并行未提交改动保留在工作区。

- 从暂存区导出临时快照独立编译：Editor Development 成功（113 actions）。
- 该快照使用本机已许可 Content，独立审计存档实机：BallisticPresentationAudit 67 / 67；后坐力与 UI 验收 78 项通过。
- [弹道断言](ballistic-assertions.txt)、[数值及颜色断言](handling-assertions.csv)、[提交源码散列](source-sha256.json)。对应日志原名 BallisticPresentationAudit-20260911160847.log、WeaponHandlingAudit/GunplayPublication_0911-runtime.log。
- V5 生成器从原始 Epic NS_MuzzleFlash 独立重建两个 Probe 资产，均 valid=1，参数断言成功。commandlet 的既有 GameFeatureData/端口日志不算生成器失败，亦不宣称整个 commandlet 零错误。
- [13 个废案归档清单](../gunplay-archive-20260911.json)：移动后逐文件 SHA-256 核验。最终 V5 和原始 Epic 包保留；历史画面对照和最终 V5 预览保留在 Saved/EpicGunFX。
- 临时验证快照已归档到本机 trash/gunplay-vfx-20260911/publication-validation，1502 个普通文件逐一验散列；详见同级 publication-validation-manifest.json。Content 目录联接仅作为联接保留，指向正式工程 Content，素材未复制或移动；勿沿该联接清理正式素材。
- Python 语法、技能双份散列、暂存差异空白、文件大小、敏感串扫描通过。本次不公开上传 Epic 派生 uasset、模型、贴图或音频；[资源恢复说明](../AssetSetup.md)。

技能新增 [Gunplay 与 Niagara 验收](../../skills/ue5-weapon-workflow/references/gunplay-vfx.md)，同步个人技能及工程镜像。未改变现有技能授权范围。
