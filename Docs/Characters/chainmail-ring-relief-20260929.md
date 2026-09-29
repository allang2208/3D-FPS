# 灰钢锁子甲：参考锁环高模与表面视差

本页记录第一版。当前活动家族已更新为 `ChainmailInterlace20260929`，交错环源、实体袖口、分槽材质和接入记录见 [V2 制作记录](chainmail-interlace-v2-20260929.md)。下文原有面数和材质合同保留为历史记录。

用户要求按提供的银灰锁子甲参考图优化衣袖表面，允许贴图位移方案。物品仍为 `ue_chainmail_shirt`；独立上衣槽、现有衣袖形状、骨架、权重、动作和战斗属性保持。

## 本轮表面与高模

- 从原先约 0.7 mm 的细密金属织层，改为约 5.8 × 6.4 mm 外径、0.82 mm 线径的可辨识锁环。
- 锁环按行错开、交替约 ±35° 倾斜，形成参考图的重复交叠和明暗层次。细微不齐与锻纹打破理想光滑圆环；属于视觉交叠模型，没有进行锁环刚体或制造工艺模拟。
- 环孔中保留暗色非金属织物衬底；金属环和衬底的颜色、粗糙度、金属度分别烘焙。没有把整张材质的金属度统一为 1，也没有用透明孔暴露手臂。
- 周期单元为 39.2 × 24 mm，包含八列八行及烘焙边缘余量。真实锁环高模共 121 个环、991,232 个四边形，保存在 `Chainmail_RingTile_HIGH.blend`。
- 在现有 M4 双臂衣袖上细分并按该锁环高度实际位移，保存 754,752 个多边形、760,254 顶点的手臂高模。保留原生骨架及权重来源，标记 `BakeOnly/NoRuntimeExport`；游戏不加载这个高模。

用户参考图只用于形状、排列和材质意图，保存在本机作者目录的 `UserReference.png`，不是投射到衣服上的截图纹理。

## 烘焙和运行材质

四张 2048×2048 的 BaseColor／ORM／Normal／Relief 从真实锁环高模烘焙，法线与高度同源。ORM 为遮蔽／粗糙度／金属度；Relief R 为相对 4.4 mm 高度范围的归一值，G 为金属环区域，B 为几何遮蔽。

衣袖继续使用原有按 25 cm 标定的 UV；平铺次数按新周期单元换算，纹理跟随蒙皮。UE 导入采用 Wrap、mip、流送、无多余 alpha；BaseColor 开 sRGB，其余关闭，法线使用 Normalmap 压缩并按本次 Blender 输出翻绿。

穿戴材质采用 Default Lit、共享偏移 UV 的浅层视差：

- 在当前蒙皮三角形上用位置／UV 导数换算厘米到纹理偏移，颜色、ORM、法线同步采样。
- 当前深度参数 0.40 cm，上限 0.44 cm；最多 10 次搜索和 2 次细化，偏移长度限于 0.10 个周期 UV。
- 随距离约 85–260 cm、掠射角及较粗 mip 衰减，搜索放在条件分支内。完整搜索最多 15 次纹理查询，禁用搜索时为颜色／ORM／法线 3 次。
- 只改变表面采样，不改变游戏轮廓、碰撞或关节运动。衣袖实体厚度和褶皱继续来自原网格，没有 WPO、逐环骨骼、刚体或 Chaos 模拟。
- 第三人称穿戴沿用同一个装备材质，依靠距离／mip 衰减；不是单独关闭视差的 Body 材质。掉落物使用 `MI_Chainmail_Rings_Standard`，深度参数为 0，跳过视差搜索。

## 实际接入

已通过当时运行中的 UE 编辑器互斥桥导入并保存四张纹理、一个主材质、一个普通材质实例，共六个 UE 资产，目录：

`/Game/Characters/ModularOutfit20260924/ChainmailRelief20260929/Materials/`

之后编辑器进入 PIE；网格复制批次在写入前被运行状态阻止。本任务改用已有装备材质覆盖合同完成接入，没有结束用户游戏，也没有重新导入／复制衣袖或掉落网格。

- `modular_outfits.json`：保留已有 22 个 `rig_meshes` 路径，将衣服 `material` 指向已保存的新主材质，家族更新为 `ChainmailRelief20260929`。
- `items.json`：保留物品 ID、类别、槽位、数值、占格与掉落网格，只更新材质、描述和统一图标。
- 现有组件的单一材质覆盖适用于本件单材质衣袖；不能把此设置推广到露指皮肤或钢甲多材质装备。
- M4 衣袖游戏 LOD0 沿用原有 15,724 三角形，各原生网格、蒙皮和 LOD 未修改。该数来自此前资产读回，本轮不重新进行面数审计或帧率测量。

配置在下一次游戏会话读取，新版图标也按物品缓存生命周期刷新。当前 PIE 保持运行，未声称当前已在屏幕上热更新。

## 图标与可编辑源

使用当前整件衣服展示模型与新版 PBR 制作 320×320 RGBA 透明图标；背包、装备栏、仓库共用：

`Content/ColdSteelData/Icons/ChainmailRelief20260929/ue_chainmail_shirt.png`

作者源根：`SourceAssets/ChainmailRelief20260929/`。

| 文件 | 用途 |
| --- | --- |
| `Chainmail_RingTile_HIGH.blend` | 真实交叠锁环及烘焙单元 |
| `M4_ChainmailSleeves_HIGH.blend` | 带原生骨架来源的双臂高模与原游戏网格 |
| `ChainmailShirt_Presentation.blend` | 独立装备图标编辑场景 |
| `Textures/` | 四张生产材质图 |
| `before.json` | 制作前本件配方和物品快照 |
| `production.json` | 实际制作数量与作者输出 |
| `materials-saved.json` | UE 材质和贴图保存回执 |
| `published.json` | 最终配方、图标、保存资产及未测试状态 |

制作入口：`Tools/ModularOutfit/build_chainmail_relief.py`、`chainmail_relief.ush`、`import_chainmail_relief.py`、`publish_chainmail_relief.py`。最后一个仅发布已保存材质的配置，不启动 UE 或重导模型。

旧 `author_chainmail_shirt.py --presentation-only` 已按活动家族转到新版图标；旧整套制作／导入入口识别新家族后停止，避免误恢复细密旧材质。旧源仍保留为版型、绑定及独立图标场景的依赖。

日志：`Saved/chainmail-relief-production-20260929.log`、`Saved/chainmail-relief-materials-20260929.txt`。接入完成标记 `CHAINMAIL_RELIEF_PUBLISHED ue_chainmail_shirt 22 existing profiles; six saved material assets`。

本轮已完成制作、正式图标、材质必要编译与保存、配置接入；未启动新编辑器、游戏或额外验收，没有进行动作、视觉或 FPS 测试。交叠观感、各武器姿态和不同光照下的效果交由用户游戏内测试。
