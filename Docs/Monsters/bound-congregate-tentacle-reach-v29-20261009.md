# 缚群 V29：30 米触手

用户已确认 V28 拍击合格。本轮保留拍击动画、五次命中时刻、范围及伤害；仅制作触手射程和对应模型。V28 撕咬和 V25 衣物结构继续使用。

## 动作与命中

- 最大起手距离从 360 cm 改为 3000 cm，以怪物 Actor 到目标中心的三维距离计算。前方 120 度、视线、20 秒冷却、伤害和三次 F 脱离规则保留。
- 缚群仇恨半径 2400 → 3000 cm，接管 AI 时配置其独立视距，消除通用 1600 cm 视距对远程起手的限制；其他怪物的感知保持原配置。
- 原来的方向播放只改变甩鞭朝向，固定约 5.12 m 的整根骨链无法覆盖 30 m。V29 保留肩部／粗根，只有第 14 骨之后的细段按目标距离渐进展开。第 48–56 骨保留为密集末梢，用于甩尖和缠绕。
- 根部仍由原录制甩鞭及主体反向承重驱动；中后段添加向末端传播并衰减的横波，结束位置对应已锁定目标。释放时锁定方向，不持续追踪躲开的玩家。
- 蓄力 0.62 秒；近距离释放保持 0.09 秒，最远 30 m 渐增到 0.18 秒，沿原非线性曲线爆发；回收为 0.72 秒，以可见长链逐步缩回原待机位置。全身发力、触手展开和服务端命中共享释放时钟。
- 命中保留 24 cm 末端扫掠球；补充可见末端八小段逐段扫掠，避免用弯曲触手两端间的不可见长弦结算伤害。保留遮挡、最终姿态后一帧扫掠和捕获脱离。
- 仅攻击期间扩展组件渲染包围范围，避免主体离开屏幕后长触手被裁掉；不改角色胶囊或用于接地的导入 bounds。地形采样仍为固定 15 点和既有频率。

## 模型

从 `SourceAssets/BoundCongregateMeshy20261006/GarmentDrapeV25/BoundCongregate_GarmentDrapeV25.blend` 派生，只修改 `BC_AttackTentacle` 中后段。

细段边增加两处细分、修整局部鼓包与尖点、按中心线改为相邻站点蒙皮。身体网格顶点 93922 → 121751，其中 31417 个细段顶点参与重新塑形／配重。保留原 UV、雕刻表面和材质，展开时按局部伸展量适度收细截面，最小径向比例 0.55；没有整体放大身体。

骨架仍为原参考姿态，攻击链 57 骨；V28 拍击与撕咬资源不重新烘焙。V25 衣片、固定贴身主体、短模拟破边、内部身体裁面和材质复用。新显示网格另建匹配连续软体死亡表面，不能引用旧顶点对应表。

## 重建入口与交付边界

- 外部制作：`Tools/BoundCongregate/author_tentacle_reach_v29.py`。
- 运行时：`BoundCongregateTentacleReach.h`、`BoundCongregateTentacleControl.h`、`BoundCongregateTentacle.cpp`、`BoundCongregateWhipDrive.h`。
- 导入：`Tools/BoundCongregate/import_tentacle_reach_v29.py`，复用已有衣物和软体死亡保存流程。
- 后台构建和实际保存：`Tools/BoundCongregate/finish_tentacle_reach_v29.ps1`。
- 新资产目录：`/Game/Monsters/BoundCongregate/TentacleReachV29`；继续接入原 `BP_BoundCongregate` 和 F6 缚群入口。

模型源与 FBX 已导出。后台 commandlet 已实际保存新网格、三件衣物模拟、匹配连续尸体与原蓝图，退出码 0，最终日志 0 errors。保存回执同时记录保留的 V28 拍击／撕咬资源。补充独立 AI 视距和命中距离上限后的最终 Editor/Game 必要构建均为 `Result: Succeeded`，对应日志位于 `SourceAssets/BoundCongregateMeshy20261006/TentacleReachV29/build-FPSGAMEEditor-console.log` 与 `build-FPSGAME-console.log`；导入为同目录 `import-final.log` 和 `delivery.json`。

按用户规则不主动运行游戏、测试、截图或验收；最终表现交由用户体验。
