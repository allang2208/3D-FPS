# 715 原形体线条与表面细节修订

用户认为整体形态可用，要求参考 QBZ191，让检视时的线条及零件细节更清楚。本版从回退后的 Mirror 开始，只制作新的表面与材质绑定。

参考 `Docs/Weapons/qbz191-hero-surfaces-20260913.md`：保留源结构法线，独立制作反射表面，再向实际低模的 UV 和切线基础烘焙。715 保留自身抛光不锈钢颜色，不套用 QBZ191 的深色涂层。

- 保留现有网格、轮廓、UV0、运行分裂法线、蒙皮、机械骨架和所有动作；UE 复制 Mirror 网格后仅替换三个金属材质槽。
- 源件高模恢复原参考的角点法线，取消 Mirror 的高通过滤与 0.45 全局细节衰减；原刻字、浅槽及加工过渡直接参与重新烘焙。源结构与新微表面独立，本轮不添加颗粒凹凸。
- 保留已有倒角几何；枪架、护罩、弹仓、击锤、扳机和锁扣分别控制抛光程度。窄边缘用局部抛光与凹处反差显示，避免整枪统一反射。
- 各对高低模同时移开后烘焙，避免邻近机械件互相投射。保留旧 UV，生成 Frame/Cylinder/Steel 三组 4K BaseColor、ORM、Normal。
- 原镜面配件、手臂、握把、弹药、音效和换弹入口保持当前引用；新金属表面带对应雨滴湿润材质。

制作脚本与可编辑源保存在本目录。已完成必要导入、构建与接入，依用户规则未启动游戏、预览、截图或测试。

## 制作文件与接入

- `surface_material.py`：完整结构法线、线条反差遮罩、各部位抛光参数。主枪架/护罩/弹仓外壁粗糙度中心为 0.045/0.060/0.035；击锤 0.105、扳机 0.075、锁扣 0.085–0.090，弹仓端面在外壁基础上增加 0.048。参数是本版制作选择，不是实机验收结论。
- `bake_detail.py`：读取 Mirror 完整装配，恢复源件高模角点法线，成对隔离烘焙；运行低模保持原数据。
- `DanWesson715_Detail_Editable.blend`：完整可编辑装配、作者高模与新表面，保留原动作、配件与手臂。
- `Textures` / `textures.json` / `production.json`：9 张新图、材质槽与作者处理记录。烘焙使用现有 HeroUV，游戏仍按 UV0 采样。
- `import_detail.py` / `import.json`：复制 Mirror 骨骼网格，仅替换三个金属槽，不导入 FBX 或动画。新建三组干湿材质和 `DA_DW715_WetMaterials`，由天气初始化合并到当前配置的运行时映射。
- 运行主体 `/Game/Weapons/DanWesson715/Detail20260914/SK_DW715_Manny`；配件沿用 `/Game/Weapons/DanWesson715/Mirror20260914/Attachments`。现有 `/Game/Weapons/DanWesson715` Cook 条目覆盖本版资源。

烘焙退出 0，已保存完整源文件。导入脚本完成并保存资产，标记 `DW715_DETAIL_IMPORT_COMPLETE`；commandlet 因工程已有 GameFeatureData 配置错误退出 1。生产日志分别为 `bake.log`、`import.log`。未运行游戏或视觉测试。

原生 Editor 构建成功：`build.log` 记录 `Result: Succeeded`，模块后缀为 `71416`。重启编辑器加载新模块与表面材质。

原模型、原贴图及 Manny/P9 来源许可沿用此前记录；没有新增外部下载。Mirror 和已撤回的 Precision 文件保持原样，后者不参与本版运行。
