# M24 原厂枪托与先进枪机的表面衔接

## 当前版本：使用原厂握颈几何和材质

用户反馈上一版仍能看出衔接件。读取正式先进枪机发现，原来的过渡体延伸到前方 10.4 cm，旧遮罩在 6 cm 已回到金属表面。此版移除该过渡体及其切口残片，从当前 `SK_M24_MotionV9` 的 `M24_FactoryRearSeat` 读取实际相邻握颈三角面、面角 UV 和法线，保留切边，在先进机匣内部收口。新 `M24_FactoryStockContinuation` 槽直接绑定原厂枪托的 `MI_M24_Regional_host`，金属侧壁单独使用统一机匣涂层。正式先进枪机网格已在原路径保存。制作源和备份位于 `SourceAssets/M24StockJunctionR2_20261105/`。[保存记录](../../SourceAssets/M24StockJunctionR2_20261105/saved.json)。最终装枪观感待用户确认。

## 旧版位置遮罩

2026-11-05：用户反馈原厂枪托衔接部位材质不自然。本轮沿当前加载路径读取原厂枪身、原厂贴腮板与先进枪机材质。原厂枪身的原厂枪托、握颈、尾座和前段已经共用 `MI_M24_Regional_host`；贴腮板同样使用当前区域配方。明确差异位于先进枪机的原厂枪托连接颈：该区域原先与机匣共用全金属表面，而相邻保留的原厂握颈是非金属复合材质。

从原始 glTF 的实际颜色及 ORM 贴图按原厂 UV 采样，衔接附近的金属度接近 0。源 FBX 随附贴图与当前 glTF 图集不同，本轮最终配方以当前 glTF 图集为准。原厂真实切边在 Blender 纵向 0.020163–0.030502 m，按当前静态资产转换到厘米并反向 Y。

为标准先进枪机创建私有母材质与实例，只重绑 `SM_M24_m24_advanced_action` 的 `M24_AAS_CoatedMetal` 槽。后端衔接区采用原厂握颈采样后的线性底色约 `(0.02051, 0.02252, 0.02351)`、基础粗糙度约 `0.58848` 和非金属反射；从前向 3.10 cm 到 6.00 cm 过渡回原机匣金属，宽度与高度约束限定在连接颈。湿润层采用与原厂相同的自动非金属响应。原厂表面不被整件金属化，机匣其他金属、独立后握把版本、骨架后托及碳纤维后托保持原有绑定。

正式资产：

- `/Game/Weapons/M24/FactoryStockSeam20261105/M_M24_FactoryStockTransition`
- `/Game/Weapons/M24/FactoryStockSeam20261105/MI_M24_FactoryStockTransition`
- `/Game/Weapons/M24/AdvancedAction20261029/Meshes/SM_M24_m24_advanced_action`（原路径，槽绑定已保存）

制作源、原厂采样、修改前备份与保存回执位于 `SourceAssets/M24FactoryStockSeam20261105/`。新增材质目录已加入打包配置。后台资产操作完成，未启动交互编辑器、游戏、PIE、预览渲染或验收测试；最终观感由用户确认。

碳纤维枪托的新造型已暂停。原图透视被用户否决，当前游戏中的旧模型继续作为装配依赖，归档边界见 [枪托制作记录](m24-carbon-spine-concept.md)。
