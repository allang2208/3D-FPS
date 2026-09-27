# 裁片露指手套：共用动画、开口与皮革

2026-09-27，用户反馈当前 `TailoredFingerlessV1`「基本 ok」。这是用户反馈；本轮整理不新增穿模或游戏验收。通用换装合同见 [第一人称装备工作流](first-person-equipment-workflow.md)，图标规则见 [手套图标](../../ue5-item-asset-workflow/references/glove-inventory-icons.md)。

## 换手套不复制动作

第一人称手套是按原生手骨蒙皮的装备外观。`FPSModularOutfitComponent` 用 `SetLeaderPoseComponent(Source)` 跟随源视模，部件不运行第二套动画状态机或 Tick。单个 socket 只能带动刚体，不能代替手指、虎口和腕部蒙皮。新增款式按现有 profile 适配网格、参考姿态与权重，动画继续共用；同版型换色共享网格。只有确实改变接触包络的厚护板等款式才考虑按握持类别局部修正，不能每增加物品就重做全套动作。

当前家族有 22 套原生绑定，包含 Body、Bow 和左右单手；这个数量是本次范围，不是固定上限。保留骨长、局部轴和原生层级，不把 M4 绑定矩阵套给所有武器。

## 露指开口是配对几何

- 覆盖掌心、手背及虎口到指根，五指露出。皮革下的皮肤裁去，开口两侧使用同一裁切线、位置及插值权重；完整裸手叠一层壳容易穿出。
- 当前 `skin_meshes` 是裸露皮肤与皮革的组合网格，材质槽分别保留；`glove_in_base=true` 防止再显示第二份手套，`covers: []` 保留裸露区。全指黑色款继续使用其自己的覆盖合同。
- 皮肤与皮革一起生成 LOD。当前 `FingerlessGloveLeather` 槽触发 50%／35% 简化，保留边界和最多 8 权重；旧 20% 远景简化曾折坏窄指口。该比例属于本款经验，不能替代其他形状的判断。
- 展示／掉落空壳保留内衬、开口厚度；穿戴网格用与皮肤匹配的外层。不要把展示内衬直接叠进身体，也不要整体放大手套躲避局部穿插。

## 从橡胶感转为皮革

先修结构，再做表面。平滑膨胀与圆鼓衬垫缺少裁片逻辑，即使加颗粒仍像模压橡胶。本款采用虎口裁片、弧形手背接缝、短腕带、双缝线及局部受力褶皱；掌心握点和开口不整体外推。轮廓、裁片起伏和腕带用几何，细颗粒、缝线与磨亮变化用烘焙法线和粗糙度。

不要只不断提高粗糙度或法线强度。沿用有来源的皮革扫描，控制真实颗粒尺度、掌背差别和接触磨亮；皮革金属度为 0，不继承皮肤散射。法线必须与网格切线／UV 同一基准；BC5 采样不要当普通 RGB 高度数据解码，OpenGL 法线入 UE 按通道约定翻绿。

裁片款使用 2K BaseColor／Roughness／Normal 烘焙。只在有序拓扑对应时共享 UV；Body 和左单手局部封口分别烘焙，M1911_l 复用 DW715_l，最终共 3 组材质。顶点数量相同本身不能证明拓扑或 UV 可互换。

## 当前制作与恢复入口

正式入口为 `Tools/ModularOutfit/author_tailored_fingerless_family.py` → `save_tailored_fingerless_family.py` → `import_tailored_fingerless_family.py`。它们复用 `tailored_fingerless_candidate.py`、`build_tailored_fingerless_candidate.py`、`import_tailored_fingerless_candidate.py` 的作者、烘焙与导入函数；文件名有 candidate 不代表已经作废。

保留本机 `TailoredFingerlessCandidate` 的选定样件、贴图和图标场景，以及 `FingerlessHuntV2/FullShell`、`SkinCoverage` 与原生绑定输入。正式源为 `SourceAssets/ModularOutfit20260927/TailoredFingerlessV1`；UE 根为 `/Game/Characters/ModularOutfit20260924/TailoredFingerlessV1`。导入器保存全部 profile 与掉落件后才切换棕色配方；源散列回执支持中断续接。实际资产保存与仅生成脚本分别报告。

旧版指节、肩肘修复属于对已有动作缺陷的处理，不是每款手套都要重跑的步骤。短袖口缩放／腕部局部重分区试验未采用；不要为换皮革再次执行旧动画修复或旧家族发布脚本。

旧存档物品 `Data` 保存目录快照，换掉落网格仅改目录不足以刷新旧物品。本款在现有读档事务里仅同步 `ue_icon`、`world_mesh`、`world_material`，不改实例身份、强化或数值；配置由下次会话加载。当前棕色防御基础 2、强化增量 0.5，攻速／换弹各 10%；黑色仍为 4、1、各 5%，外观制作不擅自改平衡。

后台静态网格 LOD 保存中，commandlet 可能取不到现成 `StaticMeshEditorSubsystem`；本机导入器使用 `get_editor_subsystem(...) or new_object(...)` 完成保存。不要因此默认启动编辑器，也不要把此局部处理扩大到所有 subsystem。

来源与发布：Manny 派生表面、原生绑定、Quixel 扫描及其烘焙产物保留本机。公开代码、参数和恢复说明不等于授权公开原资源。废案按依赖分类并归档散列，保留重建仍需的旧源。
