# 守寝者 V14：剔除衣物与左手修复（2026-10-17）

> 历史制作记录；2026-10-17 当前 V18 移动仍被用户否定并转待办。旧版本源/资产可能已归档，恢复位置与当前状态以 [收尾记录](../Publication/NightWarden20261017/README.md) 为准。

用户否定 V13 衣物并指出左手手指尖刺。本次剔除活动角色的围布、腰带、内层与模拟代理，恢复此前衣物覆盖区域的完整身体；保留待机、行走、百目挥击及既有 AI 参数。

## 源问题与修改

完整身体源中的左手表面有 26 个顶点混入其他骨骼权重。其中指尖顶点 95946/95947 的左大腿 `Bone_010` 权重约为 0.9098，原手指权重仅剩约 0.0902。该处原长约 0.65 cm 的边在现有行走源键下被拉到约 67 cm，在挥击源键下被拉到约 116 cm，形成用户反馈的尖刺。

依据源几何连通性区分左手与旁边的大腿表面，仅修复左手区域错绑的 26 个顶点：去除外来骨骼影响，按原比例归一化已有手部骨骼权重。没有削短手指、移动顶点、改 UV 或重新绑定整个身体。

源身体使用 V10 文件中保留的 `NW10_CompleteOriginalBody_Source`，含 145849 个顶点和 198386 个面，沿用 46 根原动作骨骼。导出仅包含该完整身体和骨架，不包含衣物、遮挡内层、物理代理或 V13 衣物辅助骨骼。

## 交付进度

- Blender 源与 FBX 已完成：`SourceAssets/NightWarden20261015/V14BareBodyHand/Authoring/NightWarden_BareBody_HandRepair_V14.blend`、同级 `Exports/SK_NightWarden_BareBody_HandRepair_V14.fbx`。
- 原始问题定位数据：同级 `Records/left_hand_source.json`。
- 修改明细：同级 `Records/authoring.json`，逐顶点保留修改前后的权重。
- UE 导入脚本与互斥入口：`SourceAssets/NightWarden20261015/Scripts/install_bare_body_hand_v14.py`、`v14_background.ps1`。
- 用户结束试玩后，已通过现有编辑器互斥桥导入完整身体、保存骨架并更新原 `BP_NightWarden`。保存回执为同级 `Records/ue_delivery.json`，`complete=true`。

当前使用 `/Game/Monsters/NightWarden/V14BareBodyHand/SK_NightWarden_BareBody_HandRepair_V14`，原 `BP_NightWarden` 已切换；复用现有 V08 待机、V07 行走与 V12 百目横扫原动画，布料模拟关闭。步速基准仍为 177.3769 cm/s、Yaw 转身速度 100 度/秒、攻击接触时间窗 0.54–0.73 秒。此次没有运行游戏、渲染或追加修复后验收。
