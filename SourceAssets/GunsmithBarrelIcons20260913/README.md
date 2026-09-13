# 枪管分类和短、长枪管图标

2026-09-13：补齐现有枪匠通用枪管改造的二维图标。

| 用途 | 生成源图 | 游戏引用 |
| --- | --- | --- |
| 左侧枪管大类、标准枪管 | `category_barrel.png` | `/Game/UI/GunsmithWorkbench/ColdGlass/T_Category_barrel` |
| 轻型短枪管 | `barrel_short.png` | `Content/ColdSteelData/AttachmentIcons20260913/barrel_short.png` |
| 重型长枪管 | `barrel_long.png` | `Content/ColdSteelData/AttachmentIcons20260913/barrel_long.png` |

三张均使用内置 imagegen 分别生成，原图和完整提示词保存在本目录及 `manifest.json`。采用现有冷钢图标的银灰金属、石墨暗部和斜向视图。短枪管采用紧凑轮廓与纵向凹槽，长枪管采用延长的平滑管体，便于在小图标中区分。图片只用作二维枪匠图标，不作为 PBR 贴图或模型替换。

原分类导入脚本将旧 `barrel` 候选导入为 `foregrip`，因此没有生成运行时 `LoadCategoryIcons` 所需的 `T_Category_barrel`。本目录 `import_category.py` 单独导入缺失的枪管分类纹理，沿用原 `M_CategoryIcon` 近黑背景透明合成材质。分类源图按该材质要求生成黑背景，短、长配件源图按透明 alpha 背景生成并原样复制。

现有 `UM4GunsmithWidget::BuildOption` 根据 `槽位_选项ID.png` 自动读取两张配件图；标准枪管 `false` 沿用分类画刷回退。新增图标覆盖使用通用 `common_options.barrel` 的枪械。原有短、长枪管数值、模型、动画和实例保存逻辑没有修改。

现有打包配置已包含 `/Game/UI/GunsmithWorkbench` 的 AlwaysCook 目录，以及 `ColdSteelData/AttachmentIcons20260913` 的 UFS 目录，无需新增打包规则。

导入脚本已执行成功并保存分类纹理，路径记录见 `import-result.json`。本次 commandlet 进程退出码为 1，汇总错误为工程已有的 GameFeatureData 注册配置缺失及 127.0.0.1:8000 端口占用；Python 导入未报错。完整日志保存在 `import.log` 与 `import-console.log`，不将导入结果称为游戏显示验收。

重新打开游戏会话后进入枪匠使用。本轮仅制作与接入，未主动运行游戏、测试、截图或渲染验收，由用户测试。
