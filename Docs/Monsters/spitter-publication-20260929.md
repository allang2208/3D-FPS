# 毒液僵尸整理与发布（2026-09-29）

发布宿主为 `D:/FPS3D/FPSGAME`，目标为 `https://github.com/allang2208/3D-FPS.git` 的 `main`。工作分支保留 `cursor/highland-blade-seat`，不切换或重置共享工作区。本次按 WORKFLOW 第 4、5、6、8 节进行归档和源码发布检查。

## 当前本机结果

- 保留原 Meshy 24 骨蒙皮、绿色感染材质与现有模型。F6 的“毒液僵尸”加载 `/Game/Monsters/SpitterZombie/BP_SpitterZombie`。
- 移动为 V10 Walk_A 与 V11 Walk_B/Walk_C/Run_A；出生时固定一种动作及匹配步速，停走不重抽。
- 普通攻击为 D、胖子抓击、女僵尸下挥，每次出手选择且不连续重复。每段保留独立命中窗口，基础范围 145 cm，实际命中上限 217.5 cm。
- 死亡接现有人形布娃娃，从当前姿态交接并继承有限运动，预算不足保留死亡动画回退。
- 每次实际造成伤害且目标存活的近战命中叠一层共用中毒。沿用状态免疫、净化、状态栏及减层规则。

MeleePoisonV15 的正式 DLL 后台构建已成功；V14 的三段攻击数组和范围/死亡资产保存已有回执。上述是制作阶段结果，本轮整理没有重新运行游戏、动画验收或性能测试。

## 废案与保留依据

987 文件、611.28 MiB 已归档到本机 `trash/spitter-zombie-retired-20260929`。原路径、目标、字节数、SHA-256、理由及替代物见 [逐文件归档清单](../AssetArchives/spitter-zombie-retired-20260929.json)。移前限制绝对路径范围，移后散列全部一致。

归档包括 V2–V6 自制吐毒、旧撕咬 V8（除共用参数脚本）、Attack_A V9、V7 被替代成品/安装器、旧蓝图快照、Blender 自动备份、过期日志副本、预览中间帧，以及近战转换后没有调用者的 `SpitterVenomProjectile.h/.cpp`。原始参考、已交付 GIF/联系表和历史量化报告保留；不删除未能证明没有引用的 UE 动画包。

以下旧目录仍有用途，不能作为废案整体移动：

- 根目录 `SpitterZombie_Animated.blend`：目标原蒙皮、Idle 与共用制作基底。
- `LibraryMotionV7`：Native FBX、native.json、采样/原骨长还原/导出助手、UE 重定向作者脚本。原 `Final` 和旧安装器已退役。
- `BiteV8/melee_settings.py`：总安装器仍使用其近战参数函数。
- `LocomotionV10`：Walk_A 正式源及导入单位修正函数；B/C/Run 的旧输出保留作 V11 历史测量的比较输入。
- `LibraryReview20260928`、`RigAudit20260928`：来源、许可、诊断与最终对照图；逐帧 PNG 中间输出已归档。

四个现行定向安装器的新备份出口改为 `trash/spitter-zombie-rollbacks/<revision>/Before`。总安装器跳过非动画 `MeleePoison` 块，重建器保留该玩法合同。

## 公开源码边界

公开现行作者/导入脚本、简洁 Meshy 请求参数、当前动作/战斗合同、恢复说明、归档索引和怪物 SKILL。模型、纹理、FBX/Blend、uasset、密集骨架/权重/姿态数据、生成回执、下载地址、构建日志及 trash 不公开。

**本次公共 Source 仍不包含完整毒液僵尸运行接入。** 本机父类、布娃娃与韧性接口尚有其他任务的未发布改动；不整文件发布这些混合修改。三份独立原生源和本次共享接点保存在 [运行交接补丁](PublicationSpitter20260929/spitter-runtime.patch)，依赖与逐文件散列见 [交接清单](PublicationSpitter20260929/runtime-handoff.json)。该补丁位于 Docs，不参加公共 UBT 构建；不能在当前完整宿主上重复应用，也不能声称克隆主线已恢复完整游戏。

共享接点仅包含 Nurse 的近战扩展点、Spitter 名称/数值/F6 注册，以及布娃娃对 `SpitterRoot` 的处理。未包含其他怪物改动、玻璃门修复、全局韧性/导航/武器开发内容。先完成共享接口独立发布，再在其上接入本补丁。

## 本机恢复与重建

1. 恢复合法原始输入：Meshy 模型/绑骨/PBR、参考图、共享 mutant 感染材质；项目已有 Mesh2Motion CC0 动作、ZombieAnimationPack 与 ZombieFemale/Nurse 包。Mesh2Motion 的 CC0 不覆盖其余资源，未核定再分发许可的输入均保留本机。
2. 恢复 `prepared`、`native_retarget`、原始/基础 Blend，以及 `LibraryMotionV7/Native`、V10/V11/V12/V13 的最终 FBX 和制作报告。本机原生接口按上述补丁依赖恢复后，执行必要常规构建。
3. 缺少作者输入时按 `prepare.py` → `author_surface.py` → `import_retarget.py` 建立基础。已有 Meshy 任务从本机回执恢复，不重新提交付费任务。
4. 保留基础反应；V7 重定向提供干净动作输入，V10/V11 负责当前四种移动，V12/V13 负责三种攻击。按根 [README](../../SourceAssets/SpitterZombieMeshy20260927/README.md) 选择最终安装入口。
5. `install_final.py` 使用当前合同导入/保存，`CombatDeathV14/install_combat.py` 可单独保存范围、布娃娃绑定和三段攻击池。中毒是原生行为，无需重复导入动画。

历史专项排查工具若要重做 V7 前后对比，应先从归档恢复相应旧成品到隔离输入位置；不要用旧安装器覆盖正式蓝图。默认后台制作与保存；是否运行游戏仍由用户决定。

本轮发布检查范围为精确暂存差异、文本/脚本、大小、敏感信息、许可边界、归档散列和远端 SHA。发布回执写入本机 `Saved/spitter-publication-20260929`。
