# PSO-1 / AKM、A762、PKM 作者源

后续镜筒接缝透空修复见 [PSOSeamRepair20260923](../PSOSeamRepair20260923/README.md)。本目录三份可编辑 Blend 已同步修正；最终 FBX 和补全涂层图集改用该目录，避免旧导出重新覆盖机械环的不透明分区。

当前运行表面进一步升级为 [PSOMatteFinish20260923](../PSOMatteFinish20260923/README.md) 的枪型专用哑光干湿材质。当前材质绑定以该轮保存回执为准。

本目录用于 `pso1_4x` 三款私有适配。完整接入说明见 [开发记录](../../Docs/Weapons/pso1-russian-attachments-20260923.md)。

## 制作输入与空间约定

`sources.json` 记录从正式 UE 网格读取的源文件及材质引用；`geometry_frames.json` 记录源骨架空间转换。三套参考来自 AKM RearGrip20260913、A762 Accessories05、PKM Lowpoly HandleFinish27，不能用历史 M4 的统一偏移替代。

源 PSO 取自当前 SVD 可编辑完整装配，已含前轮 UV 修复。`prepare_geometry.py` 将 PSO 和各机匣转换到 `WPN_root` 静止局部空间，Blender 以米为单位、-Y 为前、+X 为左。`author.py` 按实际机匣表面射线求交制作侧座；仅采用固定在枪根的面，不把活动盖板当连接面。

导出时转为 +X 光学前向，UE 运行时采用 `PSO1AttachmentAssets::Mount()` 的 +90° yaw 和 0.01 比例回到共享枪根空间。`AimCenter`／`AimFront` 从原 SVD 瞄准标记同样转换，写入最终静态网格 Socket。不得只旋转网格而遗漏 Socket。

`PSO1_<枪型>_Editable.blend` 保留镜体、光学玻璃、新侧座、隐藏机匣参考及涂层作者材质；FBX 导出新增侧座时先三角化。原结构法线复用 UE `T_SVD_pso_normal`，新增侧座依靠实体倒角与加权法线。内壁保护与非金属区域防止枪身涂层覆盖橡胶、玻璃和镜内结构。

## 脚本顺序

1. 在现有 UE 批次互斥下，通过 `background.ps1` 执行 `read_sources.py`，读取当前输入；不用打开交互式编辑器。
2. 使用本机 Blender 后台执行 `prepare_geometry.py`、`measure_interfaces.py`、`author.py`。后两步分别生成制作所需接口数据和三套几何／4K 涂层烘焙。
3. Blender 后台执行 `export_and_icons.py`，导出最终 FBX，并制作透明 UI 图标和独立图标 Blend。
4. `update_catalog.py` 只追加三款指定枪械的瞄具选项。代码接入在 `Source/FPSGAME/Weapons/PSO1AttachmentAssets.h` 及共享枪匠／ADS／天气调用处。
5. `build_native.ps1` 后台构建；`background.ps1 -Script import_assets.py` 执行 UE 导入并保存。脚本会等待现有批次互斥，遇到正在运行的项目编辑器则保留现场。

`import_assets.py` 支持中断续作：已记录完成的材料阶段会复用资产。再次更改贴图／材质后，不应直接把一次恢复执行当成重新导入；须使用新的版本目录，或明确重置本目录 `import_receipt.json` 的对应制作阶段后导入。不得清理其它任务的记录或资产。

## 输出记录

- `authoring.json`：三套安装偏移、接口、光学 Socket 与导出数据。
- `icons.json`：三个实际模型选项图标生产记录。
- `import_receipt.json`：已保存包、最终槽位、Socket、纹理、UI 图标及六组干湿映射。
- `import_assets.log`：最终后台导入完成日志。首次 Socket 属性写法失败的日志单独保留为 `import_assets_first.log`，已改用 `set_editor_property` 后续作完成。
- `build_native.log`：最终编译和链接成功；`build_native_first.log` 保留已修复的局部变量遮蔽编译错误。

这批作者源与正式 UE 包均已落盘。未进行游戏测试、保存／加载测试、动态换弹间隙验收或游戏画面渲染。图标渲染和材质烘焙属于资产生产。

原 PSO 镜体是 LeroyCake 的 SVD 作品派生，继续保留 CC BY 4.0 署名。三套侧座、新涂层和图标是本轮改动；来源记录见 [第三方声明](../../ThirdPartyNotices/SVD_DRAGUNOV.md)。
