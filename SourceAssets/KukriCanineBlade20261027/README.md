# 犬牙刀身 — 2026-10-27

尼泊尔弯刀专属特殊改造，选项 `canine_blade`，刀身槽 `blade_1`。保留原有刀身长度、刀尖和握柄接口，在实际刃口制作连续犬牙锯齿。

## 数值与流血

- 物理伤害+20%：`physical_damage_mult = 1.20`。
- 韧性伤害−50%：`toughness_damage_mult = 0.50`。
- 本刀每次攻击命中敌人叠加1层流血：`melee_hit_bleed_stacks = 1`。

流血复用 `UCombatStatusFormula::AddBleeding`。每秒按目标当前生命值的1%×层数结算，现有实现向下取整且最低1点；新增层数刷新10秒衰减计时，此后每10秒减少1层，保持既有免疫、状态显示与复制机制。

后续修复：流血生命值读取已改为怪物通用 `GetVitals` 接口，修复后续怪物被读取为 0 而跳过扣血的问题；接触入口改用 `AddBleedingHit` 记录伤口位置，并增加命中及跳伤时的红色粒子喷发。源码、材质制作与构建记录见 `../BleedingFixBurst20261027/README.md`。

触发入口为 `UColdSteelStatusModel::ApplySkillWeaponHit` 的权威近战接触结算。该次出手从实际武器的 `ColdSteelSkills::Snapshot` 捕获层数，服务器根据本次命中申报对应的已装备实例重建同一快照。主手、副手、普攻、重击、上挑、旋风、冲刺和快速近战沿用各自命中去重；同一刀同一攻击窗口对同一目标只加一层。护甲减伤不取消已成立的接触，尸体、场景、友方、免疫目标和流血自身跳伤不会由此继续叠层。双持两刀各自命中时独立触发。

常驻数值写入 `effects` 与 `stats`；触发规则写入 `special_effects`，供改造详情和物品浮窗共用。

## 制作来源

- 基础模型：`KukriBladeSurfaceV220261026/Kukri_Blade_SurfaceV2_Editable.blend` 的百炼均衡刃。
- `serrate_mesh.py` 沿齿峰/齿谷截面局部重分面，插值保留 UV、顶点色和面角法线；冻结6.6 cm以下接口。
- 12个实体齿口，间距1.2 cm、深度0.38 cm。保持原有长度，不继承猎手刀身的长度或攻击距离加成。
- 可编辑母版：`Kukri_Canine_Editable.blend`；游戏网格：`Export/SM_Kukri_Blade_Canine.fbx`。
- 独立2048 BaseColor、ORM及切线空间法线贴图；UE导入翻转法线绿色通道。
- 三款符文按新网格单独烘焙遮罩，保留原有比例和浮雕材质。
- 图标由内置 image_gen 单独生成。实际模型参考 `Icons/Canine_Model_Reference.png`，钢框样式沿用猎手刀身图标；提示保存在 `Icons/generation-prompt.txt`，成图为 `Icons/ue_kukri_blade_1_canine_blade.png`。
- 图标生成原件：`C:/Users/allan/.codex/generated_images/01a17715-3312-74c2-a3a3-318b877cf0ca/exec-71820469-adc5-4120-9a4d-036c296eb8ea.png`。

## 接入记录

必要构建记录见 `build-editor.log`，实际导入保存见 `import-receipt.json`，目录部署见 `publication-receipt.json`。修改前的目录文件保存在 `Before/`。未运行游戏、联机测试或验收，由用户测试。

本轮结果：Editor 目标构建成功（排队结束后 UBT 报告目标已是最新，7.54秒）；13个 UE 资源实际导入保存完成；运行时及制作源目录、三款符文材质映射、PNG 图标均已部署。首轮完成日志沿用了旧脚本的 `HUNTER_ASSETS_SAVED 13` 标记，实际路径及回执均为 Canine，后续脚本标记已改为 Canine。

重做顺序：`prepare_authoring.py` → Blender运行 `author_canine.py` → `bake_canine_runes.py` → 单独生成图标 → `build-editor.ps1` → `import-background.ps1` → `publish_canine.py`。仅更新本刀身的数据键和新资源，不重置其他改造项。

首次导入在任何资源写入前等待 SDK 查询锁；只停止了本任务导入进程及其 SDK 查询子进程。第二次导入使用引擎支持的进程级 `UE_SKIP_UBT_SDK_SETUP=1`，不改变机器或项目的 SDK 配置，也不终止其他构建。最终导入日志为 `import-commandlet-sdk-skip.log`。
