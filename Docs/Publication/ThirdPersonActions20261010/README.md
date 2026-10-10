# 第三人称法杖、魔法书与消耗品动作：源码发布与恢复

本次发布来自 `D:/FPS3D/FPSGAME`，目标为 `allang2208/3D-FPS` 的 `main`。范围是本轮法杖抓握与整臂、空手出拳、持书及推击、饮用和进食适配。它是源码与制作配方发布，不能仅凭 Git 克隆还原完整可运行工程；已授权素材、UE 派生包和密集采样仍需从合法本机备份恢复。

## 当前使用的版本

动画公共前缀为 `/Game/Characters/JasonPlayer20261003/`，具体入口以 `Content/ColdSteelData/player_body.json` 为准。

| 入口 | 当前派生目录 | 恢复要点 |
| --- | --- | --- |
| 右手抓握、左手空闲手型 | 原生 C++ 抓握映射 | `FPSBodyStaffGrip.h` 复用当前第一人称握杖；`FPSUnarmedHandPose.h` 复用空手指型，手臂仍由第三人称动作控制 |
| `Unarmed.FullBody.PunchRight/Left` | `StaffPunch20261009/Animations` | KayKit 派生出拳；身体动画不执行玩法通知 |
| `Staff.NativeArm.Carry/CastGather/CastRelease` | `StaffCarryClearance20261010/Animations` | Motifect 供体适配 Jason 整臂，持握前移外展、留出整根杖杆的身体净空 |
| `Staff.FullBody.Strike` | `StaffStrikeCarry20261010/Animations` | 从当前持杖整臂出发，完整接回持握 |
| `Staff.FullBody.CastGather/CastRelease` | `StaffCast20261009/Animations` | 原生施法资产不可用时的 KayKit 回退 |
| `Staff.BookCarry` | `BookCarryRelax20261010/Animations` | 轻微步态叠加，保留书本支撑和局部手腕 |
| `Staff.BookPush` | `BookPush20261010/Animations` | 本地整臂推击，关闭该侧第一人称位置 IK 的重复驱动 |
| `Consume.Drink` | `WizardDrink20261010/Animations` | 已获用户“喝药没有问题”反馈，沿用饮用标记重定时 |
| `Consume.EatBread/EatBaguette` | `FoodNative20261010/Animations` | 以认可饮用手臂为参考、迁移第一人称进食相对轨迹；修复辅助骨循环覆盖上臂后，用户反馈“基本OK” |

金属手套配置只更新 Jason 项：`modular_outfits.json` → `items.ue_steel_gauntlets.rig_meshes.Jason`，指向 `StaffSurfaceRepair20261009/SK_Jason_SteelGauntlets`。其他骨架家族未改动。

法杖普通攻击调用与空手相同的体力计算入口。第三人称动画继续只负责表现，伤害、扣费、库存扣除及动作时钟由原玩法组件控制。

本次整理发现六组新片段通过 JSON 字符串引用，但没有独立 Cook 目录，已补入 `DefaultGame.ini`。出拳与回退施法的两组 Cook 配置一同发布。没有执行打包，不把配置补齐作为打包验收。

## 制作链与必须保留的本机数据

1. **供体骨架与回退动作**：`prepare_staff_combat20261009.py`、`prepare_staff_cast20261009.py` → 对应作者与保存工具。共用 `staff_arm_fit.py` 和 `SourceAssets/ThirdPersonSwordDonorRepair20261006/adapt_donor.py` 的骨架数学。后者导入时仍需原有 `ThirdPersonSwordActions20261006/authoring-input.json`、`ThirdPersonSwordDonorRepair20261006/retargeted-poses.json`、`original-poses.json`。这批上游输入保留本机，不能因目录名字带 Sword 而删除。
2. **当前持杖、施法**：`read_motifect_staff_sources20261010.py` → `author_motifect_staff_arm20261010.py` → `author_staff_carry_clearance20261010.py` → 对应 `save_*.py`。依赖 `ThirdPersonStaffCast20261009/donors.json`、Motifect `source-poses.json`、`ThirdPersonStaffSurfaceRepair20261009/FinalCheck/poses.json` 和 CarryClearance 的 `existing-scene.json`。最后一项保存实际法杖／书本挂接，不能用空场景代替。
3. **攻击与持书**：在上述当前 CarryClearance 制作源之上，分别运行 `author_staff_strike_carry20261010.py`、`author_book_carry_relax20261010.py`；推击再读取 BookCarryRelax 制作源。各自保存工具按实际配置键更新，并保留上游保存回执。
4. **饮用**：`read_wizard_drink20261010.py` → `prepare_wizard_drink20261010.py` → `author_wizard_drink20261010.py` → `save_wizard_drink20261010.py`。需要已导入的 Wizard 包、Jason 身体、V7 原生手型和 `SourceAssets/Consume20261006/contact-anatomy.json`。
5. **进食**：`author_food_native20261010.py` → `save_food_native20261010.py`。需要 Wizard 的 `authored.json`／`inputs.json`、原 `potion_use_motion.json`、Consume 的 `food-geometry.json`／`contact-anatomy.json`。`prepare_consume20261006.py` 与 `prepare_consume_contacts.py` 是上游读取／准备工具，不要用旧序列的保存工具覆盖当前 `Consume.*` 映射。
6. **手套与接触校准**：保留 SurfaceRepair 的 body／shirt／glove 输入、原 StaffCheck 姿态、FPS 法杖完整姿态／表面输入，以及 ThumbSteel 的 `original.json`／`production.json`／`steel-repaired.json`。当前源为 `author_staff_surface_repair20261009.py`、`save_staff_surface_repair20261009.py`、`fit_staff_contact20261009.py`。旧 Facing 的 `authored-grip.json` 仍供回退动作制作使用；保留其作者配方是为了恢复上游输入，不代表手工抓握表重新成为运行时标准。

保存工具会写资产或配置；诊断工具有的要求运行中的 PIE。只有按用户授权的具体制作／检查阶段才执行，不把这份依赖顺序当作自动批量运行脚本。`repair_food_upperarm20261010.py` 会写修复证据；一般读回请用只读的 `review_food_native20261010.py`。

## 来源与公开边界

- [Motifect 动画包](https://www.fab.com/listings/b775c780-309f-4cd9-a3f1-e50f7c912b37)及 [Wizard for Battle: PBR](https://www.fab.com/listings/a42813d8-92bd-4ee4-a3de-fd12f568ded2)由用户取得并导入；本次未确认它们可公开再分发。源包、几何、密集关键帧、派生动画及 UE 包均不进入 Git。
- KayKit Character Animations 1.1 随包 `License.txt` 标明 CC0；本次仍只提交项目自己的适配代码与配方。UAL2、Jason、V7、服装和装备的取得及恢复继续遵守各自已有来源记录。
- `FPSBodyStaffContactFit.h` 等只包含本项目的稀疏挂接／接触校准常量，不包含整段供体采样。公开清单见 [published-files.json](published-files.json)；清单记录本批变更文件，未重复列出 HEAD 已有依赖。
- `FPSBodySwordMotion.h`／`FPSBodySwordPose.inl` 是单手出拳、法杖攻击共用的现有库动作混合器依赖，因此一并发布。其他会话的独立剑术资产注册、步态、死亡、步枪和装备改动不随本次暂存。

## 归档与检查边界

确认退役的文件移动至本机 `trash/third-person-actions-retired-20261010/`；[archive-manifest.json](archive-manifest.json)逐项记录原路径、归档路径、大小、SHA-256、原因和替代物。移动后已逐项读回散列。`trash` 不推送；当前制作依赖和未能确认退役的文件继续保留。

此前按用户要求已读回两种食物的全部 342 根骨骼、145／163 帧，比较制作源、保存源和压缩数据，详见[进食记录](../../Characters/third-person-food-native-20261010.md)。本次仅做发布所需的文件归档、源码依赖、暂存差异与编译器语法检查。暂存候选和检查日志位于忽略目录 `Saved/ThirdPersonActionsPublication20261010/`；它们不是第二份开发工程，也不覆盖工作区并行修改。

公开快照的语法检查使用现有 UE 编译响应文件及生成元数据；只对行号宏作检查用映射，不生成或替换生产 DLL。历史必要构建成功、已保存资产和用户反馈分别保留原记录。本次未启动 UE、游戏、渲染或执行打包；移动、切装、中断和衣物最终画面仍不声明全部验收。
