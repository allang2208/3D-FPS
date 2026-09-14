# 715 保留形态的线条与表面细节修订

用户确认整体形态可用，要求参考 QBZ191，让检视时金属线条和细节更清楚。本版从 Mirror 复制运行网格，只替换三组金属表面。

采用 QBZ191 Hero 的结构法线与反射表面分离方法：源件高模恢复原角点法线，取消此前对源结构法线的过滤和整体衰减；刻字、浅槽、已有倒角重新向现有低模烘焙。各对零件在烘焙空间分开，避免邻件投射。

继续使用 715 的镜面不锈钢颜色。枪架、护罩、弹仓端面、击锤、扳机和锁扣分别控制粗糙度；窄线条遮罩只影响局部表面反差，不削弱结构法线。没有再次重建整枪、改变轮廓或增加颗粒凹凸。

已制作 Frame/Cylinder/Steel 三组共 9 张 4K 贴图、三个干材质、三个湿材质和独立湿润映射资产。运行主体为 `/Game/Weapons/DanWesson715/Detail20260914/SK_DW715_Manny`；配件继续使用 `Mirror20260914/Attachments`。动作、声音、奔跑及枪匠逻辑沿用现有入口。

可编辑源与制作脚本：[完整制作说明](../../SourceAssets/DanWesson715Detail20260914/README.md)。导入脚本已执行至 `DW715_DETAIL_IMPORT_COMPLETE` 并保存资源；commandlet 仍因工程已有 GameFeatureData 配置错误返回 1，详情在本版 `import.log`。

原生 Editor 构建成功，FPSGAME / AutoFootstep / AutoFootstepEditor 使用模块后缀 `71416`，日志为 `SourceAssets/DanWesson715Detail20260914/build.log`。重启编辑器加载本版模块与表面。

未启动游戏、效果渲染或测试，实际近景表现交由用户测试。
