# 家具坐卧交互

适用于 FPSGAME 椅子、沙发、单人床和双人床；动作制作见 [坐卧动作](../../ue5-fps-arms-animation/references/furniture-rest-motion.md)，占位复制见 [场景动作与查看者](../../ue5-save-load-replication/references/scene-motion-and-viewers.md)。

- 运行入口为 `UFPSFurnitureRestComponent`，由角色构造；沿用搜索容器的 HUD 刷新节奏、E 键和轮廓材质。容器优先级与休息占用通过同一分派协调，不能再添加一套每帧全场景扫描或重叠快捷键。
- 配置在 `Content/ColdSteelData/furniture_rest.json` 与 `apartment_furniture_rest.json`。按实际网格路径、组件变换和 ISM 实例取位置；公寓实例缩放不是普通家具的默认缩放。配置模型覆盖不等于所有地图摆放实例均已检查。
- `slots[].seat` 是动作锚点，`focus` 是选位点，`mirror` 指明另一侧完整动作，`label` 用于左右侧提示。双人床可用 `auto_select_free_slot` 从已占侧回退到空侧；单人床和单座椅被占后只显示占用提示，不再执行进入。
- 在正常交互距离内命中床即可对齐到动作入口，不再要求玩家先走到指定侧边。对齐、入座、躺卧和退出共享一组入口偏移及朝向；不能只改最终 Root 而忽略进入路径和离床位置。
- 动作表按 `Rest.<Kind>.Enter/Idle/Exit` 三阶段发布，身体变体各自有对应动画；相机轨迹带来源 `animation`，与当前 clip 不匹配时弃用旧轨迹。共享 JSON 使用字段事务，数组从新读取的内容生成，保留非目标家具。
- 床上 SAN 恢复默认 5 点/秒，只由权威端在已躺稳的 Idle 阶段累计，按 `DeltaTime` 积分并限制到 MaxSanity；进入、退出和坐椅不恢复。地牢原有消耗仍叠加，不能把净变化永远写成 +5。

本案当前配置为 25 种家具、45 个位置，其中 7 种双人床。双人占位与整姿镜像已构建，尚无实际双玩家交互验收。工程记录：`Docs/Gameplay/furniture-rest-20261022.md`；本数字是 2026-10-25 快照，新加模型按实时配置确认，不硬编码到逻辑中。
