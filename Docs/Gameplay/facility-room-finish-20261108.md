# 工业与医疗房间写实饰面第一批

制作批次从 2026-11-08 延续到 2026-11-09。后台 Blender 建模、UE commandlet 导入和正式地图保存；未启动交互编辑器、游戏、截图、渲染或性能测试。视觉与玩法体验由用户测试。

## 已接入范围

正式地图 `/Game/GameMaps/L_Dungeon_Randomized`，五个现有房间：

- `AbandonedCargoWarehouse`：独立粗混凝土扫描地面，300 cm 尺度，降低重复表面的统一感；检修盒、维修零件托盘和接触磨损。
- `SwitchgearGallery`：灰绿涂层地坪，低强度微表面起伏；检修盒与拆下的密封圈、紧固件组合。
- `GeneratorHall`：暖灰机电地坪；检修盒和连接到墙体的旁通阀组，包含真实法兰、抱箍、手轮、表盘及局部渗水痕迹。
- `AbandonedIsolationWard`：带对应法线的油毡地面、分上下色带的旧涂层墙面、弧形墙脚收边、墙面服务接口；一组拆卸面板与零件托盘放在已有桌面。
- `MedicalDoctorOffice`：偏暖的油毡地面、白色／蓝灰色墙面饰层、弧形墙脚收边及墙面服务接口。原桌面已摆放较满，本批未追加桌面托盘。

本批保存 8 个材质槽覆盖、18 个静态组合件实例、15 处局部贴花。7 个新网格包括检修盒、旁通阀组、医疗接口、工业维修托盘、医疗面板维修托盘，以及两份按房间墙段合并的墙脚收边。598 段收边合并为两个网格，不创建数百个独立 Actor。

地图原有 120 条布局记录继续保留，仅更新与材质及装饰目录相应的合同散列。房间外轮廓、原有碰撞、门洞、交互容器、遭遇配置、灯具、Lumen／光追、主入口及接待区不在本批修改范围内。

## 材质与模型来源

独立资产前缀：`/Game/Dungeons/FacilityRoomFinish20261108`。没有全局改写共享原材质。

- 工业混凝土：初版使用 `T_ConcreteRough_01_BC/N`；2026-11-09 实际样图检查后改为 HospitalCorridor 的 `T_ConcreteFloor_01_BC/N`，降低颜色反差与法线强度，减弱裸岩感。
- 医疗地面：初版 `T_linoleum_01_A/N` 经实际渲染发现带明显木纹，现已替换为低对比灰绿／暖灰表面、细颗粒法线和轻微粗糙度变化。保留实际网格分块和缝隙；不根据颜色伪造位移。追加检查与修复详见 [完整批次记录](facility-realism-completion-20261109.md)。
- 医疗墙面：已安装 `T_Stucco_01_A` 与 `T_WallPainted_01_N`，轻微表面变化和墙脚积灰。
- 涂层、金属、橡胶、陶瓷：沿用上一批 `M_MicroFinish`，新增本批独立材质实例。
- 低浓度接触磨损来自已有粗糙度／污渍资源；阀组漏水复用既有 Quixel Leakage 派生材质。
- 新模型为本地精确建模，含实际壳体厚度、倒角、端子、铰链、法兰、紧固件和托盘边缘；源文件为 `Authored/FacilityRoomFinish.blend`。

新增纹理副本上限 2048，保留流送；原始库资产不降采样。网格已构建 Nanite，开启显式切线并保留完整回退几何。新增组合件均无碰撞、不影响导航、不运行物理；小件使用 30 m 显示距离，建筑收边不使用近距消失。检修盒和阀组保留阴影。上述为制作设置，不代表已测得性能收益。

## 作者链与恢复

制作源：`SourceAssets/FacilityRoomFinish20261108/`。

- `capture_inputs.py`：读取五个房间的实际网格槽、尺寸和材料输入，输出 `inputs.json`。
- `prepare_layout.py`：从实墙、地面三角形和保留净空生成安装位置与收边，输出 `layout.json`。
- `place_table_trays.py`：按桌面支撑面与已有摆件空位制作医疗托盘位置。
- `author.py`：后台 Blender 导出 FBX 和可编辑源。
- `rr_assets.py`：制作本批材质、导入网格、构建 Nanite 并保存。
- `rr_recipe.py`：以稳定的房间与网格路径更新材质覆盖及装饰；重建时保护已变更的结构和独立材质修改。
- `install.py`：分别读取实际地图与磁盘目录，保留二者的非本批内容，再保存地图与生成配方。
- `run_background.ps1`：使用现有 UE 批次互斥，等待构建；编辑器已运行时沿用原桥，否则走无界面 commandlet。

重建钩子已接到 `DungeonFacilityFlow20261007/extend_catalog.py` 的主体材质升级之后，以本批成功保存回执为启用条件。源目录与实际地图在写入前分别备份到本批 `Backups/`。

## 落盘记录

最终导入日志：`SourceAssets/FacilityRoomFinish20261108/Receipts/import-20261109-000619.log`，commandlet 退出码 0。

安装回执：`SourceAssets/FacilityRoomFinish20261108/Receipts/install.json`，阶段 `map_saved`。初次模型导入中 Python 材质槽属性读取方式不兼容，已改为 `get_editor_property` 并完成接入。无需 C++ 修改或构建。

仅记录制作、导入和保存成功；未执行游戏、视觉、导航或性能验收。
