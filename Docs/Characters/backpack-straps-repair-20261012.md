# 背包肩带与回带修复

用户反馈第三人称登山背包的背带错乱。当前 `ue_mountain_backpack` 的骨骼网格为 `EquipmentFit20261003/SK_Jason_Backpack`，直接跟随角色身体，组件相对变换为单位变换，没有同时显示静态替代背包。

## 定位

读取的是当前已保存背包网格，不从运行中的 Leader Pose 组件转换动态网格。它与旧作者源的顶点位置最大差异约为 0.000008 cm，可对应到原始带片。

1. 旧贴合将背带权重从衣物最近表面转移，5,148 个顶点含有超过 1% 的上臂或腿部权重，局部合计最高约 43%。腋下片受上臂驱动，低位带片受大腿驱动，抬手和迈步会拉走背带。
2. 旧肩带拟合把原来截至胸侧的厚肩垫一路绕到侧腰，再返回包体；原有侧带、腰部碎片仍保留，形成重叠和悬空。

## 修改

- 两条厚肩带从包体上固定点越肩到下胸，在胸侧接窄回带，再连接包体下固定点。保留原肩带／回带三角形和 UV；局部重排几何与法线。
- 移除旧适配留下的前侧悬带、腰部多余片和旧回带挂接过渡面，保留包体、口袋、后侧扣带及其材质／UV。
- 包体仅跟随 `spine_03`；带路在 `spine_03`、`spine_04` 间平滑分配，肩顶最多混入 12% 同侧锁骨，去除全部手臂和腿部权重。肩带连接包体的末端保持包体绑定。
- LOD0 从 43,000 变为 39,328 个三角形，4,669 个带片顶点被重整；这是移除多余带片的结果，没有对包体作全局减面。保留现有材质、骨架、运行组件和装备配置。
- 本次修复针对穿戴形态；库存图标和未穿戴静态背包不变。没有增加布料物理、Tick 或新材质。

## 制作与保存

- 输入：`SourceAssets/BackpackStraps20261012/backpack_input.json`、原始背包源及 `native_islands.npz`。
- 作者脚本：`Tools/PlayerBody/author_backpack_straps20261012.py`。
- 可编辑网格源：`SourceAssets/BackpackStraps20261012/backpack_repaired.json`，包含几何、逐角 UV／法线、原生骨骼和权重；带路参数保存在 `authoring.json`。
- 保存脚本：`Tools/PlayerBody/save_backpack_straps20261012.py`。既有 `save_jason_backpack_straps.py` 也改为优先采用该修复源，避免旧肩带脚本恢复错误绑定。
- 保存到原有 `SK_Jason_Backpack` 引用，原包备份已移入 `trash/player-presentation-retired-20261012/SourceAssets/BackpackStraps20261012/Before/`。

没有修改 C++。原有穿戴资产已在无界面命令中实际保存，回执为 `SourceAssets/BackpackStraps20261012/saved.json`；日志 `save-backpack.log` 完成于 `Success - 0 error(s), 5 warning(s)`，保留原有 1 档 LOD 和原材质。源码／网格保存不代表视觉验收，尚未运行游戏或截图，动作中的效果由用户体验确认。
