> 本页保留各阶段事实。当前五款容量、R2/R3 动态、开拓者接入及 2026-10-23 的后台联机覆盖，见[整理发布记录](../Publication/Backpacks20261023/README.md)。旧 R1 发布器已归档，不能据历史参数覆盖当前配置。

# 两款背包容量与军用包侧袋处理

日期：2026-10-21。用户要求军用背包两侧开口自然、细节优化，并检查两款背包代码，怀疑登山包未给主背包增加一行。

## 2026-10-22 行军包穿身修复与三款包惯性摆动

用户已认可重装远征包的原穿戴外观，本次新增摆动另待体验。用户截图指出行军包穿进躯干。实际读取旧挂点及原生参考骨架后，行军包包体中心为身体空间 `(0,-10.5,120)` cm，前侧达到 Y=+9.21 cm；它直接沿用了旧登山包挂点，没有独立贴合。六种身体／上衣包络中，旧帆布主体有 1,064–1,177 个顶点侵入，向后退出所需最大位移约 19.1–23.3 cm。这是实际位置错误，与前一轮修正的正反面问题不同。

修复保留原包体、侧袋开口、UV 和材质，并保留实际旧挂法的 180° Y 轴朝向；只取下两个完整的旧刚性肩带连通部件，另做六套贴身肩带、胸扣与腰封。包体重新置于背后，再按裸身、棉衫、野行上衣、锁甲、法袍和 ST6 分别校准。源几何参考姿势的包体退出量均为 0；此结论不等于所有动作均无接触。

摆动使用一套有阻尼的惯性弹簧，以移动加速度、实际脊柱姿态的角速度和锚点加速度驱动，奔跑脚步与落地来自原生动画和角色移动，不另造一个正弦步频。包体保持刚性；肩带和腰封贴身体的部分固定，连接包体的末端在 12 cm 长度内平滑过渡。动态变形只作用于穿戴资产，原静态展示源和图标保持原样。

| 背包 | 弹簧频率 | 阻尼比 | 最大摆角 | 最大垂直位移 |
| --- | --- | --- | --- | --- |
| 行军背包 | 3.7 Hz | 0.85 | 2.4° | 0.32 cm |
| 登山包 | 3.3 Hz | 0.82 | 3.0° | 0.45 cm |
| 重装远征背包 | 2.8 Hz | 0.94 | 1.8° | 0.24 cm |

逐帧在身体骨骼完成后更新，每步最多 1/120 秒；向身体一侧的旋转位移由包体支撑盒补偿向后位移，不消耗校准出的前后间隙。保存前一帧变形参数用于速度缓冲。换装、传送、超过 100 ms 的长帧、隐藏及布娃娃状态会重置；空闲时弹簧回到静止。控制台 `fps.Backpack.Sway 0/1` 关闭／开启。只复用角色现有移动数据，不新增 RPC，不改变碰撞、容量、重量规则或玩家存档。专用服务器不运行此表现组件。

实现为 `FPSBackpackMotionComponent` 与原换装入口的一处调用，材质使用共享的自定义组件数据，不逐帧创建材质或加载资产。三款包各六套变体输出到 `/Game/Characters/BackpackMotion20261022/`；登山包和远征包复制当前已保存几何及原 LOD，仅写入摆动权重和等价表面材质。行军包原静态源继续用于展示，实际穿戴由新骨骼变体负责。

18 个穿戴变体、11 个摆动材质和三款背包的配置已保存并切换，实际回执为 `SourceAssets/BackpackMotion20261022/saved_assets.json`、`published.json`。最终原生步伐驱动的正式 Editor／Game 构建均成功，记录为 `native_build.json` 和 `build-motion-r3-*`。几何诊断为 `alice_penetration_diagnosis.json`，方案和每模型参数为 `manifest.json`，交付总表为 `delivery.json`；未启动游戏或验收渲染。

后续重做源模型时，先完成原制作流程，再执行 `Tools/BackpackMotion/prepare.py`、后台 `save_assets.py`，并按当前 R2 配方执行 `register_response_refit.py`、`save_refit_r2.py` 与 `publish_response_r2.py`，同步更新骨骼变体、摆动权重与配置。不可只用旧发布器切回无摆动的源资产后仍声称已保留此功能。

### 远征包背带白色棋盘修复

用户随后反馈背带变成白色马赛克。实际游戏日志指出 `M_Motion_M_ExpeditionHarness_Fabric_b63f8c` 在 PCD3D_SM6 编译失败，原文为 `(Node Desaturation) Missing Desaturation input`，因而回落默认棋盘材质。源制作脚本将颜色连接到名为 `Input` 的引脚，但 UE 将此节点的第一个引脚缩写为空名，连接返回失败后旧脚本没有处理。

已在 `Tools/ExpeditionBackpack/save_assets.py` 改用明确选择第零输入的空引脚名，并处理颜色、去色比例和着色连接的失败返回。原始 `M_ExpeditionHarness_Fabric` 与当前穿戴用摆动副本均补回原 BaseColor 贴图连接，保留法线、粗糙度、金属度和 WPO 图。后台使用 `Tools/BackpackMotion/run_material_repair.ps1` 的 `-AllowCommandletRendering -RenderOffscreen` 启用实际 SM6 材质编译，不启动编辑器或生成验收图；普通 NullRHI 保存不能证明 shader 可用。

两个材质经 `GetStatistics` 等待实际着色器编译完成后保存，已取得有效顶点／像素着色器统计。回执为 `SourceAssets/BackpackMotion20261022/FabricRepair/saved.json`，修复前资产保留在同目录 `Before/`。未运行游戏或做视觉验收。

## 2026-10-22 军用背包正反面检查与修复

用户确认登山包 R6 修复成功后要求检查军用背包。该轮 `ue_portable_backpack` 使用原静态 `SM_AliceBackpack`，1 个 LOD，Nanite 已启用；五个材质均为单面不透明，没有 Opacity／OpacityMask／WPO 输入。

从正在运行的编辑器只读导出 SourceModel 与 RenderData，二者均为 34,201 个三角形，其中 34,133 个面的法线与 UE 正面约定相反。原因与登山包相同：Blender 源经 Z 反射后又反转面序，导出结果保留作者空间的 `cross(e1,e2)`，保存器却未转换到 UE 的 `cross(e2,e1)`。原源几何检查没有覆盖这个接口。

当前 `AliceUEFrontFaceR2_20261022` 的保存入口使用背包专用 `winding.py`，将三角形及其 UV／法线面角一起重排，保持挂载、位置、侧袋开口、材质和 UV 不变；少量微小倒角面的保留法线在实际 float32 几何下反向，局部修正了 68 面。既有内衬材质直接复用，不重建材质图。导出器明确写入作者空间约定，旧 OBJ 写入器的防覆盖规则继续保留。

保存后重新读取实际 SourceModel 与 RenderData：两个数据集反向面均为 0；三角形集合、面角 UV 和材质映射在重排面序后与修复前完全一致；五个材质槽一致。两侧袋口四处采样均有内侧表面且朝向射线正面，原 4.2–4.6 cm 凹入深度及皮带／扣具保留。未填平用户要求的侧袋开口，也未改变 Nanite 或增加 LOD。

检查及实际保存记录位于 `SourceAssets/BackpacksReview20261021/FacingRepair20261022/`。本轮沿用已打开的编辑器完成；请求保存前的 PIE 状态返回无运行会话，因此没有实际结束 PIE。未启动新编辑器、游戏或进行验收渲染，军用包实际运行效果仍由用户确认。下方容量与编译记录属于 2026-10-21，本轮未修改容量代码，也未重跑容量测试。

## 军用包两侧

本轮按 `ue_portable_backpack`（行军背包／ALICE）的两侧侧袋处理。原侧袋顶盖和袋身是一整块鼓包，缺少可读的袋口层次。

- 在原侧袋顶盖下方形成约 10.2 cm 宽、5.5 mm 缝隙的开口，边缘带轻微弧度。
- 袋口有内凹衬壁，源模型射线测得深度约 4.2–4.6 cm；开口停在侧袋内，没有切通主包。
- 上下各有约 1 mm 实体布边，皮带从袋口前方完整经过，原搭扣及背带保留。
- 使用原有帆布／织带／皮革／金属材质，新增 `M_Alice_PocketLining`。不重烘整包、不改既有穿戴挂载参数。
- 新网格已写入原 `SM_AliceBackpack` 包，保持原轴向、枢轴和包围盒；保存后几何数读回为 34,201 三角形、五个材质槽。
- 320×320 透明图标已按新网格更新到 `Content/ColdSteelData/Icons/ue_portable_backpack.png`。

源几何核对同时发现旧低模中退化的三角片和塌缩扣具 UV。导出器删除没有有效面积的微小片，并给原扣具退化壁面单独投影；其余皮带、搭扣、织带的有效三角形集合保持一致。具体统计与哈希见 `SourceAssets/BackpacksReview20261021/alice_authored.json`、`alice_geometry_checks.json`。源预览位于该目录 `Preview/`，属于 Blender 画面，不是 UE 游戏截图。

旧 `build_alice_ue.py` 在新版本已保存后拒绝用旧 OBJ 覆盖。旧发布器改用共享配置事务，并保留现有挂载值，只更新网格引用；本次没有重跑它去修改玩家配置。

## 容量结论

| 状态／物品 | 主背包 | 独立夹层 |
| --- | --- | --- |
| 未装备背包 | 18×4＝72 格 | 无 |
| 行军背包 | 18×5＝90 格，增加 1 行 | 6×6＝36 格 |
| 登山包 | 18×5＝90 格，增加 1 行 | 5×6＝30 格 |

两款包互换时主背包行数相同，扩行不叠加。配置 `bagExtraCells` 均为 18，数据没有漏配。

只读检查六份现存 `ColdSteelPlayer`／PIE A/B 存档：登山包都在 Place 1、Cell 14，保存的 `bagExtraCells` 已是 18，规则读到 5 行。因此未在这些实际存档里复现“当前登山包只给四行”，不把下面的旧数据缺口当作已证实的本次现场根因。

## 逐路径代码检查

| 路径 | 结论／修改 |
| --- | --- |
| `Content/ColdSteelData/items.json` | 两款容量配置正确，保留数值 |
| `ColdSteelInventoryRules.cpp` | 旧 BagRows、CompartmentGridOf 及换包目标边界直接依赖实例 JSON 快照；改为按定义读取缓存目录容量。未在目录中的自定义物品仍按自己的数据处理 |
| `ColdSteelProfileRuntime.cpp` | 原容量同步仅在本地 ReloadProfile 后段；网络镜像／影子模型未走同一段。保留本地同步，统一规则层读取使各路径结果一致 |
| `ColdSteelCompartmentRules.cpp`／`ColdSteelWarehouseRules.cpp` | 使用共享容量、换包回填和原子 proposal；未添加第二套容量公式 |
| `ColdSteelInventoryWidget.cpp` | StorageRows、布局高度、鼠标格位和键盘边界均动态读取 BagRows，未找到固定四行的活动路径 |
| `ColdSteelHUDWidget.cpp` | 旧 MakeInventoryGrid 有四行样板常量，但没有活动调用；不误改样板来冒充修复 |
| `ColdSteelInventoryPresentation.cpp` | 增加“空间背包 · 5 行（+1）”说明，扩展区淡底色和第 4／5 行分界，延用横排和现有冷钢样式 |
| `ColdSteelItemTooltipData.cpp` | 扩容量和夹层说明改读与放置规则一致的接口，避免旧实例浮窗与实际容量不一致 |
| `FPSPlayerBodyEquipment.cpp` | 装备外观与容量职责独立；保留登山包按上衣选骨骼变体、军用包静态模型和两者槽 14 互斥 |

容量目录仅首次读取一次，缓存只保留背包定义；未新增 Tick、逐帧磁盘读取或全目录刷新。装备状态仍从当前物品列表读取，单纯携带背包不授予容量。

## 本轮检查与交付边界

`BackpackCapacityAuditCommandlet` 在内存构造两款背包的当前／缺字段／零字段旧快照，核对装备后 90 格、第 90 个格位可用、第六行拒绝、携带无加成、卸下回填、6×6 换 5×6 夹层回填和满包拒绝卸下。32 项通过、0 失败，记录 `SourceAssets/BackpacksReview20261021/capacity_checks.txt`。

同一 commandlet 只读真实存档，没有创建游戏实例、保存档案、运行角色或改动物品位置。前面的 Python 读档尝试因反射保护无法读取 Profile，已改用 C++ 只读入口，并删除失效 Python 脚本。

Editor 和 Game 正式构建均已成功（日志 `Saved/BuildEditor/build-20261021-162811.log`、`SourceAssets/BackpacksReview20261021/build_game.log`）。最终文件哈希见本轮 `delivery.json`。侧袋实际保存回执为 `alice_saved_assets.json`。

未启动编辑器／游戏或执行真实联机、Slate 鼠标验收；侧袋自然度和新增行的界面表现由用户体验。登山包上一轮尚未完成的右肩／衣袖动作交叉仍见 `backpack-harness-rebuild-20261020.md`，不因本次容量检查而标记解决。
