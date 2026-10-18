# SUPER90 改造图标逐项排查

用户要求范围：当前 SUPER90 所有可见改造分类和选项。完整 44 项清单见 `Docs/UI/super90-icons-review-20261016.md` 和本目录 `review.json`。

- `baseline.json`：修改前选项合并快照、实际解析路径、尺寸与散列；一次性基线，不覆盖重跑。
- `audit_before_1.png` 至 `audit_before_4.png`：旧图及 48/64 像素查看布局。第 39 项缺少图文件，真实 UI 回退到 `category_underbarrel`，详见 `review.json`。
- `source_islands.json`、`NativeSource.blend`：现有 SUPER90 原生导出及组件定位；不修改运行网格。
- `render_sources.py`、`FactoryIconSources.blend`、`References`、`source_manifest.json`：六件真实原厂部件、材质来源、方向和相机。
- `generation_manifest.json`：内置 imagegen 的完整逐图提示词、参考和结果路径，包含枪托孔数修正记录。
- `Generated`：六张最终母图与三张复用母图；运行源在 `Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms`。
- `deployment.json`：九个准确加载键、旧包散列与备份位置。十个被替换文件保存在 `trash/super90-icons-replaced-20261016`。
- `import_receipt.json`：九个 Texture2D 全部保存，`completed: true`。成功后台日志为 `icon-import-02`，退出码 0；首轮在部署失败后因缺少清单停止，没有导入资产。
- `audit_changed_final.png`：九项最终图片及 48/64 像素缩略图。

原枪托、后握把作者目录的 PNG 和恢复入口已同步。共享战术垂直握把使用实际相同供体，弹仓分类采用已有无状态标记代表图。未改变原生代码、三维模型、动画、属性或存档；无原生构建需求。此次完成静态图标排查和资产落盘，没有打开 UE 编辑器界面、运行游戏或 PIE；游戏内效果由用户测试。
