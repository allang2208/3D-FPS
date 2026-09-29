# 毒液僵尸：当前制作与恢复入口

当前为 V10/V11 固定步态、V12/V13 三种随机近战、V14 范围与死亡布娃娃、V15 命中叠毒。正式 DLL 已后台构建，现有 BP/动画已保存；未做最新游戏验收。每次有效近战命中增加一层共用中毒。

运行资产：`/Game/Monsters/SpitterZombie/BP_SpitterZombie`。Meshy 网格/原蒙皮与 mutant 配方绿色材质保留。移动出生时抽一次并固定对应步速；攻击每次进入状态选择 D/胖子抓击/女僵尸下挥，不连续重复。每次攻击最多结算一次。

| 用途 | 当前作者源 | 接入 |
| --- | --- | --- |
| 原始模型、材质、基础反应 | `prepare.py`、`author_surface.py`、`import_retarget.py`、`author_animation.py` | `install_final.py` |
| Walk_A | `LocomotionV10/author_locomotion.py` | 首次恢复后继续安装 V11 |
| Walk_B、Walk_C、Run_A | `LocomotionV11/author_locomotion.py` | `LocomotionV11/install_locomotion.py` |
| D 踏步挥抓 | `AttackD_V12/author_attack_d.py` | `AttackD_V12/install_attack_d.py` |
| 两种供体近战 | `AttackVariantsV13/retarget_attacks.py`、`author_variants.py` | `AttackVariantsV13/install_attacks.py` |
| 145 cm 基础范围、布娃娃绑定、三段池 | `CombatDeathV14/settings.json` | `CombatDeathV14/install_combat.py` |
| 近战叠毒 | `ASpitterZombie::ApplyMeleeDamage` | 正式原生 DLL；无需资产重导 |

总安装器按 `animation_contract.json` 的当前引用恢复。局部旧版安装器不能覆盖较新合同：V10 单独恢复后仍需 V11；V12 单独恢复后仍需 V13/V14。当前原生接口已在完整本机工程接入，公共仓库仅保留待共享接口发布后应用的运行补丁，详见 [整理与发布](../../Docs/Monsters/spitter-publication-20260929.md)。

保留 `SpitterZombie_Meshy_Source.blend`、`SpitterZombie_Animated.blend`、`prepared`、`native_retarget`、`LibraryMotionV7/Native` 和原始 Meshy 回执。V10/V11/V12/V13 仍调用 V7 采样助手，`BiteV8/melee_settings.py` 仍是总安装器依赖；不能按旧版本名整体归档。V2–V6、旧撕咬、Attack_A、V7 旧成品与备份已移入 `trash/spitter-zombie-retired-20260929`。

`MeleePoisonV15/build-result.json` 为最近一次成功构建回执；`CombatDeathV14/installation.json` 为范围和三段池保存回执。回执及许可证原件留本机；代码/脚本不替代模型、源动作、纹理和 UE 包。来源和完整恢复顺序见上述发布说明，历史过程见 `Docs/Monsters/SpitterZombieMeshy20260927.md`。

Meshy 密钥只从环境变量或隐藏输入读取，不存入工程；已有任务先用本机回执恢复，不重复付费提交。
