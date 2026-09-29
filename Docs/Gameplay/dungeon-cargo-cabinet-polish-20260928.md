# 地牢货箱和配电柜精修

用户截图对应正式设施组合件 `SM_Facility_CargoStack`、`SM_Facility_PowerCabinet`。本次针对其简单盒体、空白标签、平面假通风条及均匀锈斑重新制作几何和 PBR 表面。

## 制作内容

货箱保持原三箱堆叠与暗红配色，增加箱盖接缝、嵌板、钢箍、包角、锁扣、背部铰链、侧面提手、固定螺丝、不同编号货运标签和搬运标识。托盘改为具有叉车空隙的木梁、垫块、木板与钉头；裸木和涂漆箱体分开表达。

配电柜保持原绿灰双门外观，增加折边外壳、顶盖边缘、门缝、门封、门锁、弯折把手、铰链和紧固件。通风部位为真实开口、深色内腔与倾斜百叶；两只仪表具有分层表圈、密封垫、刻度盘、独立指针和安装件。新增启停按钮、铭牌、警示/额定参数牌及后部电缆接头。

两件共用一套原创 4096×2048 图集，分别提供 BaseColor、Normal、ORM。磨损集中于边缘、接缝和底部，漆面粗糙度、金属拉丝、木纹与氧化各有区分。无外部下载资产。

## 接入边界

正式路径不变：

- `/Game/Dungeons/FacilityScenes20260927/Meshes/SM_Facility_CargoStack`
- `/Game/Dungeons/FacilityScenes20260927/Meshes/SM_Facility_PowerCabinet`

新增共享材质与贴图位于 `/Game/Dungeons/FacilityPropPolish20260928/`。原地牢配置已经引用这两个网格，无需重建房间池或改换引用。

落地轴心、既有摆放/堆叠关系和原 UCX 碰撞体积保持。配电柜 21,504 三角形、一个碰撞体；货箱 32,452 三角形、两个碰撞体。每件一个材质槽，细节合并在静态网格内，保留 Nanite、显式切线、完整回退网格；本轮没有性能测试，不将此设置表述为 FPS 改善。

作者输入在 `SourceAssets/DungeonFacilityPropPolish20260928`；原设施作者脚本调用同一精修实现，原 FBX/清单和合集 Blender 同步更新，仅替换这两件。旧模型/作者输入在本批 `Backup` 中保留。

## 保存状态

模型、贴图与可编辑源已制作并落盘；两个正式网格、三张贴图和共享材质均已导入 UE 并保存。`Receipts/install.json` 状态为 `assets_saved`，待处理项为空。

用户退出运行后编辑器已关闭，因此改用无界面 Python commandlet 完成接入；沿用桥的同名互斥窗口，未打开交互编辑器。最终执行日志为 `SourceAssets/DungeonFacilityPropPolish20260928/Receipts/import-commandlet-02.log`，退出码 0。首次导入因尝试写只读的导入材质槽名称而停止，已改为继承 FBX 导入器生成的槽位元数据；第二次完成两件网格保存。

原作者目录的两件 FBX、清单及合集 Blender 均已同步，源文件保存记录见 `Receipts/sync-combined-source.log`。未保存地图、未改房间池；用户下次打开项目时即可使用同路径的新版本。

未运行游戏测试、视觉截图或性能验收，交由用户查看效果；不自动打开、重启编辑器或进入游戏。
