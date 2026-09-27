# 长杖乳白水晶材质 V20

## 来源说明

当前长杖使用混合制作：木杆来自 Meshy 7.1 任务 `01a0e301-9f4d-73fc-b3b6-d6b79d0dd044` 的轮廓底稿，V19 在本地重建封闭木杆并适配原握持接口；水晶与上部麻绳由 Blender 制作，木纹使用工程现有 UnrealNormandy PBR。不是未经加工的 Meshy 原成品。本次不重新调用 Meshy。

## 本次调整

用户反馈顶部水晶太透明，仅改变默认白水晶材质：

- 透射色由接近纯白的 `(0.95,0.98,0.97)` 调为 `(0.78,0.84,0.82)`。
- 乳白表面覆盖从 0 改为由云雾纹理控制的 0.24–0.42，粗糙度从 0.075 改为 0.16–0.24。它们是材质参数，并非画面最终透明百分比。
- 两层快速三维梯度噪声固定在物体局部坐标，模拟柔和的内含物浑浊感；不使用世界空间移动纹理、时间动画或发光。
- 保留晶体切面、尺寸、UV、封闭网格、顶部麻绳和全部握持／施法接口；没有新增内部面片。

新材质为 `/Game/Weapons/ApprenticeStaff20260927/QuartzMilkV20/Materials/M_Staff_QuartzMilkV20`，绑定活动及 V19 版本目录中 `SM_Staff_Base` 与 `SM_Staff_head_crystal_false` 的水晶槽。旧透明材质保留，原槽引用见 `previous_bindings.json`。

`quartz_parameters.json`、`ue_quartz_material.py` 和 `blender_quartz_material.py` 是参数与制作源。V19 作者／导入入口已改用此配方，并更新可编辑 Blend、两份默认模型 FBX 及背包图标。源文件备份在 `Before/`。

是否完成引擎保存以 `install-receipt.json` 的 complete/saved 为准。没有启动 UE、PIE、诊断截图或验收渲染；只生成配套背包图标。材质编译和资产保存属于必要接入，游戏中的最终表现由用户测试。

本轮已通过后台 commandlet 完成新材质及 4 个引用网格的保存，回执 complete=true；同步发布更新后的背包图标。未运行游戏或做材质效果验收。
