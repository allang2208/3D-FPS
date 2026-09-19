# 用户新参考 / RTX 5080 枪托重制

**当前交付为 [DetailRefine/README.md](DetailRefine/README.md) 中的细节精修版。** 用户接受 5080 结果整体方向后，要求修开粘连细节并按枪型匹配枪身金属。下文的 50,000 面减面版和早期验收均为历史阶段；最终统计、近景及游戏截图见精修目录。

2026-09-12 用户明确否定上一版模型过于粗糙，提供 `user_reference.png` 并指定重新制作三视图、使用 5080 管线。新参考覆盖上一版三角架视觉依据。此前 `SourceAssets/SkeletonStock20260912` 的功能回归结果不能用作本版视觉验收。

本目录独立保留新参考、三视图、实际多视角输入、RTX 5080 服务信息、完整工作流、队列回执、原始几何、纹理母版与实际模型渲染。生成来源必须是本次实查在线的 RTX 5080 / TRELLIS.2；用户已指定管线，不切换到混元，也不以程序拼件代替生成结果。

实际生成成功：TRELLIS.2-4B / 1024_cascade，结构 16、形状 32、纹理 24 步，4K 纹理。任务 `ed2e8baf-ed8d-4190-8ddc-6e8efa03c921`，用时 257.52 秒，历史状态 success。原始几何 3,253,936 三角面；纹理母版实际 186,763 面（请求目标 200,000）；4K 颜色及打包 Metallic/Roughness 两张生成图，不能把它们称作四张独立生成 PBR 图。

## 可查看结果

- `model_views.png`：实际送入 5080 的三独立视角（左侧、肩垫端面、右侧）；图来自内置图像生成。按 `view_crops.json` 分割、去背景后送入三个具备空间方向的条件输入，未将整张拼图当一张物体，也未把顶视图当侧视图。
- `orthographic_reference_draft.png`：早期侧/顶/端面草稿，端面遮挡关系不一致，未用于生成；保留为过程证据，不作最终三视图。
- `reference_stock_high_raw_geometry_00001_.glb`：完整 5080 原始高模；`reference_stock_high_textured_master_00001_.glb`：4K 纹理母版。
- `ReferenceStock5080_Generated_Editable.blend` 与 `generated_beauty.png` / `generated_front.png` / `generated_back.png`：保留生成几何与材质的真实模型预览。`generated_top.png` 是最初取景记录，端部有裁切，不作完整正交验收。
- `ReferenceStock5080_Game_Editable.blend`、`ReferenceStock5080_Game.glb`、`SM_SkeletonStock.fbx`：基于生成纹理母版减面的 50,000 面游戏版。保留原 4K 颜色及 Metallic/Roughness，额外从母版烘焙 4K 切线法线。
- `AKM/ReferenceStock5080_AKM_Editable.blend`：同一生成枪托加机匣尾盖，51,216 面、2 材质。尾盖是单独制作的逐枪转接部件，枪托本体没有用程序拼件重做。

## 衔接与功能

沿用此前已核对的原厂可逆 section 替换算法，以及每枪独立枪根坐标。M4 局部安装 `(0,-.0385,.0725)`，AKM `(.0008,-.083,.035)`，根继承缩放只抵消一次。模型作者以安装口中心为原点，+X 指向肩垫；作者和 UE 读回长约 23.04 cm、宽 2.88 cm、高 11.19 cm。

正式运行引用为 `/Game/Weapons/ReferenceStock5080/SM_SkeletonStock`，AKM 为同目录 `AKM/SM_SkeletonStock`。M4/AKM 枪匠使用“骨架枪托”名称、同一 `skeleton` 实例 ID，保持原存档与数值合同。此前原厂切分的 AKM `StockV2` 骨架网格继续使用；新转接没有修改手模、骨架或动画。`m4_interface.png` 和 `akm_interface.png` 为实际接口渲染。

新模块编译后，`run_validation.ps1 -RunId stock5080-v1` 使用隔离存档验证 M4/AKM 写入和独立进程重载、草稿与取消、保存失败、移除/重装、未装备实例、图标、掉落、换枪、ADS/射击及四种换弹。最终结果见 `acceptance.json`，不将旧版测试当新版测试。没有修改用户常用存档。

## 质量和验证边界

生成母版保留双管、矩形通孔、接环、紧固件和肩垫，仍能看到少量边缘起伏。游戏版源检查记录 107 条边界边、429 条非流形边、0 个零面积面；这些残留来自生成表面，不声明拓扑完全清理或全枪零穿模。近零切线/副法线警告也保留在导入日志，需结合实际渲染判断。4K 法线烘焙约 0.23% 无效或反向像素回退为几何法线，完整数值见 `game_mesh_report.json`。

两个 UE 导入回读 PASS，但 commandlet 各退出 **1**，日志保留了项目既有 GameFeatureData AssetManager 错误；这不等于导入 Python 失败。编译与新游戏进程结果分别记录。未执行完整打包，静音动作预览不证明音效验收。

`pipeline.py`、`fetch_models.py`、`render_generated.py`、`build_game.py`、`fit_akm_adapter.py`、`import_game.py`、`import_akm_adapter.py`、`render_fit.py`、`run_validation.ps1` 为复现入口；游戏转接仍依赖上一轮保留的枪根测量场景。所有远程 GLB/PNG 下载后与 5080 上 SHA-256 核对，见 `remote_outputs.json`。图像来源是用户新参考及本次生成；现有 M4/AKM 原始素材继续遵循项目原许可，不增加其公开再分发授权。
