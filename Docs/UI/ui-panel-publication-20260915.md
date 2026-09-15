# 冷钢 UI 与必要系统源码发布 · 2026-09-15

本批发布右侧状态／背包／技能入口、冷白装备浮窗、加工角标圆角、改造台选中详情及流动效果、快捷栏冷却表现、剑动态预览、近战资源读数，以及双持手枪主副手共用字号和布局。

用户明确同意连同 UI 所需的双持、体力、强化及技能源码一起发布。共享角色、控制器、伤害公式、技能运行时、库存和存档入口随必要依赖纳入；地形、树木生长呈现及其他不相关制作文件保留在本机。源文件清单和纳入原因见 [源码发布范围](ui-panel-source-scope-20260915.json)，最终提交文件以 Git commit 为准。

## 资源恢复

- 三个入口运行图为 `Content/ColdSteelUI/Icons/Navigation/{status,backpack,skills}_subject.png`。来源、完整提示词及抠图记录位于 `SourceAssets/PanelNavigation20260915`；二进制保留在本机，散列见 [本地资源清单](panel-navigation-local-assets-20260915.json)。
- 恢复时从授权宿主拷贝上述透明 PNG 至相同相对目录。需要重新抠图时先恢复 `SubjectOnly/*_generated_rgb.png`，准备 Python、Pillow、NumPy、rembg、onnxruntime 及 `isnet-general-use` 模型，再运行 `python Tools/UI/export_navigation_subjects.py`。模型及第三方依赖遵守各自许可，不随本批提交。
- 被首次生成器烘焙进 RGB 的棋盘格不会自动变成透明；保留成功抠图所用 RGB、全尺寸 RGBA 和原始带框源图，它们均为有效生产来源。
- 字体、武器／双持手臂／剑／火球动画、材质、音频、场景及生成图属于本机内容依赖；按 [资源恢复约定](../AssetSetup.md) 和各系统制作记录恢复。源码、软路径和生成记录不等于完整 Content 备份，也不表示原资产已获得公开再分发许可。
- `Config/DefaultGame.ini` 仅合入本批所需新增内容目录的 cook／UFS 条目，保留远端已有条目；其他打包配置变更留在工作区。

## 废案归档

三个旧版带底框运行 PNG 及相应导入 uasset，共六个文件移至 `trash/ui-panel-polish-20260915/Content/ColdSteelUI/Icons/Navigation/`。原路径、替代物、字节数和归档后核对的 SHA-256 见 [归档清单](ui-panel-archive-20260915.json)。trash 不提交 Git；有效源图、生成记录、抠图工具及历史设计说明保留。

## SKILL 与发布检查边界

已将双持共建布局、近战权威数据估算、主体缩放与固定命中区域、导航弹层转发及源图归档边界沉淀到 [HUD 导航与武器资源栏](../../skills/ue5-ui-umg-slate/references/hud-navigation-and-weapon-readouts.md)，同步个人技能与工程镜像。浮窗、圆角与动态预览经验继续留在对应引用中；数值规范集中在正式 UI 规则。

本批仅执行用户要求的仓库发布检查：远端、提交范围、差异、文件大小、敏感信息、公开资源边界、归档散列及技能／文档链接。既有 `Docs/AssetSetup.md` 暂存内容和其他并行修改不随本批带入。使用独立临时 Git index 制作本批提交，仍直接从 D 盘工程的 main 普通推送；不建立第二份源码工作区。

此前双持布局的必要 Editor 构建记录为本机 `Saved/BuildEditor/build-20260915-090729.log`。本次整理没有重新构建候选提交，也没有启动游戏、运行回归或生成验收截图；该历史构建不证明本批精确提交树或实际画面已通过。交由用户自行测试。
