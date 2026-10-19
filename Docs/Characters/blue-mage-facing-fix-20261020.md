# 法袍胸前兜帽方向修复

用户截图中的蓝色胸前突起来自 `RobeHood` 及其配对内衬。Body、Jason 的原生脚尖朝 +Y，旧 `append_trim()` 将 +Y 当作背部，把垂落兜帽生成到了胸前；饰条、领扣和腰带扣则在 -Y 一侧。

本次从脚骨到脚掌骨的原生方向确定前后，重新在目标侧的躯干外表面求交并插值该处骨权重。兜帽及内衬移到后背，翻转后的面序按新朝向构建；饰条、领扣、宝石和腰带扣移回正面。Body、Body_Owner、Jason、Jason_Owner 四个源网格仅替换独立辅件岛，保留胸腹、领口、袖子、裙摆及布料代理原有的顶点属性与三角形。原生修复不使用整体旋转、隐藏胸前材质或骨骼缩放。

制作入口为 `Tools/BlueMageRobe/repair_facing.py`，沿用修正后的 `author_body.py`。可编辑 Blender 与 FBX 导出由 `export_facing.py` 完成；`save_facing.py` 保存四个穿戴资产及三维展示/掉落模型；`publish_facing.py` 仅更新法袍的两个世界身体、两个本机躯干引用。枪、弓、法杖、双手锤等继续走现有共用身体路径。角色网络装备字段、玩法及武器袖子不变。

生产记录与恢复输入位于 `SourceAssets/BlueMageRobe20261018/FacingFix20261020/`。`Before/` 保留本次修改前的四个作者网格和三维图标源；新资产使用独立版本目录。`HemContinuity20261019` 的 32 条内搭引用与当前布料参数继续沿用。

本次更新了背包三维展示源与后续图标生成的正面方向，沿用现有 PNG 贴图，未执行预览渲染。是否已接入以 `saved_assets.json`、`published.json` 的完成记录为准。未运行游戏、动作回归或联机测试，实际画面由用户试玩确认。

2026-10-20 已落盘：`facing-author-02.log` 完成四个作者版本；`facing-export-01.log` 完成对应 Blender 与 FBX；`facing-save-01.log` 后台资产命令退出码为 0，四个穿戴网格及展示、掉落模型已保存。发布输出为 `ROBE_FACING_PUBLISHED 4`，当前目录的世界身体与本机躯干均引用 `FacingFix20261020`。本次未修改 C++，无需额外程序构建。
