# 研究员 M-05 V02：硬直衣物适配

2026-10-09 整理补注：本文记录对应版本历史；当前组合、保留依赖及已移入 trash 的旧导出/备份路径见 [无面职员发布与恢复](../../../Docs/Publication/FacelessStaff20261009/README.md)。不要批量运行旧导入脚本覆盖当前入口。

2026-10-09。用户截图显示硬直时两侧大腿的黑色裤装穿出白大褂前摆。本次仅处理研究员受击硬直期间的衣物表现，不修改硬直时长、攻击时序或移动数值。

## 实际动作与原因

当前蓝图 `BP_FacelessResearcher` 的 `CombatExecution.HitClip` 指向 `/Game/Monsters/AI/A_Nurse_Hit`，长度 0.6 秒；它使用原女僵尸骨架，没有研究员的衣物曲线。V01 只为待机、移动和攻击制作了 53 个衣物修正形态，受击阶段没有对应形态。输入保存在 `reaction_source.json` 和 `Motion/A_Researcher_source_hit.fbx`。

## 制作变更

- 从 V01 完整作者文件继续制作，保留身体、衣物拓扑、UV、材质槽、骨骼权重及已有 53 个形态。
- 新增 19 个受击修正形态，按实际 30 fps、0–0.6 秒采样，覆盖受击、硬直保持取样和收势；忽略 FBX 导出多出的末尾重复帧。
- 上衣按完整身体表面保持间距，下摆以穿着的裤装外表面为碰撞包络。制作投射使用 16 mm 间距，沿连续衣面扩散后再次约束，避免平滑把衣摆拉回裤装内部。内外壁使用同一位移，口袋、门襟、胸牌随主衣修正。
- 完整动作骨骼轨道不改动；复制为研究员专用受击资产并绑定到其原生同源骨架，加入上述形态曲线，通过既有硬直时间采样。没有增加运行时布料、Tick 或动态碰撞求解。
- 作者源为 `Authoring/FacelessResearcher_V02.blend`，完整身体、独立衣物、运行组合分别导出到 `Delivery/`。完整身体 199621 三角面、运行组合 219505 三角面、总修正形态 72 个。

## 接入

导入 `SK_FacelessResearcher_V02` 和 `SK_FacelessResearcher_Clothing_V02`，沿用现有研究员骨架、物理资产与材质。将研究员蓝图的显示网格及 `HitClip` 指向新资产。待机、移动、攻击仍引用 V01 动画，原 F6“研究员 M-05”入口保留。

已通过现有编辑器互斥桥完成导入和保存，`ue_delivery.json` 为 `stage: saved`：两份 V02 网格、`A_Researcher_Hit_V02`、研究员骨架的曲线元数据及原角色蓝图均已保存，共 5 个资产。编辑器原有 PIE 已为导入结束，未关闭或重启编辑器；重新开始试玩并生成“研究员 M-05”即可使用新版。

本轮没有 C++ 变更，无需原生构建；没有启动游戏、截图、渲染或运行验收，由用户测试硬直和恢复期间的衣物效果。

恢复步骤：`export_reaction_v02.py` → `tailor_reaction_v02.py` → `prepare_reaction_import_v02.py` → `import_reaction_outfit_v02.py` → `import_reaction_clothing_v02.py` → `apply_reaction_v02.py`，均位于 `Tools/FacelessResearcher/`。已有编辑器时，接入批次走 `Tools/AssetPipeline/mcp_call_codex.ps1`；制作源和 V01 资产保留。
