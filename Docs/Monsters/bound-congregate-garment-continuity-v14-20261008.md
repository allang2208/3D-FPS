# 缚群 V14：连续衣片与独立袖口

> 历史阶段记录。2026-10-08 用户否定整体衣物并暂停；V18、V19 均未获认可。当前状态、最新参数和已归档证据的取回位置以[暂停与发布记录](bound-congregate-paused-publication-20261008.md)为准。

用户反馈 V13 后仍有明显拉扯、破碎感。V13 修正的是胶囊尺寸放大 100 倍，不代表衣物形状、权重和动态表现已经合格。

## 本次处理

V12 的逐点最近表面投射会让相邻布点落到不同供体肢体，并用该处肉体权重驱动衣物；清除投射后退化面又会改变衣物开口。继续降低模拟活动距离不能修复这套源结构。

- 从 V12 的完整肉体和骨架继续，只重做衣物。两侧衣片改为有序径向曲面，跨过细小肉瘤起伏，加入浅而连续的褶皱。
- 按真实肢体表面制作活动开口，平顺边缘；每片保留连续连接，不保留独立碎片或仅单点相连的网格。
- 主衣片仅使用躯干支撑。右上衣片平顺过渡到触手根部前四节，移除与各独立腿部之间的牵连。
- 两个袖口按各自小腿表面独立建环，几何焊接，仅 UV 接缝断开；不再复制肉体凹凸面或转移到邻近腿骨。
- 同源表面生成模拟代理和 3 mm 外层厚度。衣片最大活动距离约 3.2 cm、袖口 1.2 cm，缝合支撑区域固定，继续保留 Chaos 摆动。
- 肩部皮带和铭牌重新贴合新衣片，共用躯干支撑。
- 保留原材质、肉体几何与 UV、骨架、分叉触手、已认可攻击及 2 秒冷却。沿用 V13 碰撞单位修复和 V11 的 CCD 关闭设置。

## 制作与接入

作者入口：`Tools/BoundCongregate/author_garment_continuity_v14.py`。

导入保存：`Tools/BoundCongregate/import_garment_continuity_v14.py`，死亡表面使用 `author_soft_corpse.py --garment-v14` 生成新的完整绑定。

源文件与回执：`SourceAssets/BoundCongregateMeshy20261006/GarmentContinuityV14/`，含 Blender、FBX、`authoring.json`、`delivery.json`、导入日志及修改前蓝图备份。

目标活体：`/Game/Monsters/BoundCongregate/GarmentContinuityV14/SK_BoundCongregate_SurfaceFitV12_GarmentV14`。名称保留 `SurfaceFitV12` 是为了复用现有原生布料构建中的正确碰撞分支，不表示重新使用旧衣物几何。

匹配死亡网格和软体数据位于同目录 `Corpse/`。完成这些资产落盘后才切换 `BP_BoundCongregate` 的 `visual_mesh`，不修改其他玩法字段。

本次不修改原生 C++，无需重新编译模块。通过现有编辑器的互斥桥导入保存，不启动新的编辑器、PIE 或游戏，不做渲染或运行验收。以 `delivery.json` 的实际保存状态为准，游戏表现由用户测试。
