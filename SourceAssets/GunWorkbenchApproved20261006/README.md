# 枪械工作台批准设计导入记录 · 2026-10-06

用户批准的云端 V2 布局已导入原生枪械工作台 `gun_workbench_table`，正式网格继续使用 `/Game/Building/GunWorkbenchLibraryTools20260928/SM_GunWorkbench`。本轮没有修改斧镐工作台、C++、配方、玩家存档或地图。

## 来源与资产

- `ApprovedDesign/`：六个批准 ZIP 合并后的原始相对链接设计，包含 Textures；源文件原样保留。
- `Authored/GunWorkbench_GameReady.blend`：转换后游戏母版；图片已内嵌，重新打开确认无外部库或未打包贴图。
- `Authored/SM_GunWorkbench.fbx`：正式导入源，Z 向上、米制；字体和曲线均转换为网格。
- 新 UE 材质与贴图：`/Game/Building/GunWorkbenchApproved20261006`。新增机器、组件和支撑垫共用 2048×2048 BaseColor、Normal、ORM、Emissive 图集；透明玻璃独立材质；桌体、台灯与工具保留原项目材质。
- 桌面仅使用批准的 9mm、5.56、7.62 三盒弹药，无弹药系统变更。

## 已保存的兼容处理

- 保留原网格路径、构件 ID、13×13×8 占格和复杂网格作为简单碰撞的模式，简单碰撞数量仍为零。
- 保留木材材质槽 0，因为运行时代码 `AVoxelBuildPrefabActor::Configure()` 会以 Palette Surface 覆盖该槽。
- UE 重导入保留了旧弹药材质槽别名，最终显式将这四个别名绑定至批准的新纸盒／金属材质。网格保留 32 个材质槽记录；最终绑定清单见 `Validation/ue_import_receipt.json`。
- 单一网格同时含不透明与透明部分，使用常规静态网格路线，Nanite 关闭。已通过 StaticMeshEditorSubsystem 重新构建完整 LOD0，避免继续使用旧 Nanite 回退几何。未全局改变渲染设置。
- 源高由 159.027636 cm 增至 172.200912 cm。Palette 中仅该条目的 `PivotOffsetCm.Z` 从 0 调到 **6.586639404296875 cm**。按实际 `Rotation(BoundsOrigin)` 公式核对四个朝向，原组件变换最大差异为 0.00000763 cm。旧桌面、装配锚点和桌脚高度保持不变；格坐标为零时原有桌脚标高约 0.486183 cm，未另行改变原地面约定。

## 实际完成的检查

- 源文件校验、背景 Blender 加载、转换和 FBX 回读：338 个设计网格／曲线／文字对象，8 个曲线或文字对象已转换，128,478 个制作顶点，242,532 个源三角形。
- UE 磁盘保存后在新的恢复编辑器会话独立读回：**241,967 个源模型／渲染三角形**。565 个差异面已逐个定位为 561 个零面积面及旧台灯上 4 个极小面积面；后四者总面积约 1.483e-10 m²。不是整体减面或遗失机器部件。
- 转换后顶点距离批准源几何的最大误差约 2.53e-7 m。实际 UE 导出网格与源三角面中心最大误差约 4.46e-7 m；弹药 UV 最大差异约 4.66e-8。
- 分组表面相交检查未发现组间穿插；新增道具未进入现有装配拖动范围。机器内部安装连接、同组部件的有意接触不作为组间穿插。
- 机器、托盘和弹药垫距原台面约 0.25 mm；工具距整理垫约 0.50 mm。静态截图检查了桌面承托、中央留白、玻璃透视、铭牌、金属和纸盒标签。
- 四张截图为真实 UE 静态编辑器渲染，临时棚拍灯光。截图不是游戏内 PIE 画面。
- 默认配置、地图与存档共 1,766 个既有文件的前后 SHA-256 均一致。具体清单见 `Validation/protected_audit.json`。

## 未验证与保留事项

没有运行 PIE、E 交互、玩家移动、机器动画、Cook 或性能测试。当前保留高精度近景 LOD0，没有依据未知目标平台主动减面；常规网格和复杂碰撞的游戏性能仍待后续按需求实测。静态四方向公式验证不等同于实际存档放置交互验收。

首个专用编辑器 PID 65224 在工作中退出，未发现对应新崩溃记录，原因未确认。恢复会话 PID 61060 从已保存资产继续，仅补完材质绑定和截图，没有再次整套导入。首个会话日志另有枪托与螳螂动画的并行任务写入；这些资产未被本任务撤销或计入本轮修改。

2026-10-06 08:17:24 UTC，恢复会话在已完成保存、读回和四张截图后，清理未保存的临时预览地图时发生致命 GC 错误：Python 引用阻止 `/Engine/Maps/Entry` 包释放。日志随后记录异常退出，进程已结束；不能将此表述为正常关闭。错误发生在 `EditorLoadingAndSavingUtils.NewBlankMap`，没有保存临时地图。最终审计引用此前成功的真实 UE 读回回执，并在退出后再次核对磁盘文件；未为重做收尾而重新启动编辑器。详见 `Validation/final_ue_readback.json`。

## 备份与复现

原网格、Palette 和旧作者源的备份及 SHA-256 清单位于 `C:/Users/allan/Documents/Codex/2026-10-04/task-2/gunbench_import_20261006/backup_before/` 与同级 `backup_receipt.json`。完整操作回执、日志在同级审计工作目录。

`Scripts/convert_design.py`、`finalize_mesh.py` 支持本目录布局：从 ApprovedDesign 生成 Authored；UE 导入脚本保留本轮快照校验，供复核流程使用，后续重新执行需重新建立对应基线，不应跳过并发保护。旧 `GunWorkbenchAmmo20260928` 源仍为历史恢复依据，不应再用旧导入器覆盖本批准版本。

Library 截图身份见 `Validation/library_delivery.json`。没有 Git 提交或推送。
