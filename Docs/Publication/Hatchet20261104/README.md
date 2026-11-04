# 战斧模型、改造与重击修复发布（2026-11-04）

本批整理本对话的战斧模型、改造、符文、图标及联机重击修复。遵循根目录 WORKFLOW 第 4、6、8 节和武器 Skill 的 publication 规则；使用临时索引，不提交共享索引中的其他任务内容，不改写实际工作文件为裁剪版本。

## 当前生产源与归档

- 原厂、拆分三槽：`SourceAssets/OneHandAxe20261101/` 与 `ModulesV1/`。
- 钩月：`BladeVariants20261102/CrescentReferenceR4_20261104/`，使用 `FactoryFinish20261104/` 的原厂同源材质。
- 厚背重劈、百炼弧锋与三张通用改造图标：`BladeVariants20261102/ContinuousBladesR5_20261104/`。
- 专属隼喙斧刃：`FalconEdge20261103/`；长柄：`LongGrip20261103/`；破阵镂空握柄：`AgileGrip20261103/HollowV2/`。破阵数值以父目录当前 design.json 和正式改造目录为准。
- 通用挂坠：`Pendants20261102/FitV2/`；通用斧面符文：`CommonRunes20261104/`。
- 装备栏／背包画布修正：`IconCanvas20261102/`；不以改造件灰阶金属框图代替整武器 PBR 目录图。

179 个已否决或被替代的文件、826986462 字节，已可恢复地移动至本机 `trash/HatchetPublication20261104/`，移动前后逐文件比对大小与 SHA-256。精确位置、理由和保留替代物见 [cleanup-manifest.json](cleanup-manifest.json)。不是删除或回收磁盘空间。

当前 R5 仍使用 R2 author.py 的轮廓函数；R4 FactoryFinish 的 Before/author.py、原始几何和纹理仍是生产输入；镂空握柄仍使用 V1 母版和 Before/agile_grip.json，均保留。关键失败对照、最终记录、原始 GLB、实际 Content 和他人正在制作的 GhostScythe／HatchetPairs 未归档。

## 本次进入主树的内容

1. 重击起手使用受限的同步服务器时间；补齐规定蓄力时长中尚未扣费的部分，保持原有门槛、释放窗口和取消语义。只提交 `KukriHeavy.cpp` 与头文件中属于本次计时／诊断的改动，保留远端基线已有的装备选择路径。
2. `ModularSwordVisual.cpp` 的战斧目录回退和动态挂坠路径；不混入其他武器材质、附魔和握柄适配改动。
3. 战斧导入辅助类、独立物品／改造／模块／通用斧刃目录与 Cook 路径；作者脚本、参数、来源记录和可复用的显式检查工具。
4. 武器、联机、调试 Skill 的本轮新增段落。个人维护源与工程对应新增内容一致；已有其他任务的文档差异不随本次提交。

完整精确清单见 [source-manifest.json](source-manifest.json)，发布检查见 [publication-checks.json](publication-checks.json)。本仓库仍为源码／配方交付，**不包含本机完整可运行 Content**。二进制模型、图像、音频、字体和 UE 资产没有新增再分发授权，保留本机及既有备份；恢复清单见 [asset-dependencies.json](asset-dependencies.json)。

## 共享代码的接入边界

远端 `d7bea973` 没有同时具备本机的 `ActiveKukriWeapon`、`OneHandedMeleeArt`、`IsOneHandedMelee`、成对重击 RPC 和部分命中回执 API。它已存在相关调用与声明不齐的发布依赖，不能为了把本批打包成完整游戏而夹带其他任务全部未提交实现。

因此，本轮修改的联机夹具、专项命令行检查、图标画布策略以 [Integration](Integration) 中的精确补丁保留；**这些补丁尚未作为对应 Source 文件合入 main，不能将其称为公开主线已具备的完整运行功能**。依赖与宿主源散列见 [integration-prerequisites.json](integration-prerequisites.json)。本机实现、资产及此前编译产物保持原样。

作者配方中的共享刀类选项、模块工具、裸手骨架和材质母版仍需要项目现有依赖。新武器目录和制作脚本的提交不等于整套主副手、命中公式和 UI 分类消费者都已独立公开构建。后续应随这些共享层的所属批次接通，不回写本批索引裁剪内容到工作区。

## 已有检查证据

详细经过见 [本机检查记录](../../../Tools/HatchetAudit20261104/README.md)，摘要和原始结果散列见 [validation-evidence.json](validation-evidence.json)。

- 修复前，400 ms 起手延迟、随后恢复 60 ms 的真实 UDP 条件使四次重击全部失败；拥有者必需动画已加载，服务端只计得约 1.65 秒。
- 修复后，同条件专用服 7 个场景、常规监听主机 14 个场景及 53 项确定性检查通过。专用服正常保持第一人称动画未加载。
- 这些是完整本机混合工作区的历史构建／运行证据，不是本次裁剪源码提交独立构建或重新测试的结果。本次仅执行用户要求的整理、内容与推送检查；未启动 UE、未重新编译、未运行游戏或画面验收。

本批只使用普通非强制推送；共享索引其他内容保持，远端提交号由推送后回读确认。
