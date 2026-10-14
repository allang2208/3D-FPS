# 第二间分流大厅：突发事件现场布景

2026-10-10。对象为正式随机地牢的 `FacilityTransit`，同步保存两个现有分流大厅样板。保持现有 32 盏灯、门洞、楼梯、分流拓扑和交互容器。

同日后续已将本批 9 个原创杂物升级为独立细节版本，72 处正式引用已替换；现用模型与 PBR 制作记录见 [杂物细节升级](transit-incident-detail-20261010.md)。下文保留初版现场布局与来源记录。

## 布景组织

- **下廊清洁中断**：黄色空心清洁桶倒伏，包含桶沿、提手、轮子和挤水部件；拖把横倒、棉条散开贴地，警示牌倒在旁边。位于西侧下廊等候长凳与通行区之间。
- **执勤文件散落**：楼上值班区倾倒金属纸篓、摊开的文件夹和纸张；楼下另一处文件夹与夹板形成第二处散落中心。纸张带表单印刷、卷边、折痕和薄纸厚度。
- **应急取用痕迹**：PPE 等候区前增加侧倒椅子、横放灭火器及纸张，复用现有椅子、灭火器网格和原材质；断续血迹从等候区向外延伸。
- **维修台附近**：维修记录夹板、文件夹和散纸离开原本规整的台面，少量血迹连接现场。保留原维修台、工具箱及其交互。

共增加 76 个静态布景摆放，其中 65 张废纸；另有 11 处血迹贴花。重复纸张使用 4 个共享网格，正式生成器按既有实例化规则合批。杂物不产生碰撞、物理模拟、拾取、怪物或新 Tick。纸张不投射额外阴影；较大的倒伏道具保留阴影。

局部物体以实际网格最低点或 90 度倾倒后的包围轴落地。血迹保持扫描贴图原始正方形比例，改变尺寸与旋转形成断续痕迹，不将同一贴图强拉成长条。贴花投射半深度 1.2 cm。

## 来源与维护

- 原创模型与纸面／警示印刷：`SourceAssets/TransitIncidentDressing20261010`。黄色塑料、纤维板、棉条、印刷材质在独立目录创建；钢、橡胶、普通纸、青色设施材质复用现有资源。
- 血迹：直接复用 `/Game/Dungeons/IsolationWard20260929/BloodScan/M_WardBlood_Quixel`，不修改它。来源为用户已有 Quixel Blood Stain `sgfjdepc`；元数据与授权来源沿用 `SourceAssets/DungeonIsolationWard20260929/BloodScan20260929/README.md`。
- 灭火器：**Fire Extinguisher Old Rusty 3D Scan**, grafi，CC BY 4.0。来源和许可见 `SourceAssets/DungeonArtPass20260922/PROVENANCE.md`，原资源及署名保留。
- 椅子与夹板：直接复用 ReceptionHall `Refine20261007` 已存资产。
- `recipe.py` 保存按房间局部厘米坐标的配置；`placements.json` 保存复用道具的落地高度。目录重建和样板重建均已接入此覆盖层，成功安装后才自动恢复布景。

## 落盘状态

16 个本批资产已保存：9 个网格、5 个材质、2 张贴图。正式地图 `/Game/GameMaps/L_Dungeon_Randomized` 及现有 `L_FacilityTransit_Subject`、`L_FacilityTransit_Alternate_Subject` 均已保存，源 catalog 同步。

保存回执：`SourceAssets/TransitIncidentDressing20261010/Receipts/install.json`，阶段 `maps_saved`。后台导入日志 `Receipts/import-20261010-112633.log` 结束为退出码 0，0 error、10 项现有编辑器接口／导航警告；无本批材质编译失败或切线导入警告。

仅完成制作、导入与保存；没有打开 GUI、运行游戏、渲染截图或执行视觉／运行测试，由用户体验确认。
