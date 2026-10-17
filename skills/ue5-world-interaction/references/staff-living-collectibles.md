# 生活区收集品与排水检修工具箱

先读 facility-search-containers.md。2026-10-16 批次新增非装备收集品，用户明确不要把现成装备直接塞入生活区收集池。

| 物品 ID | 占格 | 回收价 |
| --- | --- | --- |
| search_private_perfume | 1×2 | 900 |
| search_portable_music_player | 1×2 | 1200 |
| search_compact_camera | 2×2 | 2400 |
| search_business_laptop | 3×2 | 3600 |

先完成模型、材质、图标与明确用途，再接 items.json、拾取模型路径、Cook 和搜索池。相机现用 V2 网格配 V1 材质，不能删除 V1 目录。既有食品、U盘、磁带、硬盘等按柜子用途复用，不另造同义物品。

生活区共 67 个稳定入口、8 个 staff_* 池，件数权重 [0,100,0,0]：首次固定一件，条目权重和为 100 时才等于此次单抽百分比。这不是其他区域的通用件数规则。

排水入口 Hospital.Drainage.Tools.Entry 与检修位置 Hospital.Drainage.Tools.Service 直接绑定 research_maintenance；不复制新池。当前该池固定一件，零件箱32、精密机件28、万用表20、电源控制10、检修工具8、冲击扳手2（具体 ID/权重以 scene_search_loot.json 为准）。

67/2 是配置入口数量，不保证每局全生成。已有搜索结果和已取空状态不重置；运行种子、完整容器 ID、共享事务与服务器生成继续沿用。配置缓存读取一次，新进程加载新数据，但不能为此主动重启用户编辑器。

原始模型、PBR和 UE 包留本机；公开原创作者脚本、四个条目、67+2 绑定及精确共享接入补丁。恢复/许可和历史构建边界见 Docs/Publication/LivingArmor20261018/README.md；未做生活区真实双客户端取物验收。
