# 地牢排水坑粘液与破损墙面

目标是 `/Game/GameMaps/L_Dungeon_AuthoredExpansion` 的排水坑、破损支护室断口与碎砖，以及缺口后侧神像朝向。复用现有房间布局，制作根目录 `SourceAssets/DungeonHazardPolish20260922`。当前实际接入状态以 `Receipts/install.json` 为准；本文件不代替保存结果。

## 腐蚀坑道

`ADungeonPusChannel` 位于 `Source/FPSGAME/Dungeons`。默认伤害和间隔从 `FFatZombiePusSettings` 初始化，保持胖子僵尸粘液的每 0.5 秒 8 点原始腐蚀魔法伤害，调用已有 `UCorrosivePusDamage` 和 `ApplyDamage`，由现有生命与战斗公式处理最终扣血。环境池持续存在，离开接触范围即停止命中，不叠加新的中毒状态。

Actor 原点位于沟底，当前世界位置为 `(2350,-3600,39)` cm。液面覆盖实际沟内矩形，半宽 141 cm、半长 391 cm，约 4.3 cm 深。服务端定时查询玩家；每个脉冲按 Pawn 去重，同时要求脚底在湿润范围、接近沟底且人物着地。上方 94 cm 桥面和坑边地面不能仅因胶囊与查询体重叠而掉血；跳跃判断沿用原胖子粘液的着地约定。池面没有阻挡碰撞，沿用原沟底与桥面碰撞。

材质 `M_DungeonViscousPus` 独立继承胖子粘液制作来源和绿色浑浊基调，借用喷泉双层流动法线、逐像素表面光照及解析波纹方法。低速流向、局部密度变化、错相气泡环和小幅顶点起伏由材质 Time 驱动，不进行逐帧 CPU 网格重建。原怪物和喷泉材质不被改写。

配方保存在 `DungeonRoomShells20260922/Config/rooms.json` 的排水房 `trench.hazard`；整场安装器已经接上该配方。危险区域需要包含新增类的常规原生构建。

## 断面、碎砖与神像

`author_materials.py` 制作原创 2K 碎裂混凝土 PBR：0.64 m 物理平铺，碎骨料、细砂、孔隙和凹陷由同一高度场派生 BaseColor／Normal／Roughness-AO／16 位 Height。新材质实例复用墙面高度材质父级，替换的仅是破墙断面与碎石，不改变通道已认可的剥落瓷砖。

房间源的 `room_detail_geometry.py` 将断口和混凝土碎块绑定专用材质；地面另有带图集釉面、真实陶瓷芯厚度与不规则边缘的碎砖。网格更新范围是 `SM_RS_ShoredBreach_Shell` 和 `SM_RS_ShoredBreach_Debris`。

神像按实际场景 Actor 路径记录单独旋转，朝向缺口外部；旋转时维持原有世界包围盒中心，避免偏离底座位置。具体操作写入 `Config/scene-actions.json`，幂等设置绝对旋转，重复执行不会每次累积转角。

本轮只进行制作、必要编译、导入和保存。未运行 PIE、伤害测试、截图或验收渲染；实际扣血和视觉效果交由用户测试。
