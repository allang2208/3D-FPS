# 赐福激光镭射

枪械通用战术槽改造，ID 为 `blessed_laser`，传说级红色卡片。

| 属性 | 改造值 |
| --- | --- |
| 腰射随机散布 | ×0.20（减少 80%） |
| ADS 瞄准时间 | −30% |
| 后坐力 | ×1.15（增加 15%） |
| 枪械稳定性 | ×0.85（降低 15%） |

ADS 沿用项目的 `ads_percent` 约定，与其他百分比改造相加；其余倍率沿用枪匠的乘法叠加规则。描述与效果分别存储，不重复在描述里填写数值。

`Content/ColdSteelData/gunsmith.json` 的 `common_options.tactical` 将该改造注入所有枪械的选项和允许列表；近战、弓、工具和法杖继续走各自目录。保存与读取沿用枪匠配件 ID 流程。

`TacticalDeviceVariants.h` 保留 `blessed_laser` 的镭射行为类型，同时为各枪选择独立的 `SM_BlessedLaser_<Family>` 模型。枪匠预载和左右手战术组件使用同一模型目录；双持手枪的配件动作选择继续复用镭射行为。共享图标使用 `tactical_blessed_laser` 独立键。

金色光束和命中光点使用两份独立材质：

- `/Game/Weapons/TacticalDevices20260913/BlessedLaser20261006/M_BlessedLaserBeam`
- `/Game/Weapons/TacticalDevices20260913/BlessedLaser20261006/M_BlessedLaserDot`

以现有 ScopeAware 材质为基础复制，保留光束的时序响应、光点的 AfterMotionBlur 合成和逐像素深度遮挡。连续金色光束叠加三条柔和细丝与沿束长移动的光泽，命中点加入轻微亮度起伏。GPU Time 驱动流动，Custom Primitive Data 1 传入实际光束长度，使遮挡截断时的移动速度保持一致；Custom Primitive Data 0 继续驱动瞄具淡出。没有增加粒子、灯光或射线查询。

制作入口：`Tools/Weapons/BlessedLaser20261006/create_materials.py`，同目录 HLSL 为特效源代码。资产处于已有 AlwaysCook 目录。后台保存记录位于 `Saved/BlessedLaser20261006/material-save.json`。

2026-10-06 两份材质已通过无界面 Python commandlet 保存；`FPSGAMEEditor Win64 Development` 后台构建成功，日志为 `Saved/BuildEditor/build-20261006-114114.log`。

本次不启动游戏，不执行自动测试或渲染验收；实际光效和操作手感由用户在游戏中确认。

## 2026-10-06 用户截图反馈后的修订

用户反馈金色不明显、激光偏淡，以及 G18 旧镭射外壳出现红色碎点，并要求先给出新发射器设计图。

- 金色 V1 光束基础透明度只有 0.34，且自发光没有曝光补偿。V2 基础透明度改为 0.80，减低蓝色分量，使用 `EyeAdaptationInverse` 保持日光环境下的颜色和亮度；细丝高光仍沿光束方向移动。命中光点同步处理，保留原遮挡和瞄具淡出。
- 普通红色的 ScopeAware 光束和命中点保留红色，加入同类曝光补偿，避免依靠场景整体曝光来提亮。
- 只读读取确认 G18 `SM_G18_laser` 共用 `M_M1911_laser_Body`，其最终发光依赖底色红色差值及顶点色 G。原镜口以外的贴图红点会在区域信息失配时被点亮。本次从原始 `M1911_Device_Editable.blend` 的镜口区域烘焙 UV0 专用遮罩，共 310 个相关三角面；干燥与淋湿母材质只在遮罩内生成红色发光，不再依赖导入后的顶点色 G。未改变外壳几何、涂层或挂点，未把截图里的红点认定为已证明的实体破洞。
- 诊断时当前 PIE 角色持有 A762，读到的是普通红色光束材质，不能据此断言用户截图中安装的改造 ID。没有改动用户装备与存档。

制作入口为 `bake_aperture_mask.py` 和 `repair_laser_materials.py`，均在 `Tools/Weapons/BlessedLaser20261006`。修订通过当前已运行的编辑器保存。首次纹理导入后，EditorAssetLibrary 因正在 PIE 拒绝读取；结束当前游玩后完成保存，未关闭/重启编辑器，也未再次启动游戏。保存记录为 `Saved/BlessedLaser20261006/visual-repair-save.json`，修改前资产备份在该记录的 `backup` 路径。完成的是材质制作、编译与保存，没有进行修改后的游戏视觉复测。

此阶段先提供了新发射器概念设计：深石墨金属封闭外壳、少量金色嵌线、内凹遮光镜口及日轮刻纹，附正/侧/顶视图。图像通过内置 `image_gen` 生成，以用户第二张截图作为用途和轮廓参考；各视图为设计推断，不是工程测量图或已导入模型截图。用户随后批准完成建模，制作记录见下文。

- 设计图：`SourceAssets/BlessedLaser20261006/Design/concept-01.png`
- 完整生成提示词：`SourceAssets/BlessedLaser20261006/Design/concept-01-prompt.txt`

## 2026-10-06 批准设计后的模型制作

按概念 01 在 Blender 中制作了可编辑硬表面母模。主体为倒角八边形封闭胶囊，包含金色镜口压环、内凹黑色遮光筒、独立镜片、金色侧板嵌线、双侧日轮纹、后部旋钮与顶部承接座。只有独立镜片使用金色自发光；石墨外壳、金属嵌线和刻纹均为不透明 PBR 表面。五份共享材质直接支持 `WeaponWetness`，保留黑金身份。

- 分件母模：`SourceAssets/BlessedLaser20261006/Model/BlessedLaser_Master.blend`
- 合并游戏母模：`SourceAssets/BlessedLaser20261006/Model/BlessedLaser_GameMaster.blend`
- 各枪可编辑装配：同目录 `Fitted/BlessedLaser_<Family>.blend`
- 交付 FBX：同目录 `Exports/SM_BlessedLaser_<Family>.fbx`，另有 Master
- 作者参数、保留材质与原始挂点：同目录 `authoring.json`
- 制作入口：`Tools/Weapons/BlessedLaser20261006/author_emitter.py`

适配 M4、AKM、QBZ191、M1911、G18、PitViper2011、DanWesson715、RSH12、ASH12、M16、A762、SVD、PKM、LMG201、HK416，共 15 个枪型。各版沿用当前镭射资产的局部坐标、原安装接触面和 `Emitter` / `AimGuide` 挂点，用局部过渡座衔接新壳。HK416 的旧主体与安装结构合用一个材质，单独从其原始可编辑场景提取 `mount_low` 接触结构，避免把旧壳、线缆和开关残留带入新模型。母体缩放按各枪当前附件包围尺寸制作；未调整角色姿态、枪体装配变换或射线方向逻辑。

UE 模型目录为 `/Game/Weapons/TacticalDevices20260913/BlessedLaser20261006/Models`，材质目录为其同级 `Materials`。`TacticalDeviceComponent.cpp` 在选择 `blessed_laser` 时使用新模型，普通红色 `laser` 保留原路径。此改动不修改现有数值或存档 ID。

共享灰阶金属框图标从实际母模渲染轮廓，再由内置 `imagegen` 与既有认可边框合成。正式运行 PNG 为 `Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms/tactical_blessed_laser.png`；制作源图、最终图和完整提示词保存于 `SourceAssets/BlessedLaser20261006/Model`，分别为 `blessed-emitter-icon-source.png`、`tactical_blessed_laser.png`、`icon-prompt.txt`。UE Texture2D 为 `/Game/Weapons/TacticalDevices20260913/BlessedLaser20261006/Icons/T_BlessedLaserIcon`，UI 纹理组、Editor Icon 压缩、sRGB、Never Stream。

来源：本轮新外壳根据用户批准的 AI 概念进行本地几何制作；安装座沿用项目当前对应枪械配件的原有几何、UV 与材质，来源路径逐项保存在 `Model/Sources/mount-sources.json` 和 `authoring.json`，保留这些已有素材原有授权范围。

本轮不启动游戏，不执行测试或额外验收渲染。图标渲染属于正式 UI 资产制作；游戏中的遮挡、装配观感与光束表现由用户自行测试。

模型切换代码已完成 `FPSGAMEEditor Win64 Development` 构建，日志为 `Saved/BuildEditor/build-20261006-122937.log`。原有编辑器在导入排队期间退出，后续接入改用同一批次互斥下的无界面 Python commandlet，不重新打开编辑器。

后台接入已完成：15 个装配模型与 1 个母模、5 份共享材质、2 份天气材质映射均已保存，共 23 个模型/材质/数据包；共享图标 Texture2D 另行导入并保存。生产日志为 `Saved/BlessedLaser20261006/import-20261006-123300.log`，逐资产保存回执为 `SourceAssets/BlessedLaser20261006/Model/import-receipt.json`，图标回执为同目录 `icon-import-receipt.json`。这代表资产已实际导入和落盘，不代表已进行游戏实测。

## 2026-10-06 全枪型安装结构 V2

用户反馈旧壳尾端残留、支架悬空并要求逐枪排查。本次仅处理 15 个赐福镭射装配模型。保留批准的黑金外壳、光束效果、属性、存档 ID 与光学挂点；普通红色镭射使用原资产。

根因：V1 按三角面最多的材质槽判断旧主体，PitViper 的旧尾壳位于另一个材质槽，留下了大量碎片。其余型号保留的圆壳托架与新平面承接块也不匹配；用残留结构的整体包围盒搭接会造成悬空、穿入和不必要的绕光轴倾斜。V2 停用该算法，直接使用批准的封闭母体与明确的安装结构。

通过只读 commandlet 导出当前实际运行的 15 份枪械骨架模型和绑定骨变换，再按运行时战术配件的相对变换转换到各配件空间。接触数据保存在 `Model/MountRepair/Hosts`，不修改宿主枪体。外部 Blender 装配图用于本次用户明确要求的接口排查，不代表游戏实测。

| 枪型 | V2 安装调整 |
| --- | --- |
| M4 | 安装面横向移到实际侧轨承托面，取消旧圆托与穿入导轨的高边。 |
| AKM | 按护木表面斜度制作接触面，底部与新外壳键座闭合。 |
| QBZ191 | 独立设置侧轨承托宽度，避开护木开孔，使用实体过渡座。 |
| M1911 | 重做窄型下挂接触座，顶部贴合机匣下缘曲面。 |
| G18 | 沿用原前后安装位置，接触面跟随机匣下缘的纵向坡度。 |
| PitViper2011 | 完全移除旧尾壳碎片，支座后移至平直承托区，避开前端台阶。 |
| DanWesson715 | 窄型承托贴合枪管下部曲面，取消原来高而悬空的矩形托架。 |
| RSH12 | 保留原狭窄导轨夹爪与侧置路径，重建连续偏置腹板，增加贴合新键座的纵向承托；校正外壳绕光轴的倾斜。 |
| ASH12 | 按底轨表面制作接触座，主体与导轨用封闭实体衔接。 |
| M16 | 明确保留护木抱箍及承托板，只替换圆壳托架和过渡座，不丢失枪体固定结构。 |
| A762 | 取消重复旧承托板，用贴合当前护木的独立座体连接。 |
| SVD | 前后两处接触脚跨过中部开口，底部与新外壳承接块连接。 |
| PKM | 校正安装方向并横向偏置接触面，贴合当前枪管外表面。 |
| LMG201 | 接触端后移至实体护木承托区，用斜向实体支撑连接外壳。 |
| HK416 | 移除原镭射托架，按侧轨后段接触面重建小型偏置座，避让前方结构。 |

制作源与恢复位置：

- `Tools/Weapons/BlessedLaser20261006/fit_mounts.py`：逐枪明确接触范围、实体连接、接触面制作与导出；原 `author_emitter.py` 已调用此入口，重新制作不会恢复 V1 算法。
- `Model/MountRepair/Editable/BlessedLaser_<Family>_MountV2.blend`：保留独立可编辑机械零件的局部坐标制作源。
- `Model/Fitted`、`Model/Exports`、`Model/authoring.json`：更新后的正式装配源、FBX 与参数；`Emitter` 和 `AimGuide` 使用原值。
- `Model/MountRepair/Before`：本次修改前的 15 个模型、导出文件、UE 模型资产、参数与旧制作脚本。
- `Model/MountRepair/before-mounts.jpg` 与 `after-mounts.jpg`：相同相机规则下的离线接口排查图，宿主为灰色诊断材质。
- `Tools/Weapons/BlessedLaser20261006/import_mounts_v2.py`：仅导入和保存 15 个模型，复用已有共享材质。

接入时原有编辑器已经退出，因此使用同一批次互斥下的无界面 commandlet 保存，未打开或关闭编辑器。15 个正式模型均已实际导入并保存：`Model/MountRepair/import-mounts-v2-receipt.json` 的 `saved` 数量为 15，`status` 为 `fifteen_mount_assets_imported_and_saved`。最终生产日志为 `Saved/BlessedLaser20261006/mount-import-20261006-135308.log`。

导入制作过程中清除了 M16 抱箍继承的多余 UV 通道，将其接入同一石墨材质；新接触面按最终三角面生成物理尺度 UV，修正 SVD 台阶接触处的退化切线。最终导入无 FBX 几何告警。本次未修改 C++，无需重新构建基础 DLL。

此次不启动游戏；动态持枪、双持遮挡和游戏观感由用户测试。
