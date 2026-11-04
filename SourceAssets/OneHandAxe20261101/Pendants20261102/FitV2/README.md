# 穿孔修正 V2

初版仅对齐弯刀与战斧孔心，原宽绳并不适合战斧的窄孔，三款挂饰与四款柄尾均存在实体相交。本批次只修正连接端，保留通用挂饰的下部造型、UV、PBR、数值、ID 和图标。

- `author_fit.py`：保留局部 Z ≤ -1.8 cm 的通用主体，新增直径 1.5 mm 的固定穿孔绳和下部接合，主体挂点下移 5 mm。
- `prepare_staging.py` / `import_fitted.py`：隔离无界面工程导入三款修正网格及一份深色绳材质，保留 UV2 精度与原动态材质，并导出保存后的 UE 网格用于检查。
- `SavedMeshCheck/geometry_report.json`：12 组组合均无相交面或显著内部顶点，并有绳体通过孔洞中面；检查范围为静态安装几何。
- `publish_fit.py` / `registration_receipt.json`：发布四个全新资产，合并本战斧三条挂坠配方与柄尾碰撞包络。没有覆盖原有公共挂饰资产。
- `ModularSwordVisual.cpp`：第三人称为战斧网格读取战斧挂坠动态配方。

诊断图中的橙色只用于标示绳路。未运行游戏或验证动作摆动。

`FPSGAMEEditor Win64 Development` 后台构建已成功，见 `build-editor-retry.log`、`build_receipt.json`；保存、发布、12 组静态检查与构建汇总见 `delivery.json`。首轮遇到并行更新中的符文剑声明不一致，待当前头文件完整后以增量构建完成，没有修改那部分代码。
