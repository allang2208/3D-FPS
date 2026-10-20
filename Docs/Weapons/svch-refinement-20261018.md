# SVCH 表面、基础握持与 ADS 修订（2026-10-18）

本轮针对用户反馈的原厂 SVCH 表面低模感、双手握持和 ADS 顺时针歪斜进行排查与修订。首次交付为后台制作；用户随后明确要求“你自行检查一遍”，并追加修复检视翻腕的右腕折痕、优化机械准星等圆曲部件。最新模型与材质为 R8Surface；手模和动作继续使用 R7NativeV9 基线，旧版记录保留为历史。

## 当前：保留原型的表面升级（R8Surface）

按用户截图及“尽量不改变原模型”的要求，参考既有 WS1、SVD、A762 与 PKM 表面改进流程，在原模型上制作局部倒角、圆曲面与独立结构贴图。本轮只交付后台制作、资产保存和必要编译；没有追加游戏测试、截图或外观验收。R7 的历史运行结果不代表 R8 已通过验收。

新网格：`/Game/Weapons/SVCH/Refined20261018/R8Surface/SK_SVCH_R8Surface`。新增 9 个本枪材质实例、18 张引擎纹理，全部已实际导入保存。装备与预加载引用指向新网格；`FPSGAMEEditor Win64 Development` 后台构建成功（20 个步骤，退出码 0）。构建日志在 `SourceAssets/SVCHRefinement20261018/R8Surface/build-editor.log`，交付状态已写入回执。

| 部位 / 内容 | R8 制作内容 |
|---|---|
| 机匣、护木、上盖 | 从原模型对应壳体补 0.35 mm、三段窄倒角；保留主体平面、孔槽及装配位置 |
| 导轨与其他机械边缘 | 导轨 0.12 mm、一般小件 0.18 mm 倒角；保留真实齿形和节距 |
| 后机瞄侧盘及两处销轴 | 保持原尺寸位置，圆周增加到 64 段并补边缘倒角 |
| 已改善的圆曲件 | 保留 R5 瞄孔、护翼、准星柱、枪管和枪口机构；握把、贴腮与托垫接触几何保留 |
| 结构贴图 | 枪械独立展开 UV；主体 4K、弹匣 2K 法线，其他机械件 512–1K；烘焙局部 AO 与分件粗糙度，遮蔽只来自对应刚性部件 |
| 材质 | 分开金属、聚合物、橡胶和活动件的反光；以结构法线替代原随机颗粒法线，减弱粗糙度噪声，关闭附加斑驳、划痕与假磨边 |
| V9 手模及动作 | 保留原生手模跟随、18 个既有修形和材质槽 9/10 隐藏规则；继续引用 R7 已更新的 `R5/DA_SVCH_BaseGrip`，没有重建手腕或手指动作 |

主体粗糙度按部位约 0.34–0.44，枪机 0.31、聚合物 0.52、弹匣 0.51、橡胶 0.69；WS1 仍叠加少量细微表面变化与既有天气效果。使用新 UV 的物理尺寸调整水珠平铺，公共 WS1 母材质与预设未改。

制作源枪体为 **72,304** 三角面，内嵌手臂 **37,086** 面，合计 **109,390** 面；相对 R5 枪体增加 14,904 面。原枪外形、机械骨绑定、准星/照门/枪口/抛壳口标定继续沿用，运行引用与预加载之外没有新增动作逻辑。

可编辑源、FBX、烘焙纹理及脚本在 `SourceAssets/SVCHRefinement20261018/R8Surface/`。`model_receipt.json` 为制作输出，`bake_receipt.json` / `texture_receipt.json` 为贴图输出，`install_receipt.json` / `arm_correctives_receipt.json` 为实际资产保存记录；这些记录不作为视觉通过结论。用户自行在游戏中确认最终效果。

## 手模与动作基线：回归 V9 源手型和认可动作（R7NativeV9）

用户指出 R5 右腕仍有扭曲，并明确要求沿用认可动画与标准 V9 手模，不能另造动作。为此撤回 R6 肩肘支撑候选；该候选曾保存，但没有运行交付，现不被运行或预加载引用。废案说明在 `SourceAssets/SVCHRefinement20261018/R6/REJECTED_SUPPORT.md`。

继续排查发现：SVCH 旧适配层除握点对齐外，还改变了右腕与指骨局部姿态；检视中额外右腕旋转最大约 10.65°，部分指骨旋转超过 40°。关闭关节修形并未消除腕部外形问题；当前保存源动画的原始与压缩姿态也基本一致，未把这两项当作故障原因。

本次改为：

- 从当前保存的 **压缩源动画**读取全部 12 条动作；源动画资产不改写。
- 删除 SVCH 右手、指骨、上臂和前臂的局部改姿轨道。仅用整条右臂的刚体坐标对齐保留原有掌心锚点，右臂内部关节关系与源动作一致。没有重新设计腕肘运动。
- 两根末端扭转辅助骨沿用既有 V9 标准：近腕 100%、中段 50%，不改变手掌或手指。
- 直接引用原生 V9 的 SVD 家族裸臂，隐藏枪体内嵌手臂槽 9、10，保留原生 UV、权重、18 个修形及三槽 `MI_BareSkinV9`。资源名保留历史 `BarePalmV7/SVD/SK_SVD_BareArmsV7`，实际内容已在 V9 推广中升级；不另造手模。
- 枪械继续使用 R5 圆滑机械件。现有 `R5/DA_SVCH_BaseGrip` 在备份后原位更新，当前网格和代码引用不变，因此本次资产接入无需新增 C++ 构建。

作者数据中，掌心位置变化为 0；右臂内部关节相对源动作的最大旋转差约 `3.62e-14°`（浮点误差，扭转辅助骨单独按 V9 规则处理）。原生手模和 12 条源动画的散列记录在 `R7NativeV9/source_preservation.json`。制作、保存与备份见同目录 `register_native_arm.py`、`registration_receipt.json`、`install_receipt.json`、`Before/`。

本轮运行 `svch-check-20261018-native-v9-02` 已完成：208 张截图、208 条逐帧记录，无缺图；ADS 14 个稳定采样中瞄点中心误差为 0 px，普通与空仓换弹完成，检视后正常回握。全部 53 个检视采样均确认原生 V9 裸臂实际可见。共 156 个采样显示该原生网格；前 52 帧在异步载入期间仍显示既有的内嵌 V9 手臂，不把这部分写成已经切换完成。源手模与 12 条动画的 13 个文件散列均未变化。

右腕保留源动画的自然弯曲；本轮移除的是 SVCH 额外叠加的局部改姿，不以新的腕角阈值重新设计动作。画面对比见 [原生 V9 回归对比](../../SourceAssets/SVCHRefinement20261018/R7NativeV9/native-v9-comparison.jpg)，完整记录见 `R7NativeV9/validation_receipt.json`。第一次离屏启动在编辑器 Python 回调栈中崩溃、未进入检视；第二次仅对自检进程使用引擎支持的 `-DisablePython` 后完成，没有修改项目插件配置。

## R5：检视右腕与机械圆曲面

当前资产为 `/Game/Weapons/SVCH/Refined20261018/R5/SK_SVCH_Refined_R5` 和同目录的 `DA_SVCH_BaseGrip`。网格、姿态、18 个原生手臂修形均已保存；运行引用、预加载与精确装备外观 profile 已切换至 R5。最终 Editor 构建成功，独立资产读回 **566 项通过**，离屏游戏自检完成 **208 张截图 / 208 条逐帧记录**，全部图片存在且实际使用 R5 网格与姿态资产。自检进程正常退出。

右腕折痕的主要原因是检视动作中的轴向旋转没有传给前臂扭转骨：原检视 3.7167 秒时，手掌相对前臂转到约 +83.52°，近腕扭转骨仍停在 -33.81°，相差约 **117.33°**。R5 仅在 SVCH 的检视差量中加入两条右前臂扭转轨道，近腕承担 100%、中段承担 50%，进出检视平滑衔接。离线同帧近腕扭转已与手掌一致；手掌变换与动作首尾变化均为 0，另 11 条动作保持原样。原生腕部修形继续处理弯曲，没有用移动握点来掩盖扭转。

| 部位 | R5 几何修订 |
|---|---|
| 照门孔环 | 72 段椭圆环，真实内外表面与 0.25 mm 边缘倒角 |
| 准星护翼 | 72 段开口圆弧，平滑连接两端，0.18 mm 倒角 |
| 准星柱与六处销轴/螺钉 | 48 段圆曲面，按原装配尺寸重建，保留准星顶点高度 |
| 枪管与枪口制退器 | 原低边数截面重建为 64 段空心管，三组真实贯穿排气孔带圆角，保留枪口端点 |

共替换 10 个原始连通机械件；平直机匣、安装座、槽口和其他活动件保留。枪体共 **57,400** 三角面，手臂仍为 37,086 面，合计 **94,486** 面。新增圆曲件均闭合，保存后没有退化面；9 个武器表面与 2 个手臂材质槽沿用既有身份。照门、准星、枪口与抛壳口标定不变。

R5 自检使用独立存档 `SVCHPoseAudit_svch-check-20261018-r5-01` 和既有验证地图，没有启动可交互编辑器或修改正式存档。结果如下：

| 检查 | R5 实际结果 |
|---|---|
| 检视扭转 | 极端翻腕区间 11 个运行采样，手掌与近腕扭转骨最大差值 **0.000103872°** |
| 右腕画面 | 同一检视 3.733 秒画面对比中，R4 的深扭折已消失，腕部与前臂连续衔接；另查看检视各阶段与复位关键帧 |
| ADS | 14 个稳定采样，最大物理滚转 **0.000000575°**，前后瞄点中心误差 **0 px** |
| 换弹 | 普通换弹 5→10、空仓换弹 0→10 完成，换弹后 ADS 正常 |
| 检视复位 | 结束后返回基础双手持枪，原手掌接触与动作首尾保持一致 |
| 机械曲面 | UE 画面中的照门孔和准星轮廓平滑；同机位白模近景另外确认照门、护翼、枪口内外曲面与排气孔 |

游戏对比：[R4 / R5 机械瞄具与右腕](../../SourceAssets/SVCHRefinement20261018/R5/r4-r5-comparison.jpg)。几何近景：[照门、准星、枪口白模对比](../../SourceAssets/SVCHRefinement20261018/R5/r4-r5-mechanisms-clay.jpg)；该图为 Blender 制作源的统一材质渲染，不是 UE 材质效果图。完整运行记录在 `Saved/SVCHPoseAudit/svch-check-20261018-r5-01/`，包含 `result.json`、`summary.json`、`contact_sheet.jpg` 与 `inspection_sequence.jpg`。未扩展到音频、联机、第三人称或全部可选改造配置。

构建日志：`R5/build-r5-final2.log`（Succeeded）。期间两次 DLL 占用均保留原进程、等待退出；用户保存关闭新开的编辑器后完成链接。另修正一处阻断共享构建的声明错误：`ColdSteelConsumablePresentation.h` 中 `FJsonObject` 的前置声明由 `struct` 改成与引擎一致的 `class`，没有修改 UI 逻辑。最终交付与检查回执为 `delivery_receipt.json`、`R5/validation_receipt.json`。

制作与证据目录：`SourceAssets/SVCHRefinement20261018/R5/`。`SVCH_Refined_R5.blend` 与 `SK_SVCH_Refined_R5.fbx` 为本次可编辑源与导出；`author_profile_r5.py`、`shared_profile_r5.json`、`profile_receipt_r5.json` 记录扭转修订；`author_mechanisms_r5.py`、`model_receipt_r5.json` 记录曲面重建；`install_receipt.json`、`arm_correctives_receipt.json` 与 `saved_assets.json` 分别记录实际保存、原生修形和读回检查。

## 用户授权自检后的 R4 修订

R4 历史运行目标为 `/Game/Weapons/SVCH/Refined20261018/SK_SVCH_Refined_R4`；模型、18 个原生手臂修形与独立 `SurfaceV4` 材质、纹理均已保存。用户保存关闭编辑器后，最终 Editor 构建成功；R4 读回 **564 项通过**，并完成了独立离屏运行复查。数值检查通过，手臂反面发黑已从实际画面中消失；当时极端检视翻腕仍能看到右腕折痕，因此继续进行顶部的 R5 修订。

| 检查范围 | 发现与修订 | 证据 |
|---|---|---|
| 倒角拓扑 | R2 保存后有 17 个零/近零面积三角面；倒角后增加重合点合并、退化面清理和确定性三角化。R4 导出/保存均为 74,478 面，其中枪体 37,392、手臂 37,086，无退化面 | `Checks/before_topology_cleanup/saved_assets.json`、`Checks/saved_assets.json` |
| 手臂面朝向 | R3 的全部 37,086 面相对原生 UE 供体反转。GLB 与 UE 供体错误共用了同一种绕序转换；单位法线检查无法发现此问题。R4 恢复原生绕序，并按实际顶点角重新对应 UV/法线；骨骼、权重和握持差量未改 | `Checks/before_arm_winding/arm_uv_comparison.json`、`Checks/arm_uv_comparison.json` |
| 手臂逐面对应 | R4 全部 37,086 面绕序与供体一致，最大面心位置误差约 0.00000852 cm、最大 UV 误差约 0.000000053；材质继续使用 `MI_BareSkinV9` | `Checks/arm_uv_comparison.json` |
| 原生关节修形丢失 | R4 首次实机复查消除了发黑，但检视翻腕仍出现明显折痕。FBX 手臂搬运未保留原生供体的 18 个 `JC_` 关节/握拳修形；已通过完全对应的静止顶点补回，最大对应误差 0.0000149 cm，由现有 `FPSArmJointCorrectiveComponent` 驱动 | `arm_correctives_receipt.json`、`install_arm_correctives.py` |
| 表面斑纹 | R3 原场景及中性地面画面均有较明显高光花斑。仅在本枪 `SurfaceV4` 中降低法线幅度、缩小颗粒平铺尺寸、减弱粗糙度花斑；公共 WS1 预设及此前材料版本不改 | `Checks/fine_finish_save.json` |
| ADS（R4 实机） | 最终运行采样 14 个稳定 ADS 状态；最大物理滚转约 0.000000575°，照门与准星投影到画面中心的距离为 0 px。使用 SVCH 自身瞄点与向上轴，不使用共享 SVD 标记骨 | `Saved/SVCHPoseAudit/svch-check-20261018-r4-correctives/summary.json` |
| 换弹/复位（R4 实机） | 5→10 普通换弹与 0→10 空仓换弹均完成；换弹后 ADS 保持对齐；检视结束回到基础持枪 | 最终运行保存 208 张真实游戏截图，进程退出码 0 |
| 握持视觉 | R4 腰射和 ADS 的手臂外表面正常显示，未见此前的大面积反面发黑；抽查两种换弹与检视后的握持复位。腕部修形实际触发，最大权重 1；检视 3.73 秒时右腕仍有折痕，保留为视觉残余问题 | 最终运行 `contact_sheet.jpg`、`Frames/inspect_00175.png`；`Checks/r3-r4-comparison.jpg` 为同一照明条件对比 |

运行工具：`Source/FPSGAME/Weapons/SVCHPoseAudit.cpp` 只有显式 `-SVCHPoseAudit` 才注册；测试存档必须包含 `SVCHPoseAudit`，不操作正式玩家存档。`Checks/run_runtime.ps1` 使用项目既有 `-SkipStartupMenu`，否则启动菜单会暂停世界。测试没有开启音频；未检查联机、第三人称或全部改造配件。

最终构建日志：`Checks/build-corrective-check.log`（Succeeded）；最终资产读回：`Checks/r4-complete-readback.log`；修形保存：`Checks/arm-correctives-import.log`；最终运行：`Checks/runtime-svch-check-20261018-r4-correctives.log`。交付散列和范围见 `delivery_receipt.json`、`Checks/validation_receipt.json`。R3 两次运行及 R4 未补修形前的一次运行保留为历史证据。运行画面、静态资产读回和基础 DLL 构建状态分别记载，不互相替代。

## 排查路径与处理

| 问题 | 实际路径 / 原因 | 本轮处理 |
|---|---|---|
| 平面割裂、倒角无效 | 原始 GLB 的分裂法线顶点被直接重建为互不连接的面；Body 12,982 顶点，焊接后为 2,800 顶点 | 仅同一机械件内焊接重合顶点，去退化边；硬边 0.25 mm / 小件 0.15 mm 双段倒角，保留开孔与源剪影，重建按面积加权分裂法线 |
| 所有主体都像同一种金属 | 旧 Body 单槽覆盖机匣、握把、贴腮与托垫 | 分为机匣、枪管钢、聚合物、橡胶等九种表面身份；沿用 WS1 母材质，增加本枪独立的细颗粒法线，不改公共预设 |
| 手臂 UV 损坏 | 旧脚本对裸手也执行 cube_project | 保留原手臂拓扑和权重，恢复供体逐面角 UV0、分裂法线；实际装备外观继续沿用 SVD 原生 V7 家族，并按新资产实际槽序隐藏内嵌手臂 |
| ADS 瞄点前后错位 | 以 Blender rest 矩阵反算 UE 组件空间点，遗漏 Y 镜像；Rear local Y 为 0.307448，正确约 0.019932 | 从已保存 UE 网格读取组件绑定矩阵，按同一矩阵生成照门、准星、枪口、抛壳口 |
| ADS 顺时针歪斜 | 使用骨骼局部 Z 当作枪身竖直方向；枪根绑定含约 5° 轴向偏角 | 用实测枪身向上向量 `(-0.087155794, -0.000001406, 0.996194694)` 约束完整瞄准坐标系，腰射也使用同一物理竖直轴 |
| 双手没贴枪 | 直接复用 SVD 序列，缺少 SVCH 表面接触差量；仅对齐握把包围盒中心不足以对齐掌心、食指和扶木手 | 从当前保存的 12 条 SVD 序列取姿态，按真实蒙皮表面拟合掌心/手指；两骨解算联动肩肘腕，骨长不变；原动作离开握点时平滑退出修正 |
| 活动件装配偏移 | 将组件空间几何直接绑到弹匣/枪机骨，未反算其相对枪根的待机变换；枪机绑到了标记骨 | 在当前保存 idle 中反算活动件 bind；弹匣与内部弹药共同驱动，枪机改用实际动画骨 `WPN_bolt` |

## R2 历史运行引用

- 网格：`/Game/Weapons/SVCH/Refined20261018/SK_SVCH_Refined_R2`。
- 姿态差量：`/Game/Weapons/SVCH/Refined20261018/DA_SVCH_BaseGrip`；运行消费者为 `SVDGripProfiles.cpp`、`WeaponGripProfileNode` 和现有动作通道。
- 动作源仍为 `/Game/Weapons/SVDDragunov20260922/Complete20260923/Animations/A_SVD_*`；不复制整套序列，不改射击/补弹/音效时钟。
- 网格切换：`SVCHWeaponAssets.h`；瞄准：`AFPSGAMECharacter::UpdateADSPose`；腰射：`RifleHipFraming.cpp`；预加载登记同步更新。
- 装备外观：`Content/ColdSteelData/modular_outfits.json` 为新网格增加精确 profile，旧版保留。
- 抛壳：`CasingPortCalibration.h` 改用本枪的枪根局部厘米，而非组件空间厘米。

本轮重点是原厂基础握持与瞄准；已有改造件的独立握姿、脱手后的换弹/拉柄接触和第三人称不以此作为新验收结果。共享动作的来源与许可不变；模型来源继续见 [原 SVCH 来源记录](../../SourceAssets/SVCHSketchfab20261017/PROVENANCE.md)。

## 可编辑制作源与回执

制作目录：`SourceAssets/SVCHRefinement20261018/`。

- `SVCH_Refined.blend`、`Exports/SK_SVCH_Refined.fbx`：可编辑模型与导出。
- `author_model.py`、`model_receipt.json`：拓扑、分区、UV、法线、活动件绑定。
- `runtime_inputs.json`：只读导出的当前 UE 绑定和源动作；`calibration.json`：瞄点/竖直轴。
- `fit_contacts.py`、`fit_fingers.py`、`contact_fit.json`、`finger_fit.json`：表面抓握制作。完整逐指拟合后再运行 `fit_fingers.py --preserve-order`，保持右手无名指、小指的原生高度顺序，再生成差量。
- `author_profile.py`、`shared_profile.json`：同源时钟的稀疏局部骨骼差量。
- `produce_surface_textures.py`、`Textures/`：本枪独立材质细节。
- `install_assets.py`、`install_receipt.json`：实际已保存资产列表、材质槽、姿态输入散列。

最终 R2 导入已完成：9 个武器表面槽，2 个内嵌手臂槽；手臂隐藏索引为 `[9,10]`。武器 37,416 三角面，内嵌供体手臂 37,086 面；实际 V7 换装手臂配置保留。`install_receipt.json` 的 `complete` 为真，列出 14 个保存资产；保存的差量输入散列与最终 `shared_profile.json` 一致。

针对本次故障的离线诊断记录在 `diagnosis.json`。重建瞄点间距为 53.774 cm，绑定空间物理向上误差为 0°。最终组合姿态相对原始接触代理仍有少量皮肤交叠（右手最大约 1.56 mm，左手约 2.47 mm）；不是零穿插验收结论。保留诊断图 `contact_diagnosis_final.png`，它是源坐标点云，不是引擎画面。

初次 Editor 构建 `Saved/BuildEditor/build-20261018-012444.log` 被其他工作中的 `FacilitySpawnRecheckCommandlet.cpp` 两处 `auto*` / `TObjectPtr` 类型推导错误阻塞；本轮没有改动该文件。随后磁盘上的对应循环已改为显式指针类型。

**最终 Editor 构建成功**：后续共享 `FPSGAMEEditor Win64 Development` 完成 584 个步骤，日志 `SourceAssets/Zhanmadao20261018/build-FPSGAMEEditor-01.log` 返回 `Result: Succeeded`（760.18 秒）。该构建开始于本轮 C++ 修改之后；最终 `Binaries/Win64/UnrealEditor-FPSGAME.dll` 包含 R2 实际网格引用。交付记录见 `SourceAssets/SVCHRefinement20261018/delivery_receipt.json`。

最终手指顺序修订于 2026-10-18 01:40 后台保存至 `DA_SVCH_BaseGrip`；`save-final-profile-direct.log` 记录 `SVCH_FINAL_PROFILE_SAVED`，输入散列已写回导入/交付回执。这一步只保存 DataAsset，没有再次改动 C++。该资产保存进程使用引擎支持的进程级 `UE_SKIP_UBT_SDK_SETUP=1`，省去已完成 Editor 构建后的重复 SDK 初始化；没有修改机器环境或停止其他构建。

首次 R2 交付时没有进行游戏运行或截图；随后用户授权的 R4 自检结果见本文顶部。音频与联机验收仍未进行。
