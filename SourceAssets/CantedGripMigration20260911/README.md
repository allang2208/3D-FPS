# M4 45° 握把修正与 AKM 握把迁移

2026-09-11 完成本机接入与回归。本次修正 M4 45° 侧倾握把的手臂轴向扭转、并指和拇指对握，并把 M4 四种握把的抓握方式适配到 AKM。新的视觉效果等待用户审阅，不把自动检查通过写成用户确认。

## 直接查看

- [M4 修改前后，同视角源模型渲染](Delivery/M4_Before_After.png)
- [M4 / AKM 45° 实机腕肘及手背](Delivery/M4_AKM_Canted.png)
- [AKM 四种握把实机掌侧](Delivery/AKM_Grips.png)
- 实机视频：[M4 45°](Delivery/m4_canted.mp4)、[AKM 45°](Delivery/akm_canted.mp4)、[垂直](Delivery/akm_vertical.mp4)、[棱镜](Delivery/akm_prism.mp4)、[共振](Delivery/akm_angled.mp4)。每段含待机、近景、瞄准及普通/空仓、弹匣/弹鼓四种换弹；时间间隔来自截图日志。视频静音，只用于视觉检查。

## 可编辑源

| 动作族 | 汇总 Blend（每套九条 Action） | 单动作 Blend / FBX |
| --- | --- | --- |
| M4 45° | [M4_canted_Family_Editable.blend](m4/canted/M4_canted_Family_Editable.blend) | `m4/canted/A_M4_Canted_*` |
| AKM 45° | [AKM_canted_Family_Editable.blend](akm/canted/AKM_canted_Family_Editable.blend) | `akm/canted/A_AKM_canted_*` |
| AKM 垂直 | [AKM_vertical_Family_Editable.blend](akm/vertical/AKM_vertical_Family_Editable.blend) | `akm/vertical/A_AKM_vertical_*` |
| AKM 棱镜 | [AKM_prism_Family_Editable.blend](akm/prism/AKM_prism_Family_Editable.blend) | `akm/prism/A_AKM_prism_*` |
| AKM 共振 | [AKM_angled_Family_Editable.blend](akm/angled/AKM_angled_Family_Editable.blend) | `akm/angled/A_AKM_angled_*` |

九条分别为 idle、aim、fire、aim_fire、equip、reload、reload_empty、drum_reload、drum_reload_empty。使用 Blender 5.1.2。汇总文件可切换 Action；弹匣与弹鼓预览可见性已在各自单动作 Blend 中配置。精确输出散列见 [delivery_manifest.json](delivery_manifest.json)。

## 最终实现与复现入口

M4 的整臂参照原始 M4 的肘部弯曲平面与上臂方向，保留骨长、rest、蒙皮和手指局部平移。沿整条肩肘腕链调整支撑与前臂扭转，再有限调整各指屈伸。最终静态源是 `Canted_Refit.blend` / `canted_refit.json`，退握源是 `release_final.json`。无名指与小指只在松手阶段增加约 4° 的分离修正，避免稳定姿态正确但退握时相互穿过。小指围拢短握把底端；不宣称所有指尖都在 1 mm 内贴面。

AKM 复用 M4 的手部包握关系，并按 AKM 肩位和护木安装座重新解算手臂、脱离和回握。45° 安装座改为短导轨；共振握把保留三指穿孔、拇指和小指在外，安装座降低 32 mm，并采用后侧支撑避免顶住原换弹手势。尺寸与支撑位置是本案例结果，不能跨枪直接套用。

按顺序复现；先恢复下方本机依赖，运行前确认没有覆盖正在编辑的资产：

1. `python prepare_canted_final.py` 整理已定稿参数；Blender 运行 `build_canted.py` 烘焙 M4 九条。
2. Blender 运行 `prepare_akm.py`，再分别运行 `build_akm.py -- canted`、`vertical`、`prism`、`angled`。
3. Blender 运行 `validate_m4.py`，及 `check_geometry.py -- m4 canted` / `-- akm <类型>`。`compare_source_self.py` 比对原源已有指间接触。
4. UE Python 运行 `import_assets.py`、`verify_assets.py`；`export_pose_reference.py` 与 `verify_pose_reference.py` 交叉比对 Blender 源与 UE 压缩后骨位形状。
5. 编译原生模块后，`run_final.ps1` 启动独立配置的游戏进程完成七组回归。`assemble_editable.py` 汇总 Action，`make_delivery.py` 整理预览和报告。

Blender 命令使用 `-b -t 5 --python-exit-code 1 --python <脚本>`；AKM 类型在末尾 `--` 后传入。不要仅因 Blender 进程退出而判定 Python 成功。目录中其余 `fit`、`probe`、`search`、旧 `final` 试验及对应日志保留为本机诊断历史，不是生产入口。冻结的共用辅助脚本在 `ReferenceWorkflow/`，来源及散列见其 `hashes.json`。

## 动作与数值合同

M4 非目标侧、枪根、机械轨道和换弹接触段沿用原源。普通/空仓时长为 2.1 / 2.7 s；基础/普通换弹/弹鼓分别以 120 / 480 / 240 Hz 烘焙。原动作关键时间以 `m4/canted/animation_build.json` 为准。

AKM 以原生 120 Hz 动作为源，普通/空仓换弹 3.333333 / 4.291667 s 不变。普通换弹第 42–270 帧、空仓第 42–380 帧的原接触段保留；330 / 440 帧恢复配件握姿。取弹、装入、枪机、右手及弹鼓甩出轨道保持。没有改音效或重新编排声轨。

枪匠补入 AKM 垂直与 45° 两个选项；核验 M4 的 16 个配件选项在 AKM 中 `stats` 与 `effects` 一致，见 [catalog_parity.json](catalog_parity.json)。原本一致的数值保持；四种握把都沿用 M4 的空数值加成。保留 AKM 的基础伤害、射速、7.62 弹药、30 发弹匣、50 发弹鼓和弹鼓换弹加时规则。

## 验收与边界

[acceptance.json](acceptance.json) 记录最终结果：原生模块 2026096228 编译成功，45/45 个 UE 动画读回通过，五组游戏及两组枪匠 UI 检查全部通过。运行检查包含按帧重复检查；3635 个 PASS 日志条目不是 3635 个独立场景。

4159 个实际蒙皮手指/握把采样无交叉。387 个指间相交采样时刻也存在于保留的原换弹源，没有新增独有时刻；这不是原换弹动画完全零自交的声明，也不覆盖整个手臂/整枪的连续时间碰撞。已人工查看实机第一人称、掌侧、手背、腕肘、枪匠界面及换弹接触图。

导入和读回脚本 PASS，但 commandlet 退出码 1 包含项目原有 GameFeatureData AssetManager 配置问题及 HTTP 8000 占用。七组新游戏进程均退出 0。RAW 读回关闭额外 retarget，COMPRESSED 使用运行时 retarget；不得将两种不同的求值空间差异误判为压缩损坏。额外高精度压缩试验已撤回，最终仍用 BC_M4Viewmodel。

已打开的旧 UE 编辑器可能仍载入旧模块。保存其工作后重启编辑器即可使用新模块；本次验证来自新进程，未关闭其他任务正在使用的编辑器。

## 本机资产与源码发布边界

实际引用：M4 `/Game/Weapons/M4CantedErgonomic`；AKM `/Game/Weapons/AKMIntegration/SovietFab/GripErgonomic/{canted,vertical,prism,angled}`。新静态资源为同目录 `SM_AKM_canted_CompactMount`、`SM_AKM_vertical`、`SM_AKM_angled`；棱镜仍使用既有 Attachments 资源。旧 `SM_AKM_canted` 和 `BC_AKM_GripPrecision` 为未引用的本机试验，不用于恢复正式状态。

需恢复当前 M4/Manny 手模及材质、Soviet Fab AKM、既有握把和瞄具、`AKMAttachments20260911`、`AKMReloadPolish20260911/base`、`VerticalGripErgonomic20260911`、`AngledForegrip20260910/WristNatural` 及 `M4ContactImpact/M4WrapGrip/M4TacticalToss/M4SlapImpact/M4DrumContact` 各日期源目录。完整原始骨骼采样、拟合矩阵、Blend、FBX、uasset 和图片留在本机，来源许可沿用 [AssetSetup](../../Docs/AssetSetup.md)，本次不新增外部模型或公开再分发权。

共享工程的 AKM 前置框架和角色文件含其他任务未提交内容。本次公开作者代码、验收摘要、技能和 [精确集成增量](Integration/runtime.patch)，不把这些混合文件整体暂存。增量针对本机 `Baseline` 而非公开 HEAD；需要完整 AKM 前置框架，不能将它当成独立可编译的 AKM 源码发布。patch 为零上下文记录，检查或应用需 `git apply --unidiff-zero` 并先核对基线散列；当前宿主已应用，不要重复应用。当前宿主实际源码已接入并完成上述回归。散列边界见 [Integration/manifest.json](Integration/manifest.json)。
