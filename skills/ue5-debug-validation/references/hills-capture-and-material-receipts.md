# 丘陵截图宿主与材质落盘

仅在用户要求相应截图、材质诊断或测试时使用。

- 隔离宿主除 Content/Plugins 外还须提供生产 Shaders；冻结 DLL 的 `.modules` 从同目录复制，不能拼接共享 Binaries 中后来变化的清单。记录机位、模块散列、准备计数、退出码与正式存档前后散列。
- PowerShell `Start-Process -PassThru` 后及时取 `.Handle`，再等待退出并取 `.ExitCode`，避免快速退出导致 null。构建成功、资产保存、实际加载与画面认可分别记录。
- 属性包装辅助函数返回 `INDEX_NONE` 时不能直接作 Python 下标：`-1` 会误连最后一项，可能把 ShadingModel 接到透明裁剪链。修正辅助函数后仍须重建保存受影响材质与实例；C++ 修复不会自动更新已有 uasset。按引用链缩小重建范围，不为一个材质重导所有网格。
- 测试宿主的目录联接可能指向生产 Content/Plugins/Shaders。归档只枚举自身普通文件，记录联接及目标，将联接改存描述文件后归档宿主，不遍历、移动或删除目标。保留小型结果回执，截图与过期模块按授权进入 trash。

入口：`Start-HillsLandscapeCapture.ps1`、`repair_hills_beech_material.py`。历史批次归档后按发布清单定位，不恢复失败模块作为默认输入。
