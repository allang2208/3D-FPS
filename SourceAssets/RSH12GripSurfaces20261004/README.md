# RSH 三款通用握把防滑纹

制作参考 Viper 的纵向握把覆片经验，配方和选项复用现有 `PistolGripSurface`，RSH 单独制作接触网格。外部网格已制作导出，UE 网格已保存，枪匠目录已发布；包含本次两处运行源码改动的基础 DLL 已构建成功并落盘。制作、导入、目录和构建分别记录在本目录回执中。

- 只提取源模型 `9_l` 的左右外侧握把本体，沿真实面域周界及孔洞内缩 0.8 mm。上颈、指槽、背脊、底面及周边机构不在覆盖域内。
- 双侧连续薄层保留原握把，采用封闭背面和向外面序。表面从边缘 0.09 mm 逐渐过渡至 0.24 mm；这些是游戏模型制作值。
- UV0 从最终裁切点生成，按原握把倾斜方向建立正交坐标，每 0.1 m 一个共享纹理平铺周期。没有把短图集拉长，也没有借用 Viper 的具体轮廓、安装偏移或专属鳞纹。
- 一份网格、三个既有材质：细颗粒防滑纹、橡胶菱形防滑纹、细点快握防滑纹。共享图标、改造数值和湿润映射继续使用现有资源。
- 按当前 `RSH12Speedloader20261003/Single` 的原生根骨与枪体注册导出组件参考帧；运行时使用同一 `WPN_root` 参考链。当前已认可的手型、动作、骨架及枪体网格不变。
- RSH 使用 715 动作家族，但后握把装配跳过 715 替换件分支，进入通用表面覆层。副手也保持原握把可见；恢复原厂时沿通用通路销毁覆片。

## 制作文件

1. `prepare_panels.py`：从原握把外侧面提取真实面域和内缩边界；使用本目录 `.deps` 中的 Shapely 2.1.2（制作依赖，不进入游戏）。
2. `panel_inputs.json`：选面编号、原周界、裁切周界、物理 UV 方向与三角剖分。
3. `author_grip.py`：原生组件坐标的薄层制作和 FBX 导出，不渲染。
4. `Exports/SM_RSH12_GripSurface_Editable.blend`：可编辑母版，带隐藏参考枪。
5. `Exports/SM_RSH12_GripSurface.fbx`：13,064 三角面、单材质槽。
6. `import_assets.py`：实际保存 `/Game/Weapons/RSH12/GripSurfaces20261004/SM_RSH12_GripSurface`。
7. `publish_catalog.py`：资产保存后，仅为 RSH 发布 `pistol_grip_surface` 绑定并复用公共选项；原始枪械目录生产入口也保留此绑定。

源表面沿用 [Medji RSH-12 的 CC BY 4.0 记录](../../Docs/ThirdParty/RSH12-Medji-CCBY4.md)。未制作新共享材质或图标，未发布源资产。未运行游戏、预览渲染、截图或测试，观感交由用户测试。

本任务后台 `FPSGAMEEditor` 构建已成功，198 项编译及链接动作完成，用时 244.30 秒；其中包含 `PhantomRearGripVisual.cpp` 与 `PistolDualWieldComponent.cpp`。`build_receipt.json` 记录结果日志和 DLL 保存时间。没有自动打开或重启 UE。
