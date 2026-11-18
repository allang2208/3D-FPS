# 衣物母版、派生和发布关卡

本流程记录 2026-09-29 建立的衣物母版、候选和发布入口。新增/改版衣袖沿用制作合同；检查、动作采样、画面和间隙验收仅在用户明确要求时执行，旧流程授权不作为每次新任务自动检查的依据。原因：制作入口与测试授权分别确定，未授权时仍要如实保留候选及缺少的证据。

## 当前入口

- 公共母版库：`SourceAssets/GarmentFoundation20260929/library.json`。
- 候选合同/检查/发布：`Tools/ModularOutfit/garment_pipeline.py`。
- UE 后台读写、原生骨架派生、动作采样：`Tools/ModularOutfit/garment_ue.py`。
- 保存后动作计算：`Tools/ModularOutfit/garment_motion.py`。

三套实体基准分别为短袖棉布、长袖针织和锁子甲。宽松衣物使用 `loose` 合同，必须另行制作松量与运动方案；没有把贴身母版改名冒充通用宽松成品。 原因：装备组合依赖具体身体与服装轮廓，通用裁切或单件修复不能覆盖所有配对。

这些母版是结构基准，不是所有厚度、动作、镜头都已验收的成品。母版新资产不会自动替换现有衣物；SVD、201、攀爬等专用修复继续保留。

## 制作合同

新建候选：

```powershell
py -3.11 Tools/ModularOutfit/garment_pipeline.py init SourceAssets/MyGarment/candidate.json --kind long_thick --template chainmail --profiles M4 SVD --item my_item_id
```

根据款式填写：厚度、最小活动余量、袖口搭接、肩口/袖口形式、内外层对应关系、身体覆盖槽、手套组合。数值没有通用安全默认值，必须按模型与动作确定。厚度向外扩展，肘腕和掌侧单独预留活动空间；材质位移不能代替结构厚度。

`layer_contract` 记录内外层/卷边/装饰的对应方法、共同蒙皮来源、运动场和关节活动区。宽松衣物另填 `physics_contract`，说明辅助骨骼或布料约束、内衬跟随及碰撞方案。

每个 profile 的 `local_corrections` 记录需要保留的专用修正（文件绝对路径和 SHA256），`native_fit_review` 必须说明该枪参考姿态、侧别及已有修复如何处理。重新生成不能抹掉 201 右肩、左腕等修正；不能拿其他枪的通过记录代替。 原因：各枪已有专用局部修复，重生成需明确保留它们，别枪证据不能替代本枪参考姿态。

## 母版与拓扑

肩口朝躯干自然开放；袖口只连接明确的内外层边界。禁止对所有边界调用 `holes_fill`。本次历史错误为 208 个肩部跨接封面加 32 个重叠副本，已从新母版去除；不在新衣服上硬编码这些旧三角形编号。 原因：开放结构可能是模型有意保留的接口，自动补面会制造重叠或封死功能开口。

旧日期目录是历史依赖，不是新衣服起点。旧的七个直接发布入口已停用并提示新入口；它们保留作者逻辑用于追溯，不用于覆盖当前配置。

保持手腕覆盖、UV、材质槽、顶点色运动遮罩及真实厚度。按侧别和肩/肘/腕区域传递权重，禁止全局最近点串到另一只手或躯干。先在标准身体制作，再将几何和权重一起映射到目标原生参考姿态。 原因：槽位索引和显示名称可能变化，语义对应错误会把材质绑定到别的部件。

## UE 后台保存与派生

在 UE Python commandlet 中将 `Tools/ModularOutfit` 加入 `sys.path`，调用：

```python
from garment_ue import derive_bound
receipt = derive_bound(template_asset, native_weapon_asset,
                       new_candidate_asset, output_folder,
                       correction_edits=optional_native_edit_json)
```

返回回执写入候选合同的 `candidates[profile]`；若有局部修正，把回执中同一修正文件记录写入 `local_corrections[profile]`。不允许覆盖已有候选路径。不同拓扑或新增版型先通过建模/导入链保存作者网格，再使用这些保存与检查工具；该函数不是自动设计衣服的工具。

UE 5.8 的源模型 LOD 设置位于 `source_models`，只赋 `lod_settings` 不会可靠替换已有 LOD 参数。衣物专用设置保护开口和骨骼边界，禁止内外层焊接和合并重合顶点权重；用户要求 LOD 检查时读取实际三档结果，不能以设置值冒充渲染网格证据。第一人称细节优先，不能用大幅减面换取破口或长三角面。 原因：配置中的目标比例不等于实际渲染缓冲，运行选用的档位还受独立策略影响。

每档保存 `LOD0/1/2.json` 和资产散列。结构关卡检查非法坐标、错误索引、退化/重叠面、过长边、错误权重与左右串权重。当前结构基准 LOD0 上限 4 cm，保护边界后的 LOD1/2 上限 6 cm（回读最大约 5.90 cm，旧低档曾达 14.45 cm），另有动作绝对长度/相对拉伸关卡；这是对应第一人称尺度的基准，不是所有款式固定数值。阈值写在候选合同中；需要调整阈值时先说明模型尺度或 LOD 的依据，不为消掉失败而随意提高。

## 动作清单与证据

每个 profile 在 `actions` 明确列出当前实际加载的动画路径： 原因：文件名与版本标签不能证明正在使用的对象，制作需要对应实际引用的资源身份。

1. 待机、ADS/瞄准开火；运行时还要看 ADS 进入退出。
2. 普通/空仓换弹、弹鼓、握把、双持或逐发等实际分支。
3. 装备、检视、奔跑、近战。
4. 对应攀爬、翻越、施法 profile 的动作。 原因：服装变形需要对应项目实际使用的动作配置，单独待机姿态无法涵盖这些关节活动范围。

不适用的分组必须在 `not_applicable` 说明原因；不能把本应检查的动作填为不适用。完整服装的支持范围应覆盖其实际可装备的 profile，`--profiles` 是范围声明而不是“少填就代表全面支持”。

仅在用户明确要求相应动作采样和关卡检查时，才在 UE commandlet 调用 `collect_motion(candidate_manifest)` 并执行下列命令。原因：这些命令运行独立检查，不能把它们作为普通制作的默认步骤。

```powershell
py -3.11 Tools/ModularOutfit/garment_motion.py SourceAssets/MyGarment/candidate.json
py -3.11 Tools/ModularOutfit/garment_pipeline.py gate SourceAssets/MyGarment/candidate.json
```

离线检查使用保存后的渲染 LOD 和原生压缩姿态，20 Hz 加首尾帧；同时检查参考绑定、最大绝对边长、相对拉伸。资产、原生骨架、动画或合同变化会使证据失效。离散采样不覆盖运行时 IK/物理、镜头裁切或帧间全部情况。

可用 `garment_pipeline.py review-template candidate.json --stage runtime_visual --output review.json` 创建明确为 pending 的空检查单（间隙检查用 layer_clearance）。完成真实观察后填写结果，将报告路径和 SHA256 记入合同的 evidence 对应阶段；不预填覆盖动作或通过状态。

`layer_clearance` 与 `runtime_visual` 是独立的观察报告，不能根据拉伸数字自动标记通过。报告字段：`status`、`fingerprint`、`profiles`、`covered_actions`（每项 profile/group/clip）、`glove_combinations`、`observations`、`artifacts`（实际截图/视频/测量文件路径与 SHA256）。间隙报告 `checks` 必须包含 inner_outer_clearance、skin_clearance、cuff_overlap；画面报告必须包含 camera_intrusion、ads_transition、lod_switch、runtime_deformation，逐项真实通过才填 true。检查内衬外翻、袖口露空、皮肤穿出、肩部进入镜头及三档 LOD 切换，并记录部位/动作时刻/结果。动态层需要包含实际 WPO、IK 或布料运动。 原因：文件名与版本标签不能证明正在使用的对象，制作需要对应实际引用的资源身份。

默认后台制作，不自动启动游戏或重启已有编辑器。画面证据只采用用户要求的捕获或用户提供的对应素材；缺少画面/间隙证据时保留候选并说明未验收，不伪造通过，也不改低工具门槛。原因：旧样本的通过结果不适用于新几何、动作或合同，缺少证据不能靠文档措辞补齐。

## 接入与恢复

```powershell
py -3.11 Tools/ModularOutfit/garment_pipeline.py publish SourceAssets/MyGarment/candidate.json
```

调用现有发布器会重新运行其内置关卡；本页不授权调用或绕过这些检查。执行已授权发布时，工具核对当前引用是否仍为制作开始时的路径，只更新本次衣物声明的 profile 和覆盖合同，保留其他项目的并行修改，并保存发布前配置。新物品的 ID、图标、掉落、库存和保存数据仍走物品接入链；本工具不会凭空新增一件完整游戏物品。 原因：共享工作树可能包含其他任务改动，发布范围需要对应本次实际拥有的文件与差异。

“结构基准可用”“动作数值通过”“完整可发布”是三种不同状态。门禁能阻止已知错误和缺少证据的直接发布，不能数学保证任意新款/新动作永不穿模。 原因：门禁只覆盖已知条件和现有证据，不能保证任意新款与未覆盖动作永远无穿插。
