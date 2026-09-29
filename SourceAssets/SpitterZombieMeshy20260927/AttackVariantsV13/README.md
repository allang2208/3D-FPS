# 毒液僵尸随机近战池 V13（2026-09-29）

**后续修订：** V14 将基础范围统一为 145 cm，V15 为三种近战有效命中追加一层共用中毒。下文“不增加中毒”等表述是当时制作范围；当前以根 README 和 MeleePoisonV15 为准。旧 Before 快照已归档到 trash。

用户要求参考胖子僵尸、女僵尸的攻击，为毒液僵尸新增随机攻击姿势。保留 D，新加胖子的右手抓击和女僵尸的左臂下挥。每次进入攻击状态独立抽取，本次攻击中不重抽；存在其他有效动作时不连续重复上一个动作。四种移动依旧在生成时选定并固定，移动动作及步速不修改。

## 动作与时序

| 片段 | 当前实际来源 | 长度 | 命中窗口 |
| --- | --- | ---: | ---: |
| D 踏步挥抓 | 现有 `A_Spitter_AttackD_V12` | 2.00 秒 | 0.47–0.67 秒 |
| 胖子右手抓击 | `/Game/Monsters/FatZombieMeshy/Animations/A_FatZombie_Attack` | 2.0833 秒 | 0.65–0.78 秒 |
| 女僵尸转体下挥 | `/Game/Monsters/NurseZombie/A_Nurse_attack` | 3.3333 秒 | 1.40–1.70 秒 |

三段都是完整原速、单次播放，每次攻击至多命中一次；结束后冷却统一保留毒液僵尸的 0.35 秒。保留原伤害、范围、遮挡、朝向、弹反及打断逻辑，不复用胖子的伤害/攻击距离，也不增加投射物或中毒。

来源资料：实际 CDO 的模型、攻击与时序记录在 `native.json`；制作前查看了已有女僵尸攻击接触表及 Mesh2Motion 抓击参考图。胖子动作源为工程中的 Mesh2Motion CC0 派生片段；女僵尸属于用户已导入的 ZombieFemale 包，本次仅本机复用，不作公开再分发授权声明。

## 体型适配

使用独立 UE IK Rig/Retargeter 将两种当前运行攻击重定向到毒液僵尸，保留原始输入；随后按现有 Meshy 绑定骨长和蒙皮应用 V12 的足底支撑、轻微屈肘、收势跟随和部分向前凝视修正。各自沿用源攻击的手臂侧别、蓄力及落势，并按各自命中窗口安排跟随修正。接入只导入动画，不更换绿色材质、模型、骨架或权重。无独立手指/眼球动画。

## 源码与制作入口

- `retarget_attacks.py`：从胖子原生 CDO、女僵尸现有蓝图读取输入，在毒液僵尸目录制作重定向资产并导出。
- `author_variants.py`：Blender 后台适配；产物为两份可编辑 `.blend` 和 `Final/A_Spitter_AttackV13_*.fbx`。
- `install_clips.py`：只保存两条动画，适用于编辑器仍加载旧原生 DLL 的阶段，不代表随机池已生效。
- `install_attacks.py`：正式模块加载后保存三项 `AttackVariants` 及现有蓝图。
- `Source/FPSGAME/Monsters/SpitterZombie.h/.cpp`：新增含 Clip、ContactTime、ContactEnd、RecoveryTime 的配置项；在现有攻击入口一次性随机并切换父类近战时钟读取的字段。无新 Tick、定时器或运行时资源加载。
- 配置数组追加到原类成员尾部；普通完整依赖构建，不用 `NoUBTMakefiles` 或临时 DLL 后缀。

首次构建遇到 `Dungeons/WardBreakableGlass.h` 的 `Building/ColdSteelDoor.h` 路径错误，已仅修正为 `../Building/ColdSteelDoor.h`，未修改玻璃门逻辑。该次毒液僵尸源码编译已完成，但不能把失败的模块构建视为交付。

## 当前落盘状态

两条新动画已由现有编辑器桥导入并保存，见 `installation_clips.json`。**后续 V14 已完成正式 DLL 构建与三项蓝图数组绑定**；完成回执见 `../CombatDeathV14/build-result.json` 和 `../CombatDeathV14/installation.json`（`attack_pool_bound=true`）。本目录旧 `build-result.json` 保留首次失败记录，不能代表后续完成状态。当前基础攻击范围由 V14 统一调整为 145 cm。

未运行测试、游戏、预览渲染或验收，由用户试玩确认。未改胖子/女僵尸原资产，也未主动打开、关闭或重启编辑器。
