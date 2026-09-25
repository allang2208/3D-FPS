# 暗纹猎弓 V9：整理、发布与恢复（2026-09-25）

当前 `bows.json` 选择 ContactV9 手模及八段动作，表现版本 9。已保存资产，实际游戏效果仍待用户确认；不能把本次仓库整理称为动作验收通过。本次未启动或重启编辑器、未运行游戏、截图或渲染。

## 保留与归档

175 个已退役文件（143,581,124 字节，约 136.93 MiB）移入本机 `trash/dark-bow-retired-v9-20260925/`：117 个制作文件／中间输出，58 个旧 UE 包。逐文件原路径、目标路径、字节数、SHA-256、理由和替代物见 [归档清单](../AssetArchives/dark-bow-retired-v9-20260925.json)。移动前确认范围和源散列，移动后读回散列。

UE 包通过现有编辑器的互斥 Python 桥检查无外部资产引用、无未保存修改，并卸载后归档；没有关闭编辑器或覆盖其他任务的资产。V2/V3 失效换装 profile 已移除。原包没有删除，需回溯时按清单从 trash 恢复。

| 保留位置（相对工程根） | 保留原因 |
| --- | --- |
| `Content/Weapons/DarkBow20260925/ContactV9` | 当前手模与 Idle、Ready、Equip、Nock、Draw、Hold、Release、Run |
| `Content/Weapons/DarkBow20260925/ArmsV4` | V9 共用的 Skeleton、参考网格与衣袖／手套；保留绑定复建及对照资产 |
| `Content/Weapons/DarkBow20260925/ArmsV2/SM_*` 与 `Materials` | 当前弓体、木箭、弓弦及箭材质；版本名较旧，但仍在使用 |
| 原 `SK_DarkBow` 与原始来源记录 | 保留原握把、材质和原始几何的来源依据 |
| `SourceAssets/DarkBow20260925/ContactV9` | 当前完整作者源、FBX、拟合输入、修补表面、接触参数及保存回执 |
| `SourceAssets/DarkBow20260925/ArmsV4` | 正确原生绑定的可编辑源、导入／装备制作配方及回执 |
| `SourceAssets/DarkBow20260925/ArmsV2` | Sparrow 轨迹、弓体表面、木箭作者源、静态件导入配方、绑定失败诊断数据和历史成功构建记录 |
| `SourceAssets/DarkBow20260925/GripV5` | 完整 VRE 抓握及原生空间转换输入；弓体拆分对照证据 |

ArmsV3、FramingV6、RightDrawV7、RightHandV8 的废案输出已归档；GripV5 只归档被替代的动作。V8 中 V9 仍需读取的坐标／姿态函数已独立保留为 `ContactV9/reference_hand_frame.py`，不再依赖退役目录或导出旧动作。

## 从本机资产恢复

恢复顺序为：原 dark bow 与皮肤／M4 压缩设置 → ArmsV2 静态部件及材质 → ArmsV4 Skeleton、参考手模及 Outfits → ContactV9 手模与八段动作 → `bows.json` 和 `modular_outfits.json`。

共享依赖包括 `Characters/ModularOutfit20260924/BarePalmV7` 的皮肤材质、原生装备来源，`Weapons/M4InfimaRigV4/BC_M4Viewmodel`，以及原 Fab dark bow 材质与贴图。仅恢复九个 V9 文件不足以还原完整武器。

当前配置保留 ArmsV4 原生 profile，新增 ContactV9 精确网格 profile，复用 ArmsV4 的装备。旧库存弓按 `bow_presentation_revision` 迁移表现，保留实例、强化、战斗参数与自定义换件；代码依赖本次一同发布的库存迁移及人物输入修正。

## 作者制作链

按 [作者源说明](../../SourceAssets/DarkBow20260925/README.md) 使用已有授权输入。静态件配方改为 `ArmsV2/import_parts.py`，只恢复弓体、箭和材质，不再生成已否定的 V2 手臂。

V9 顺序：Blender 运行 `read_hand_authoring.py` → Python（NumPy/SciPy）运行 `fit_hand_contact.py` → Blender 运行 `author_actions.py` → UE 后台或既有互斥桥执行 `import_assets.py`。这些是有资产写入的制作步骤，不在普通仓库整理时重跑。旧本机保存回执不能当作干净机器的导入结果；重新制作使用独立目标和新回执，先改好相应目的地。

本次仅整理配方和依赖，不重新导出／导入 V9。先前 V2 轮的常规 Editor 构建成功记录保留在本机 `ArmsV2/native_build_retry.log`；它不是本次精确暂存子集的重新构建结果。

## 公开发布范围

公开：弓原生代码、相关共享文件中的弓改动、配置、作者脚本、制作文档、技能和归档散列元数据。`SourceAssets/DarkBow20260925` 只放行 `.py/.ps1/.md`；既有已公开的尺寸／来源记录保留。

本机保留：原 Fab／Paragon／手模素材及派生网格、纹理、动画、Blend／FBX／UE 包，含表面或密集姿态的 JSON、接触拟合数据、导入回执、日志与 trash。项目已持有的使用许可不视为原资产公开再分发许可；Git 克隆不是完整可运行内容备份。

## 可复用规则与历史

手臂技能沉淀 [弓手型与弦接触](../../skills/ue5-fps-arms-animation/references/bow-hand-string-contact.md)：非零 EditBone 建骨顺序、原生绑定、完整掌骨抓握、实际蒙皮指腹接触、局部掌面修补、弦半径留缝以及双手构图。武器技能保留 [部件与运行合同](../../skills/ue5-weapon-workflow/references/first-person-bow-parts.md)。个人技能与仓库镜像同步。

历史制作记录保留用于追溯，已标明旧版或当前状态：[系列补齐 V2](dark-bow-actions-v2-20260925.md)、[绑定 V4](dark-bow-bind-fix-v4-20260925.md)、[握把 V5](dark-bow-grip-v5-20260925.md)、[构图 V6](dark-bow-framing-v6-20260925.md)、[右向拉弓 V7](dark-bow-right-draw-v7-20260925.md)、[右手 V8](dark-bow-right-hand-v8-20260925.md)、[掌面与接触 V9](dark-bow-palm-contact-v9-20260925.md)。

该系列仍缺弓臂受力形变、专用音效和图标、箭拾回、独立部件改造界面及第三人称动作；这些不属于本次已完成内容。
