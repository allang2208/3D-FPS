# 镇魂钟 V5：直接复用现有普攻首击与上挑

用户否定 V4 的方向，要求直接复用现有动作进行匹配。本版不再使用 V1/V3/V4 的重击姿态、整组旋转和替代轨迹。

第一人称实际来源为当前运行入口：

- `NormalComboV4/A_Warhammer_Slash1` 的 0.84–0.97 秒完整发力段，映射到首击 0–0.10 秒；沿用源动作所有局部骨骼轨道，包括锤子、手腕、手指和双臂。
- 普攻原有接触后动作延续至 0.15 秒；在源动作既有姿态中选取与上挑低位最接近的接点。
- 0.15–0.24 秒只做两段动作的完整局部姿态混合；不旋转根骨修正方向，不重新解算 IK 或单独扭腕。
- 从 0.24 秒开始使用 `UppercutV1/A_Warhammer_Uppercut` 的完整释放与收势。沿用现有上挑技能的源时钟，源接触帧为 1.05 秒，对应镇魂钟第二击 0.42 秒；上一版使用的高位姿态不能代替这段完整上挑。
- 专属蓄力直接采样普攻首击 0–0.84 秒，最终姿态与首击释放起点一致；中途松手按相同源时钟继续普通攻击。

Default / kaitlin 各自复用 `player_body.json` 当前的 `Warhammer.FullBody.Slash1` 和 `Warhammer.FullBody.Uppercut`。新增各自匹配的蓄力与二连动作，通过四个具体角色字段接入。命中、伤害、技能消耗与总时长不变。

`inputs.json` 记录实际输入；`author.py` 是可编辑拼接源；`authored.json` 记录已保存资产与接点。`prepare_and_author.py` 使用隔离 commandlet 制作，`build_and_publish.ps1` 完成 Editor/Game 构建并经共享配置事务接入。构建及接入结果分别见 `build_receipt.json`、`published.json`；这些回执不代表用户体验通过。

没有启动游戏、运行测试、截图或渲染。V2/V3/V4 已移入 `trash/warhammer-refinements-retired-20261025/SourceAssets/RuneboundWarhammer20261022/` 供追溯，新入口为 `FinalTollDirectReuseV5/A_FinalToll_DirectReuseV5`。

2026-10-24 已完成本地接入：Editor / Game 两个目标构建均为退出码 0；最终经 `author_and_publish_main.ps1` 在项目无界面 commandlet 中创建并保存五份动画，然后通过配置事务写入四个角色叶字段。资产制作与接入进程退出码为 0，记录于 `main-author-process.json`。独立宿主的初始化及旧编辑器接口尝试未产出资产，正式结果以主工程保存回执为准。未自动重新打开 UE。
