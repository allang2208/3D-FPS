# QR 高性能后托

用户于 2026-09-12 提供的 QR 高性能后托图片为本轮造型参考。三视图由 imagegen 根据该图重新制作，随后送入 RTX 5080 的 TRELLIS.2 管线。该配件独立使用 `stock: qr_performance`；此前的 `skeleton` 选项保留。

## 制作入口

- `user_reference.png`：用户提供的原图，仅作造型参考，原图的再分发授权未确认。
- `model_views.png`：本轮生成的三视图。
- `pipeline.py`：三视图分离、去背景及 5080 生成；`submit` 提交，`collect` 取回实际生成结果。
- `generation_workflow.json`、`qr_performance_stock_submitted.json`：实际节点图及请求记录。TRELLIS.2-4B、1024 cascade、种子 91283；高模附带 4K 纹理。
- `build_game.py`：从生成模型制作游戏网格，烘焙 4K 法线，分离金属、聚合物与橡胶材质区域，制作 M4 / AKM 安装版本并导出 FBX。
- `QRPerformanceStock_Generated.blend`：归一化后的生成源；`M4/QRPerformanceStock_Editable.blend`、`AKM/QRPerformanceStock_Editable.blend`：可编辑游戏源。
- `import_game.py`：导入 UE 网格与贴图，绑定真实枪身材质。

## 接入

作者模型长度为 18 cm，原点位于前部连接口中心，+X 指向肩垫。M4 与 AKM 沿用各自已建立的枪根坐标：M4 `(0, -0.0385, 0.0725)` m，AKM `(0.0008, -0.083, 0.035)` m。AKM 另带独立金属接收器盖板，不照搬 M4 安装接口。

- M4：`/Game/Weapons/QRPerformanceStock/M4/SM_QRPerformanceStock`，金属直接使用 `/Game/Weapons/M4InfimaV3/Body_001`。
- AKM：`/Game/Weapons/QRPerformanceStock/AKM/SM_QRPerformanceStock`，金属直接使用 `/Game/Weapons/AKMIntegration/SovietFab/M_AKM_Soviet_PBR`。
- 上部贴腮面使用生成颜色与烘焙法线；后肩垫使用高粗糙度橡胶。两者与金属槽分开。
- UV0：金属区域采样对应枪身贴图的金属区域；非金属区域保留生成 UV，保持切线法线方向。UV1：生成纹理原始展开。
- 枪匠、角色、预览、图标与掉落使用现有 `SetGunsmithStock` 装配入口。入口支持已存在组件在 `skeleton` 和 `qr_performance` 之间更换网格。
- 在 M4 / AKM 枪匠目录追加独立条目；打包目录加入 `DefaultGame.ini`。

参考图未提供数值属性，且旧项目未找到对应 QR 条目，因此本轮 `effects: []`、`stats: {}`，沿用原厂属性，不虚构“高性能”的数值加成。

## 交付状态

本轮 5080 实际任务 `c6dd995f-6734-42a7-9012-3390a1622d02` 完成，生成用时 585.91 秒。导出 M4 48,000 三角面、AKM 64,850 三角面（含接口与金属 UV 分块几何），作者高度约 13.31 cm。原生构建退出码 0。

UE 导入日志记录两种 `SM_QRPerformanceStock` 均已保存，脚本完成。整个 commandlet 退出码为 1，原因是工程现有 `GameFeatureData` 资产管理规则缺失；不能将本次导入描述为整个进程零错误完成。日志保留在 `import_assets.log`，未为该已有配置错误修改并行功能。

仅进行必要的制作、导出、导入与原生构建。按用户全局规则，本轮不执行检查、验证渲染、自动化测试、PIE 或游戏回归；游戏效果与装配由用户自行测试。未宣称通过运行验收。

原图、源模型及打包了枪身贴图的 Blend 文件保留本机，不公开提交。脚本记录来源与复现过程，不代表已取得原始参考图片的再分发许可。

源码发布保留本轮制作脚本、参数及 `qr_integration.patch`。共享的枪械源码和目录还包含其他任务未提交的开发，QR 的实际运行修改已落在本机原文件中；补丁仅记录本轮相对已有骨架枪托分支的改动，避免发布时夹带并行功能。补丁依赖本项目已有的枪托装配分支，不是空白项目的独立插件。
