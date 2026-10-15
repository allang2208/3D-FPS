# M66 V17 炉息喷吐

2026-10-15 已完成制作、常规 Editor DLL 构建、后台导入和原角色保存。原角色仍为 `/Game/Monsters/IncineratorBossM66/BP_M66RigPreview`，沿用现有 F6 M66 入口。

## 动作与时序

| 阶段 | 时间 | 实现 |
|---|---|---|
| 慢蓄势 | 0–1.20 s | 双脚保持支撑、躯干略后仰、背囊鼓起、口腔开合和吸气声；前 0.95 s 以最多 28°/s 缓慢转向，随后锁定喷吐方向 |
| 快发力 | 1.08–1.20 s | 短促前压，与起喷时刻衔接 |
| 喷吐 | 1.20–2.40 s | 锁向灰焰持续喷出，暗红/橙色热流，带流量脉动 |
| 停顿 | 2.40–2.80 s | 停止发射，保持收势前停顿；已有流体短暂消散 |
| 慢收势 | 2.80–3.40 s | 恢复站姿和合口 |

409 帧、120 Hz 的整身动画保存为 `A_M66_FurnaceBreath_V17`。以已认可的 V10 模型和完整骨链为基础；新网格 `SK_M66_Furnace_V17` 只增加口腔局部形变 `M66_FurnaceOpen`，不改中性几何、拓扑、UV 或既有权重。口腔形变排除实际双手及下垂组织区域，运行时由同步动作时钟驱动，动画 FBX 中的零值形变曲线不参与控制。

保留原 V08 横扫、V16 握拳砸地、V07 死亡物理、V10 下垂组织动态及 V12 背孔黑烟。制作源见 `Authoring/M66_furnace_breath_v17.blend`；FBX 与合成吸气 WAV 见 `Export/`。

## 战斗与联机

- 起手距离 400–900 cm，射程 900 cm，完整横向扇角 35°，独立冷却 12 s。满足冷却、视线、朝向及可用资产条件时，在现有战斗循环中选择喷吐。
- 伤害时刻为 1.20、1.40、1.60、1.80、2.00、2.20 s，每次 25 点减伤前火焰/魔法伤害，完整承受共 150 点；不额外施加眩晕、目盲或燃烧状态。
- 每跳重新判断敌我、目标身体采样点、喷流空间与遮挡，每个目标每跳最多一次。复用魔法龙息的实体遮挡规则；墙、完整楼板、门及实体冰墙阻挡，单位不会替后方实体遮挡查询截断射线。
- 服务器负责动作选择、瞄准锁定、六次伤害和中断。复制现有动作序号/开始时间以及喷吐方向，客机依服务器时钟播放，客户端不结算伤害。晚收到状态时进入当前阶段，不重播整套动作。
- 眩晕、冻结、击飞和死亡沿现有动作中断路径取消剩余伤害；喷吐期间不执行横扫/砸地，移动停止。
- 205 个 60 Hz 口部位置样本供服务器和客户端使用，不依赖服务器实时骨骼动画求值来定位伤害源。

对应原生代码为 `M66FurnaceBreath.cpp`、`M66FurnaceVisualComponent.*`、`M66BreathTiming.h`，通过现有 `M66ClawSweep` 动作状态、`M66MovementComponent` 以及 `M66AnimInstance` 接入。

## 特效与音效

`NS_M66FurnaceBreath` 基于已保存的魔法龙息 VolumeV8 R5 独立复制，保留流体、坐标修正、GDF 碰撞和九条方向射线裁剪；改为灰黑密度及暗红/橙色温度色阶。每只怪物一个流体实例，最长轴 80 格，攻击前异步准备；空闲完成准备后停止表现组件 Tick。停止喷吐后最多 0.65 s 淡出，中断时缩短至 0.15 s。

`M_M66FurnaceGlow` 提供口内暗橙光，吸气声为本轮合成的 `S_M66FurnaceInhale`，喷吐声 `S_M66FurnaceRelease` 复制既有火焰施法音并降低音调；独立空间衰减资产 `ATT_M66Furnace`。玩家龙息和百目黑烟资产均未由本轮修改。

## 构建及落盘

- 常规 Editor 构建：`Saved/BuildEditor/build-20261015-110638.log`，`Result: Succeeded`，34.14 s；记录见 `Records/native_build.json`。
- 后台导入：`Records/install-20261015-111157/engine.log`，进程退出码 0，11:12 保存完成。
- 网格/形变：`Records/skin_import.json`；动画：`Records/motion_import.json`；材质/Niagara/声音：`Records/effect_install.json`；原角色参数与资产引用：`Records/character_install.json`。
- 上述是实际构建、资产编译和保存结果；未启动游戏、渲染、试听或主客机测试，由用户测试动作、表现及战斗体验。

后台安装入口为 `run_headless_install.ps1`；脚本会避让项目编辑器及 Editor DLL 构建。资产导入链为 `import_skin.py → import_motion.py → author_effect.py → install_character.py`。只需继续某一步时使用相应脚本，避免重复导入无关资产。
