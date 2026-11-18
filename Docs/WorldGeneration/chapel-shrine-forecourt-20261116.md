# 教堂正前方神像与圆形岩石底座

2026-11-16，按用户要求将丘陵神像放大一倍，加圆形岩石底座，移到教堂院子正前方的空地。

- 位置改为教堂局部坐标 `(-3140, 0)`，即院门外正前方 9 m；面向来路。角色出生点仍在原前院。
- 仅丘陵实例的神像网格使用 2 倍等比缩放，按实际网格底部贴合底座。六种随机神像共用该装配方式，不重导入原神像资产。
- 底座为封闭的双层圆形岩石台，原型半径 220 cm、高 34 cm，入土 4 cm，净高 30 cm。实际半径按每件放大后模型的水平包围范围适配，最小 180 cm；顶部保持平整，外缘有轻微风化缺口。材质复用教堂真实岩石贴图、凹凸及粗糙度。
- 同步预留神像周围 5 m 无植被空地，外围 2 m 与地形渐变衔接，保留角色入场区。底座具有与石台轮廓相符的实体碰撞，台阶允许现有角色正常踏上。
- 神像的战斗目标原点保持离地 100 cm，避免把怪物目标点抬到放大后模型中心；基座与神像同属现有可交互 Actor。赐福事务、夜袭耐久、次日恢复和当前种子不变。
- 组件跟随原神像 Actor 创建与销毁，无额外 Tick；网格跟随教堂异步预载，客户端按相同种子和边界装配。共享神像绑定明确选择神像组件，避免把底座替换成随机神像。

资产：`/Game/WorldGeneration/HillsNightRaid/SM_ChapelShrineRockPedestal`。作者入口 `Tools/WorldGeneration/author_chapel_shrine_pedestal.py`；源码备份、网格源与制作回执位于 `SourceAssets/ChapelShrineForecourt20261116`。

底座已实际保存，作者进程退出码为 0，见同批 `authoring-receipt.json` 与 `authoring-process-1.json`。六种神像放大后高度约 360–412 cm，底座实际半径约 180–186.5 cm。

Editor／Game 两个 Development 目标均已后台编译、链接成功，见同批 `FPSGAMEEditor-build.json`（日志后缀 `-1`）和 `FPSGAME-build.json`（最终日志后缀 `-2`）。没有进行游戏测试、截图或视觉验收；布局和生成地面会在下一次进入丘陵时按当前保存种子生成。

## 2026-11-16 底座支撑面与贴花修正（SupportFixR2）

针对用户截图中的悬空、底座材质错误，以及地面纹理覆盖手持物的问题：

- 已保存的底座三角面绕序与 UE 自带 Cylinder 相反，顶面从上方被背面剔除，形成神像没有支撑的外观。作者入口修正所有面的绕序，保留原有外向法线、双层轮廓与尺寸。
- 装配高度改为取底座实际包围盒：底部埋入生成地面 4 cm，神像模型最低点与底座顶面齐平，保持神像 2 倍缩放。
- 底座使用独立不透明石材 `M_ChapelShrinePedestalStone`，按 UV0 采样石材颜色、法线、粗糙度和 AO；材质贴花响应关闭。神像与底座组件均不接收场景贴花。
- 第一人称共用可见性处理补齐手部、衣袖和手持部件的贴花接收禁用；手持生产工具创建时也直接禁用。沿用已有组件遍历，不增加 Tick 或额外扫描。

后台制作入口：`Tools/WorldGeneration/save_chapel_pedestal_support_fix.py`。本次制作回执、旧底座备份和日志保存在 `SourceAssets/ChapelShrineForecourt20261116/SupportFixR2`。未取得用户退出前的游戏场景，因此没有断言截图中具体哪一个贴花 Actor 导致覆盖；修正范围是已找到的接收路径。

底座与独立材质已实际保存，后台制作退出码为 0，见 `SupportFixR2/save-process-4.json`、`support-fix-saved.json` 与 `authoring-receipt.json`。旧底座包保留在该批次 `Before` 子目录。

本批 Editor／Game 两个 Development 目标后台构建均返回 0，见 `SupportFixR2/FPSGAMEEditor-build.json` 与 `FPSGAME-build.json`。构建工具读取 Git 工作区曾超时并导致合并编译冲突；刷新工作区状态后使用正常构建完成，未修改其他模块来绕过冲突。

随机神像选择、赐福与夜袭逻辑、神像位置和地图种子保持原有设置。本批不启动游戏、不截图或进行视觉验收，交由用户测试。

## 用户要求自查后的补正

用户随后明确要求自行检查。重新读取磁盘模型后，发现狄安娜的实际几何底部高于网格包围盒底部，2 倍缩放后会留下 0.8846 cm 的缝隙；另外五种模型误差不超过 0.006 cm。装配增加 1 cm 的浅嵌入，六种神像的实际底面相对台面为 -0.1154 至 -1.0057 cm，保留原模型资产。

`SupportFixR2/Check/saved-assets-before-seat-adjustment.json` 保留首次发现缝隙的失败证据；`saved-assets.json` 使用引擎重新读取的几何与未改变的资源哈希，代入最终嵌入量后，17 项资源检查通过。包括 1536 个三角面的封闭性、面朝向及顶面法线、UV0、实体碰撞设置、独立石材贴图及输出、无世界投射节点、贴花响应和六种模型的实际接触高度。

`Check/native-build-provenance.json` 记录三个修复源码对应的 Editor／Game 对象文件与二进制时间。隔离运行入口为 `Tools/WorldGeneration/Check-ChapelPedestal.ps1`，复制正式丘陵存档到独立 UserDir，并使用复制的原生模块，只在该运行实例中定位相机和截图。

## 2026-11-17 复用教堂矮墙灰石材（WallStoneR3）

按用户反馈重新读取教堂矮墙的实际材质：墙身 Field 使用偏黄褐色的 `StoneSurface_02A`，压顶 Cap 使用灰色裂纹 `StoneSurface_01A`。底座改用压顶的 01A 颜色、法线、RHAOM 和高度贴图；保留独立底座材质，不修改矮墙或共用源贴图。

- 保留双层圆形轮廓、高 34 cm、入土 4 cm 和原位置。下层 28 块、上层 20 块，浅缝深 1.5 cm，边缘带倒角及轻微缺口。所有块石合并为同一网格、一个材质槽，共 4992 个三角面，不增加 Actor 或 Tick。
- UV0 按 50 cm／单位映射，单块错开纹理并加入轻微色差。灰色裂纹、法线与小幅 BumpOffset 提供石材细节，凹缝由几何和顶点色表现。显式保存纹理流送密度，避免近景选用过低的 mip。
- 仍使用不透明材质、关闭贴花响应、无世界投射和顶点位移；神像及底座不接收贴花，第一人称手部和工具的禁用逻辑保留。神像按实际台面浅嵌入 1 cm。

灰石材和新底座已实际落盘，制作退出码 0，见 `WallStoneR3/save-process-6.json` 与 `authoring-receipt.json`。作者脚本清理节点时改为遍历快照，避免 UE 5.8 的 DeleteAllMaterialExpressions 在修改同一集合时漏删旧节点。

引擎重新读取保存资产后，17 项检查全部通过，见 `WallStoneR3/Check/saved-assets.json` 和 `assets-process-2.json`：网格封闭、绕序及法线正确、UV 非退化、实体碰撞、四张灰石贴图和材质输出正确，六种随机神像均接触台面。源码的 1 cm 嵌入与贴花修复已完成 Editor／Game 构建，本次 R3 仅更新模型与材质资产。

在隔离的实际丘陵运行实例中，9 项场景检查通过，见 `WallStoneR3/Check/runtime.json`：当前 muse 神像浅嵌入 1 cm，9 个地面采样均确认底座入土 4 cm，16 次简单／复杂碰撞射线命中台面，24 个第一人称组件和生产工具均拒绝贴花。正式丘陵存档 SHA256 前后相同，种子仍为 1518277816。

已实际查看 `runtime-first-person.png` 和 `runtime-support-contact.png`：可见灰石裂纹、块石缝与双层台阶，神像底边与台面贴合，手臂和枪械未出现地面材质覆盖。截图为当前种子的 muse 神像与默认枪械；六种神像均完成保存几何检查，但未分别拍摄，也未逐件装备检查所有武器。

检查脚本完成、两张截图保存后，引擎在 `Game engine shut down` 和 `Object subsystem successfully closed` 之后出现空地址访问异常，进程退出码为 3。该退出异常尚未定位，不能把本次运行称为全程无错误；资源检查、9 项场景结果与截图是已取得的独立证据，见 `runtime-process.json` 及 `runtime-engine.log`。
