# 鼓囊 M-09：Meshy 原骨架与待机／移动制作源

当前收尾状态（2026-10-13）：已完成 V01～V15 的制作/接入与 M 系列接地补齐；V13 将方向箭头移到屏边，V14 已去除怪物吸气蓄力声，V15 加入四足楼梯适配。下文按版本保留开发历史，旧“尚未制作/部署”仅描述当时状态。当前恢复顺序、56 份归档和公开边界见 `Docs/Publication/MSeries20261012/README.md`；尚未游戏验收。

用户于 2026-10-12 提供已经减面和绑骨的 `C:\Users\allan\Downloads\Meshy_AI_Character_output.glb`，要求接入游戏，先制作待机和移动。

## 原始资产

- 原件副本：`Source/BellowSacLobber_user_rig.glb`。
- SHA-256：`fe79c141f2cf6239123efff094e39732f7d830c5321f495224097b79881cc552`。
- 保留原网格拓扑、UV、蒙皮权重、32 根变形骨和原始 PBR 贴图；未重新减面或重新绑骨。
- 按原始尺度接入：约宽 115.2 cm、长 263.2 cm、高 170 cm。
- `Authoring/BellowSacLobber_source.blend` 保存原始导入；`Authoring/BellowSacLobber_locomotion_v01.blend` 保存可编辑动作。
- Blender 导入器产生的骨骼显示控件不属于怪物网格，不导出到游戏。

## 动作

| 角色 | 文件 | 循环长度 | 对应游戏速度 |
| --- | --- | --- | --- |
| 待机 | `Exports/A_BellowSacLobber_Idle_v01.fbx` | 4.8 s | 0 |
| 慢速游荡 | `Exports/A_BellowSacLobber_WalkSlow_v01.fbx` | 1.2 s | 40 cm/s |
| 正常移动 | `Exports/A_BellowSacLobber_Move_v01.fbx` | 1.2 s | 80 cm/s |

均为 60 fps 原地循环，直接基于用户原骨架制作，没有套用外部动作。待机包含缓慢呼吸、背囊伸缩和喷口轻微随动；移动采用四拍步态、76% 支撑期，制作时用离线腿链求解安排落脚、抬脚和重心转移。步幅与标称移动速度配套；游戏中使用现有四足动画系统按实际速度混合和调节播放速率。

## 制作与导入

- `Tools/BellowSacLobber/prepare_source.py`：原件归档及 Blender 源资产。
- `Tools/BellowSacLobber/author_locomotion.py`：原骨架动作制作、FBX 和原始贴图导出。
- `Tools/BellowSacLobber/import_mesh_headless.py`：UE 无界面网格、骨架、材质导入。
- `Tools/BellowSacLobber/import_motion_headless.py`：UE 无界面动作、动画配置和角色蓝图导入。
- 编辑器已运行时，对应 `import_mesh.py` / `import_motion.py` 由项目现有 MCP 批次互斥桥执行。
- `Records/source_manifest.json` 记录原始骨骼和网格；`Records/locomotion_manifest_v01.json` 记录动作制作参数；`Records/ue_import_v01.json` 记录真正保存成功的 UE 资产。

V01 只包含待机和移动。2026-10-12 后续攻击与投射物制作源在 `CombatV02/`，两段攻击、囊弹、预警环及原 F6 蓝图的原生绑定均已实际保存；`Records/ue_combat_v02.json` 已包含 `runtime_binding` 阶段。详见 `Docs/Monsters/BellowSacLobberCombatV02_20261012.md`。未制作专用死亡动作，未加入大厅正式波次。未运行游戏、自测或预览渲染，动作的实际观感由用户体验确认。

当前抛射动作更新为 V03 管道蓄压版：根部到喷口逐段膨胀、出弹收缩并轻微回弹。制作源在 `NozzleV03/`，已导入 V03 动画／动作集并绑定原蓝图；1.2 秒发射时点不变。保存记录为 `Records/ue_nozzle_v03.json`，细节见 `Docs/Monsters/BellowSacLobberNozzlePressureV03_20261012.md`。未进行游戏测试或渲染。

V04 投射物表现制作源在 `PresentationV04/`：增加飞行接近预警、屏边方向箭头、落地引信圆弧、压力折射波、尘雾／碎滴和近场镜头脉冲。四份声音已实际导入，音源峰值 -2.5 dBFS、默认播放总增益 1.25，爆裂音近场半径 2.5 米。资产回执为 `PresentationV04/ue_assets_saved.json`，实现说明为 `Docs/Monsters/BellowSacPresentationV04_20261012.md`。V03 动作与战斗数值继续沿用；未试听或游戏测试。

V05 仅更新危险提示绘制：准星周围持续显示实心方向箭头，屏内囊弹显示大号实心符号、深底板与引信环。按水平朝向处理背后目标，合并同方向与重叠位置提示，图标主体不再随距离或脉动变淡。实现和接入记录见 Docs/UI/explosive-warning-v05-plan-20261012.md；沿用 V04 声音与爆裂资产，无新美术资源导入。未进行游戏测试。

V06 名称改为“鼓囊 M-09”，同步原生默认值、原蓝图、F6／图鉴共用列表和后续导入脚本。远程投掷改为两次起手之间 4 秒，包含原有 2.2 秒动作；取消囊弹接触地面后至爆炸前的引信蓄压声，保留飞行、落地撞击和爆裂声音。当前 V03 动作集继续使用。资产保存回执为 `Records/ue_tuning_v06.json`，详情见 `Docs/Monsters/BellowSacTuningV06_20261012.md`。未试听或游戏测试。

V07 预警圆环改为一次生成的 64 段场景贴合环带，排除单位与附件，断层或无支撑处不连面，并独立于囊弹旋转／缩放。复用原材质，原静态圆环网格只保留为制作历史与参数兼容，不再运行时绘制。实现与构建状态见 `Docs/Monsters/BellowSacWarningSurfaceV07_20261012.md`；未进行游戏测试。

V08 按非人形标准接入连续软体死亡：从当前姿势解除四肢和喷管支撑，原地下落、接地摊开。652 点／2,238 四面体代理按本模型制作，独立尸体网格、骨架、变形法线材质及数据已保存，并绑定到正式活体网格。制作源与实际保存回执在 `SoftDeathV08/`，说明见 `Docs/Monsters/BellowSacSoftDeathV08_20261012.md`。现有活体动作与投射物功能保留，未进行游戏测试。

V09 攻击伤害与有效攻击距离翻倍：囊弹 48、推击 24、最大投掷 28 m、推击 4.5 m。主动警戒 32 m，新增 36 m 敏感听觉与枪声直接警戒；单持和双持枪械均上报，普通怪物保持原听觉上限。最小投掷距离、4 秒间隔、引信和爆炸半径不变。声音覆盖检查发现本体事件尚未接入，补充优先级为警戒、蓄压吐弹、死亡，再补脚步与受击；本轮未新增音源或试听。回执为 `Records/audio_inventory_v09.json` 与 `Records/ue_senses_v09.json`，详情及构建状态见 `Docs/Monsters/BellowSacSensesAudioV09_20261012.md`。

V10 加入本体声音：两段警戒、1.2 秒蓄压、两段吐弹、两段死亡泄压及真实软体落地声，共八段。原料来源、CC0 页面、公开 HQ MP3 预览副本、PCM WAV 和实际 UE 保存回执保存在 `CreatureAudioV10/`；MP3 原料不作为无损母带。声音总增益 1.35，附着喷管的蓄压声随攻击打断/死亡停止，成功发射才响吐弹，首次发现目标才响警戒；落地引信声继续关闭。八份 SoundWave、三份并发资源及原 F6 蓝图已后台保存，制作与构建记录见 `Docs/Monsters/BellowSacCreatureAudioV10_20261012.md`。未试听或游戏测试，由用户体验。

V11 在 V10 上增量补充四段湿肉承重脚步与三段短促受击声。脚步从现有动画 GaitPhase 的四足落脚相位触发，随速度调整，结合移动组件支撑面定位；受击仅在非致命实际扣血后触发，0.42 秒限频，独立通道避免抢断警戒/蓄压。七份 SoundWave、两份并发资源和原 F6 蓝图已保存，保留 V10 音色及总增益。原料、制作和保存回执在 `StepsHurtV11/`，完整接入及构建状态见 `Docs/Monsters/BellowSacStepsHurtV11_20261012.md`。未试听或运行游戏，由用户测试。

V12 按用户确认部署到迎宾大厅和分流大厅：每厅首波额外加入 4 只鼓囊，一楼和二楼各 2 只，纳入同一主题区域的波次与清厅计数。正式蓝图／代码读取确认已接入 50% 移速游荡（40 cm/s），复用现有 V03 动作及 V11 脚步声。范围、落点和构建状态见 Docs/Monsters/BellowSacHallDeploymentV12_20261012.md；未运行游戏，由用户测试。
