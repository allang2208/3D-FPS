# 201 轻机枪精修记录
> 后续状态（2026-09-28）：本页两块厚楔形上盖及细杆圆环瞄具被用户指出偏离原始参考，已由 [Refinement02 参考修订](lmg201-reference-correction-20260928.md) 取代。手部与动作修正仍沿用，本页的保存成功不代表旧外形获认可。


用户反馈首版表面粗糙、机械瞄具细节不足、局部毛边和左手穿模。本轮参考 QBZ191 与 A762 的制作方法，修改模型、PBR 和托握动画。

当前制作入口：`SourceAssets/LMG20120260927/Refinement01/README.md`。最终保存状态：同目录 `DELIVERY.json`。

最终 UE 保存批次已完成：精修表面、12 个动作和 3 个图标均返回保存成功。记录为 `Refinement01/import_revision_final_mcp02.txt`，通过现有编辑器会话执行，未启动或重启编辑器。

## 修改

1. 前后机械瞄具头部重建为闭合圆环、真实孔壁、平顶准星和细倒角；保留原瞄线与转轴。
2. 两块机匣上盖重建为规则壳体，清除重叠残面。其余表面做限幅毛边处理，保留特征边与原结构细节。
3. 按机匣涂层、外露钢和聚合物分区，收窄粗糙度波动，降低原始基色中的光照污染。原拓扑区域保留结构法线，新建区域使用自身 UV 与法线。
4. 修正 V7 裸手重复绑定变换，使用最新原生裸手拓扑和权重；重新调整掌心、手腕、拇指及四指托握。
5. 保存 12 个动作的托枪／回位修正，保持原取匣、插匣和机械事件时序。更新库存与机械瞄具图标。

## 参考

- `ue5-weapon-workflow`：`generated-rifle-refinement.md`、`weapon-finish.md`。
- `ue5-fps-arms-animation`：`grip-arm-refinement.md`、`pose-contact.md`、`accepted-bare-hands.md`。
- `Docs/Weapons/qbz191-machined-sights-20260913.md`。
- `Docs/Weapons/qbz191-hero-surfaces-20260913.md`。
- `Docs/Weapons/qbz191-receiver-coating-20260913.md`。
- `SourceAssets/A762Meshy20260920/Refinement01`、`Refinement03`。

## 检查范围与交付边界

按用户本次要求，对左手接触进行源场景检查。8 个待机、瞄准、换弹起始和回位样本均未发现左手与枪体相交三角面；记录见 `Refinement01/contact_check.json`。接触图使用源场景和诊断皮肤材质，不能代替 UE 中的最终光照、服装、动作混合和运行体验。

资产沿用 `/Game/Weapons/LMG201/Production20260927` 路径；精修材质与备份位于 `/Game/Weapons/LMG201/Refinement01`。实际导入与保存以回执为准。本轮未修改 C++，未主动启动 UE 编辑器或 PIE，未做额外玩法、性能回归，交由用户测试。
