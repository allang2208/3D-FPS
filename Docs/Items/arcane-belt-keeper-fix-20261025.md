# 星律导能腰带头顶悬浮修复

根因是 `author.py::tailoring` 给固定钉设置局部坐标后，没有在下一只皮革固定环之前恢复世界坐标。后侧 3 个固定环的原生腰线又被叠加一次腰部变换；绑定没有指向头部，错误已经存在于源几何中。

修复在每只固定环开始时恢复世界坐标，保留原本形状、尺寸及材质，重新从对应腰部位置采样权重。ModelR1 保留，ModelR2 保存修正版可编辑 Blend、FBX、GLB；男女三级 LOD、正面物品图标和静态掉落网格同步重制。

| 身体 | 修复前 LOD0 高度范围（cm） | 修复后 LOD0 高度范围（cm） |
| --- | --- | --- |
| Jason | 90.55–195.96 | 90.55–100.09 |
| Kaitlin | 91.03–193.88 | 91.03–102.05 |

已完成本次授权范围内的组件几何、六份 LOD 权重以及 UE 已保存渲染 LOD 回读检查。所有组件处于腰部范围，未发现空权重或头颈权重。未启动游戏或联机测试，也未重新验收其他服装/动作组合。

新穿戴资源位于 `/Game/Characters/ModularOutfit20260924/ArcaneConduitBelt20261025/KeeperFixR2`，两种身体的 world/owner 配方均已切换。旧物品实例可能保留旧掉落路径，该路径的网格也已同步修正，修改前包保存在 KeeperFixR2/Before。物品 ID、强化和战斗属性保持原值，无需修改 C++ 或重新构建。

重新进入游玩后加载修正版。生产入口：Blender `Tools/ArcaneConduitBelt/keeper_fix.py` → Blender `Tools/CombatBeltsIntegration/prepare_arcane_keeper_fix.py` → Python `check_arcane_keeper_fix.py` → 现有互斥桥执行 `save_arcane_keeper_fix.py` → Python `publish_arcane_keeper_fix.py`。

执行和检查记录：`SourceAssets/ArcaneConduitBelt20261025/KeeperFixR2/published.json`。
