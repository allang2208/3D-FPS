# RSH-12 原生 715 动作恢复

当前后续制作入口为 `../RSH12ContactRepair20261003/author_contact.py`，修复本版的估算吊臂轴心及持弹失配。不要直接重跑本目录旧作者脚本覆盖最新资产；保存记录以新目录的 `native-715-contact-v2` 回执为准。

用户否定上一版自制握持和动作，当前保留原生 715 的全部手、腕、臂轨迹。仅对 RSH 枪体配准、机械枢轴、五发膛孔及子弹入座制作私有差量。视频只参考镜头抖动。

生产顺序：`prepare_grip.py -- single` → `fit_grip.py` → Blender 后台运行 `author_native.py -- single`、`-- r`、`-- l` → `import_assets.py` → `publish_catalog.py` → 必要编译。导入走项目互斥 commandlet 或已运行编辑器的桥；不启动编辑器或游戏。

运行资产 `/Game/Weapons/RSH12/Native71520261003`；动画直接共享 715。`import_receipt.json` 是实际保存记录，`build_receipt.json` 单独记录编译结果。旧版源位于 `BeforeSource`，仅用于恢复本任务改动，不能整份覆盖并行编辑。

当前原生 715 手型仍需用户体验。制作没有自动测试、试听、预览或验收，不能宣称握持已获认可。
