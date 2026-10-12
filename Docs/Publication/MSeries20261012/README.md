# M 系列、鼓囊与大厅遭遇阶段收尾

开发日期 2026-10-12，收尾跨至 2026-10-13。按用户授权核对本阶段源码、保存回执与构建记录，整理废案、更新 SKILL 并发布到 `allang2208/3D-FPS` 的 `main`。本阶段开发和接入已完成；游戏、音频和楼梯画面尚待用户测试，未将构建成功写成实机验收。

## 当前交付

- 两厅各两波普通职员，每波 12～15；每厅首波额外 4 只鼓囊（上下层各 2），首波实际击杀严格过半后从检修门生成第二波。两厅作为共同区域，入场落下三个推进出口铁栅门，所有名额实际死亡后统一放行。生成失败不计击杀。
- 未发现玩家时半速游荡；主动发现与首次受击延迟 1～2 秒后的发现共用局部群体预警，同伴不转播。鼓囊为枪声敏感物种，普通怪物保留原听觉限制。
- 鼓囊正式蓝图、原骨架待机/移动、管道蓄压动作、投射物、连续软体死亡及事件声音已保存。攻击起手间隔 4 秒，囊弹伤害 48、推击 24、投掷上限 28 m、主动警戒 32 m、听觉 36 m。
- 爆炸物采用屏边方位箭头、红边脉冲与屏内位置提示；圆环独立于弹体旋转并分段贴场景。落地引信声、怪物吸气蓄力声保持关闭。
- 本阶段 12 类 M 系列角色的活体接地源码已接入；双足、根足、多触肢按真实骨链适配，补齐缚群身体承重与伏窥者着地攻击覆盖。详细清单见 [接地制作记录](../../Monsters/m-series-grounding-implementation-20261012.md)。

最初二楼远程怪物概念中另一个候选未获选进入制作，当前正式交付为鼓囊；设计文档作为候选记录保留，不计入已实现怪物。

## 本机资产与重建

正式资产根为 `/Game/Monsters/BellowSacLobber`，F6 与大厅引用同一 `BP_BellowSacLobber`。本轮磁盘含 51 个 uasset；读取保存回执确认 V02 包含 `runtime_binding`，V08 软体安装完成，V10/V11 声音与蓝图保存完成，V14 回执确认 `Charge` 已移除。这是保存和磁盘状态，不是本轮重新运行效果。

保留用户原件副本 `SourceAssets/BellowSacLobberMeshy20261012/Source/BellowSacLobber_user_rig.glb`，SHA-256 `fe79c141f2cf6239123efff094e39732f7d830c5321f495224097b79881cc552`，以及 Authoring、Exports、Textures 和所有仍供重建的版本目录。原始三视图及生成提示保留在 `SourceAssets/BellowSacLobberConcept20261012`。

恢复次序：

1. `prepare_source.py`、`author_locomotion.py`，随后 `import_mesh_headless.py`、`import_motion_headless.py`。
2. `author_attack_v02.py`、`import_combat_assets_v02.py`、`install_combat_v02_headless.py`；接着 `author_nozzle_pressure_v03.py`、`import_nozzle_pressure_v03.py`。V02 仍为 V03 的输入，不得整目录删除。
3. `author_presentation_audio_v04.py`、`import_presentation_v04.py`、`apply_tuning_v06.py`。
4. `prepare_soft_death_v08.py`、`author_soft_death_v08.py`、`install_soft_death_v08.py`，依赖既有 `Tools/MonsterSoftCorpse/author_cages.py` 及本机软体导出/绑定数据。
5. `apply_senses_v09.py`、`author_creature_audio_v10.py`、`import_creature_audio_v10.py`、`author_steps_hurt_v11.py`、`import_steps_hurt_v11.py`、必要时 `finalize_steps_hurt_v11.py`，最后 `disable_charge_audio_v14.py` 保持用户禁用项。V10 导入脚本自身也排除 Charge。
6. 构建原生 Editor/Game。V07 场景环带、V12 大厅分层、V13 屏边预警、V15 及全体接地由正式原生代码接入。

实际调用仍遵守当前后台/编辑器批次互斥规则；本收尾没有执行重建、重导入或打开编辑器。音频原料依赖 `CreatureAudioV10/Sources` 和本机 M10/M14 的已有声音源；HQ MP3 预览不等于原始无损母带，来源和 CC0 声明保留在各 `audio_manifest.json`、源页面及 README 中。

## 公开范围与共享文件

公开原生源码、原创制作/导入脚本、生成提示、说明、归档散列与适用 SKILL。没有复制 GitHub 第三方实现；此前开源检索用于方案参考。Meshy 输入及派生模型、贴图、音频、源网页、密集骨骼/几何/绑定数据、uasset、构建产物、日志和 trash 不公开提交；本轮不扩张其再分发许可。

共享角色、HUD、FX、地牢生成器和打包配置按本阶段相关部分暂存，保留工作区中的其他任务修改。源代码发布保留旧自动刷怪/推进门的停用入口，避免与大厅专用遭遇同时启动；旧类兼容空壳的其他整理不在本次范围。未混入 APS 寻路迁移、热成像、玻璃弹痕、资源条、Super90 预测射击或地牢生成性能流水线。

公共源码切片依赖仓库原有实现；必要原始资源仍须按本节和 [AssetSetup](../../AssetSetup.md) 在完整工程恢复。现有构建证据来自完整本机工程，未在纯 Git 克隆中重建，不宣称源码克隆即可直接运行全部内容。

## 归档与技能沉淀

56 份已完成阶段的回退快照和一次性编辑器关闭/导入恢复脚本，合计 828,800 字节，移入 `trash/m-series-closeout-20261012/`。每个源路径、目标、大小、SHA-256、原因和替代物记录在 [retired-files.json](retired-files.json)，移动后散列读回一致。没有仅凭旧版本号移动制作源，也未从 Content 搬走尚未完成引用核对的历史包。

新增 `ue5-monster-workflow/references/bellow-sac-lobber.md`，在 `m-series-locomotion.md` 沉淀活体逐足采样/身体承重/原始姿态快照，在 `monster-ai.md` 沉淀半速游荡、延迟受击发现与非递归预警。个人维护源与工程参考同步；工程入口已有的本机维护源迁移仍保留，不纳入本次无关改动。

## 完成核对与发布检查

- 最新接地 Editor 构建：`Saved/MSeriesGrounding20261012/Editor-build-attempt2.log`，`Result: Succeeded`，9.74 秒。
- 最新接地 Game 构建：`Saved/MSeriesGrounding20261012/Game-build.log`，`Result: Succeeded`，26.11 秒。
- 资产保存与静音回执仍保留在 SourceAssets 的 Records/V08/V10/V11，以及 `Saved/BellowMuteCharge20261012/asset-receipt.json`；此前构建日志保留原位，Before 快照已按归档清单迁移。
- 本次执行用户要求的阶段完成、归档及推送检查，包括精确暂存差异、空白错误、文件大小、敏感信息和素材边界；没有追加游戏、渲染、试听、性能或网络验收。
- 仅普通非强制推送 `HEAD:main`，完成后以 `git ls-remote` 回读远端 SHA。提交号由最终交付消息和本机发布回执记录，避免在提交内部自引用。
