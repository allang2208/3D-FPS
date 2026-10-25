# 背包装备：容量、贴身适配、动态与联机

维护于 2026-10-24，适用工程 `D:/FPS3D/FPSGAME`。用户已认可单肩包 GravityFitR3 的贴身、下垂及背带联动表现；这不代表所有动作、网络传输或打包成品已验收。默认后台制作、构建和保存；检查及测试只在用户要求时执行。

背包正反、统一模型方向、背包栏主图或 PNG／实时图标不一致时，先读[统一朝向与正面图标标准](backpack-facing-standard.md)。全款默认展示外侧正面，正交平视、顶部朝上；标准落盘与旧资产重制分别记录。

## 当前款式与容量

尺寸为横向列数 × 纵向行数，真源为 `Content/ColdSteelData/items.json`。

| ID / 名称 | 物品占格 | 主背包增加 | 独立夹层 |
|---|---|---|---|
| `ue_simple_sling_bag` 简易斜挎包 | 2×3 | 18 格，1 行 | 3×4 |
| `ue_portable_backpack` 行军背包 | 3×3 | 18 格，1 行 | 6×6 |
| `ue_mountain_backpack` 登山包 | 3×3 | 18 格，1 行 | 5×6 |
| `ue_expedition_backpack` 重装远征背包 | 3×4 | 36 格，2 行 | 8×6 |
| `ue_pathfinder_backpack` 开拓者战术背包 | 4×4 | 54 格，3 行 | 10×6 |
| `ue_farreach_backpack` 远界智能远征背包 | 4×4 | 72 格，4 行 | 12×6 |
| `ue_special_duty_backpack` 特勤重载远征背包 | 4×4 | 90 格，5 行 | 14×6 |

- `equipSlot:"backpack"` 对应装备槽 14；`grid_w/grid_h` 只表示物品自身占格。
- 主背包宽 18 格、默认 4 行；`bagExtraCells/18` 为新增整行。背包放在物品栏里不会提供容量。
- `bagCompartmentCells>0` 表示有夹层；实际容量为 `bagCompartmentColumns × bagCompartmentRows`。缺省 6×6，列数上限 18、行数上限 24。
- 容量按目录定义 ID 解析并缓存，旧实例快照／网络镜像不能独立决定容量。装备不写顶层 `rarity/grade`。
- 夹层是 `Place 5`，快捷栏计数和消耗覆盖主背包、夹层。卸包／换小包使用同一库存事务重排，放不下则完整拒绝；详情浮窗读取同一组字段。
- 校验时先用完整物品列表计算容量，再逐件验证，不能依赖装备在数组中的先后顺序。

## 模型与接触适配

1. 保留用户 Meshy GLB、已认可轮廓、PBR 与面数；修改使用新修订目录，保留 UV、硬边法线、厚度及作者源。
2. 分清包体、肩胸固定区、自由带段和扣件。侧面漏空追到源几何、绕序、剔除及运行时裁剪；只移位置或改双面材质不能替代补壳。真实侧袋开口保留袋口与内里。
3. 用当前保存的身体和实际衣物表面标定；AABB 不能代替接触面，旧 Manny 数值不能套到 Jason。当前 Jason 参考空间朝前 +Y、背部 −Y，实际骨骼绑定变换仍从当前网格读取。
4. `world_mesh` 是默认贴身骨骼件，`world_mesh_by_shirt` 按槽 7 上衣选择。目前覆盖裸身、薄棉、针织、锁甲、法袍、ST6。网格、刚体位置和接触代理必须从同一份 Outfit 选择。
5. 高细节包体可保留共享 Nanite 静态件，肩带单独蒙皮。`rigid_pack` 提供网格、位置、四元数、`location_by_shirt`。包体与背带缝接端共享一个动态变换。
6. `world_static_mesh` 保留完整展示／拾取源及图标用途；贴身骨骼件加载成功后不再渲染第二个完整静态包。

导入细节沿用当前背包工具的实证约定：作者 NumPy/Blender 三角形经过 `Tools/BackpackHarness/winding.py` 转为 UE 绘制面序，同时重排 UV／法线面角，不能只反转法线向量。非均匀缩放需同步变换自定义法线；程序化收整旧带片必须保持连续且非零的局部导数，避免压扁或翻转包壳。位置合并不能抹掉 UV 和硬法线接缝。作者空间闭合检查与 UE 实际 RenderData 正面检查是不同证据，不能混用。

新增武器、帽子、鞋靴通常不需要重新适配每个背包。只有肩、胸、背轮廓改变的上衣／体型才补对应适配；相同轮廓族优先复用。未知上衣会回退默认件，但不能据此保证厚衣物不穿模。

## 双肩包：有界惯性

三款双肩包当前为 `BackpackResponseR2_20261022`。运行组件 `FPSBackpackMotionComponent` 在身体姿态完成后读取运动加速度、躯干角速度和真实步态锚点变化；这是带阻尼的装饰惯性，不是自由布料。

- 肩胸固定段权重 0，包体与缝接端为 1，自由段平滑过渡；扣件、边缘和两侧表面跟随所属结构。
- 同时限制角度、跳动和总行程，最后 30% 行程软化，避免多个方向叠加拉长短带段。
- 支撑框产生向后补偿，使摆动不减少标定间隙；它不能替代所有衣物、极端姿态的真实接触求解。
- 行军／登山／远征当前总行程上限 2.2／2.5／1.8 cm，仅对应这三个模型，不作为新品通用参数。
- 登山包针织件使用 `/Game/Characters/BackpackMotion20261022/MountainR2/`，扣件与肩垫一同修正，不能单独恢复旧肩垫。

工具为 `Tools/BackpackMotion/`，当前回执为 `SourceAssets/BackpackMotion20261022/motion_response_r2.json`。历史 72 个原生动画组合与参考接触采样只代表记录范围，不代表本次重新测试或全部联机动作通过。

开拓者战术背包的初版为 `PathfinderMeshyHarnessR1_20261023`，复用同一有界惯性组件：共享 Nanite 包体保留用户 GLB 的 193071 个三角面，六套贴身骨骼背带分别适配上衣。完整空载展示源与穿戴源分开保存，展开的原模型肩腰带向背板平滑收整，穿戴带段另行贴合；保留所有原始壳面、UV 与法线，不删除侧面封壳。当前总行程上限 1.7 cm。工具为 `Tools/PathfinderBackpack/`，接入回执为 `SourceAssets/PathfinderBackpack20261023/published.json`，本次检查范围见同目录 `Audit/review.json`；已保存资产、编译材质并接入，后台组件和同机 socket 联机检查通过，视觉仍待用户验收。新增模型不需要在运行时代码写 ID 分支。

### 开拓者朝向与衔接修订（2026-10-24）

当前生产入口为 `Tools/PathfinderBackpack/` 的 `PathfinderOrientationFitR2_20261024`，产物位于 `SourceAssets/PathfinderBackpack20261023/OrientationFitR2_20261024/`，UE 资产使用同名新子目录。GLB 对象采用四元数旋转，直接修改 `rotation_euler.z` 曾未生效，导致包体和图标正反颠倒；须使用世界矩阵旋转并应用到顶点／法线，外侧 −Y、贴背侧 +Y，再进行贴背带收整。R1 的旧检查不能证明这一视觉朝向正确。

按当前 Jason／Kaitlin 保存身体制作各六套背带，包含裸身和五种上衣；额外读取扎腰上衣及各 22 个裤靴网格的腰部表面。肩带／腰封两端使用真实包体缝接点，原生骨骼权重和动态遮罩在缝接端一致。女性肩高和本包 8° 局部倾角独立标定，不能套到其他背包。保持 193071 个三角面、原 UV、PBR 和既有有界惯性，不增加逐帧求交。

完整显示源、实时图标的 `world_static_mesh`、目录 PNG 和固定命名 PNG 回退一同修正，旧物品实例依然可读正确图像。接入同时更新根 `outfits.ue_pathfinder_backpack` 和 `body_variants.kaitlin.outfits.ue_pathfinder_backpack`，用字段事务保留其他装备；目录与旧快照的 PNG 路径保持不变。`FPSBodyEquipment::OutfitDefinitions()` 每进程缓存图标显示源，当前已打开编辑器须由用户重启后查看完整更新，不自动重启。

保存状态见该修订的 `saved_assets.json`／`published.json`；本轮按用户要求检查参考姿态包络采样、缝接蒙皮和离线模型视图，未进行游戏动作或联机验收。详细记录为工程 `Docs/Characters/pathfinder-backpack-orientation-repair-20261024.md`。现行输入入口 `read_body_inputs.py` 转到 `read_fit_r2.py`，不要再将 R1 身体快照当作当前适配。

### 远界智能远征背包（2026-10-24）

用户提供 `Meshy_AI_Titan_Pack_1024035624_texture.glb`，当前制作入口为 `Tools/FarreachBackpack/`，源与保存回执位于 `SourceAssets/FarreachBackpack20261024/MeshyFitR1/`。保留原 GLB 的 193526 个三角面与 PBR，按原比例统一缩放至 60 cm 高，未重新塑造用户外壳。显示源正面 −Y；穿戴源收整原空载肩腰带，独立制作 Jason／Kaitlin 各六套肩带、胸带和腰封。接触输入包含当前扎腰上衣和各 22 个裤靴网格，包体与缝接端共用有界惯性；本款总行程上限为 1.4 cm。

容量按用户最终指定为主包增加 4 行、夹层 12×6、自身 4×4；同时将开拓者夹层调整为 10×6，其他容量不变。缩小夹层沿用现有旧网格迁移，溢出物品依次放入新夹层空位、主包和主仓库，不直接改玩家存档。新增物品显式配置 `world_mesh`，使用已有物理拾取入口。保存与本地接入以 `saved_assets.json`、`published.json` 为准，本轮未运行游戏、存档迁移或联机测试。

正式目录图标通过 `run_stage.ps1 -Stage export_icon` 调用 UE 同一图标棚，定向输出 `Icons/ue_farreach_backpack.png`。制作完整记录见 `Docs/Characters/farreach-backpack-integration-20261024.md`。已有五款检查夹具不能自动证明远界已覆盖。

### 远界细长与贴背修订 R2（2026-10-24）

用户反馈 R1 过宽、男女角色均离背过远，当前生产入口转为 `FarreachSlimFitR2_20261024`，资产与回执位于 `SourceAssets/FarreachBackpack20261024/SlimFitR2_20261024/`。显示源宽×高为 52×70 cm，保留全部 193526 面、UV 和 PBR；非均匀比例须同时变换法线，不能只缩放位置。穿戴源单独收整旧空载带片，保持连续非零导数，不删除壳面。

不能只按上背斜率定安装角，再让突出腰带把整个包体顶开。使用真实包体后表面和完整躯干／腰部求安装角，再针对各上衣解包体位置；肩带、胸带、腰封、缝接点和动态枢轴同批重做。男女各六套，容量及其他背包不变。制作细节见 `Docs/Characters/farreach-backpack-slim-fit-20261024.md`；已保存与接入状态以本修订回执为准，未运行游戏或联机测试。

### 特勤重载远征背包（2026-10-24）

第七款由用户正式命名为“特勤重载远征背包”，使用 `Meshy_AI_Rugged_Expedition_Pac_1024095908_texture.glb`；旧概念名“界航”不再作为生产名。入口为 `Tools/SpecialDutyBackpack/`，源与回执为 `SourceAssets/SpecialDutyBackpack20261024/MeshyFitR1_20261024/`，ID 为 `ue_special_duty_backpack`。原比例统一缩放至高 72 cm、宽约 44.41 cm，保留 195009 面、UV 和 PBR，不横向压缩。

按真实后背垫收整原空载带片；男女各包含裸身和六件当前上衣，共 14 套贴身背带，额外覆盖 `ue_work_jacket`。发现旧输入缺少新上衣时，应按当前配置补取实际保存表面，不能只复制固定五件上衣清单；贴身入口从当前配方补齐新增上衣。完整背部／腰部与本款后表面共同求安装角和偏移，缝接点、腰封、肩胸带及动态枢轴一并制作。

容量沿用模型交接前的草案：主包＋5 行、夹层 14×6、自身 4×4。Cook 与拾取模型单独登记，图标采用同一 UE 图标棚正面导出。保存和接入状态以本款 `saved_assets.json`、`published.json`、`Icon/exported.json` 为准；没有执行游戏或联机测试。详细记录为 `Docs/Characters/special-duty-backpack-integration-20261024.md`。

## 单肩包：已认可 GravityFitR3

运行入口 `FPSBackpackHangingMotion.cpp`；资产 `/Game/Characters/SimpleSlingBag20261022/GravityFitR3/`。保留共享高细节包体，肩带单独蒙皮，使用轻量刚体接触代理。

- 固定肩胸带段贴身；从真实包顶与下端缝口定义两处挂点，不用裁切面中心充当挂点。
- 世界重力使包体下垂；两条带长约束只抵抗拉长、允许松弛，不锁在悬空偏移上。
- 身体与上衣生成随骨骼运动的低密度躯干凸代理，包体探针限制进入身体。分段端盖只判断范围，向外推离仅用侧面，避免卡在分段台阶上。
- `hanging_pack`、`hanging_pack_by_shirt` 保存中心、挂点、长度、骨骼绑定、躯干代理和接触探针，必须与对应刚体位置及背带资产同时发布。
- 作者合同：2 条约束，最多 6 个凸段、24 个探针；当前使用 20 探针。固定迭代及子步，不在运行时扫描高模。这不是全包体、手臂或环境碰撞。
- 包体与背带共用姿态；自由段连接包体，肩胸固定区保持贴身。材质保留 PBR、当前／上一帧 WPO 以及法线旋转，不能把遮罩顶点色输出为织物颜色导致白色马赛克。
- 当前／上一帧场共占 30 个 CPD 浮点；位移范围、材质 WPO 上限和网格 bounds 同步维护。

制作顺序：`Tools/SimpleSlingBag/read_gravity_body.py` 读取保存源 → `author_gravity.py` 生成贴身件和代理 → `save_gravity_assets.py` 真正保存资产 → `publish_gravity.py` 按字段接入。只有脚本不算资产已导入。

用户 2026-10-23 回复“不错，记入背包工作流中”，认可记录在 `SourceAssets/SimpleSlingBag20261022/GravityFitR3/published.json` 与 `design.json`。范围为上述视觉方案，不延伸为后续代码或联机验收。

## 联机、复位与存档

- 装备和容量由服务器库存规则决定。服务端远端角色使用 `GetNetShadowProfile()`；`ReplicatedOutfit` 同步槽号与定义 ID，`OnRep_Outfit` 在观察端重建表现。初次出现、晚加入及换衣沿用此路径，远端不能读取观察者自己的衣柜。
- 摆动是各观察端本地装饰状态，没有逐帧 RPC，不要求各端角度完全相同。独立服务器不运行背包动态，不参与命中、库存或存档。
- CMC 网络纠偏会先移动胶囊，再平滑可见身体。传送复位根据身体组件的位置跳变，不能仅看胶囊跳变，否则身体未动时包体会弹回初始位置。
- 换装先 `Clear` 清理 CPD、刚体状态及接触代理，再销毁旧件、Configure 新件。真实传送、长帧、隐藏和布娃娃复位历史；前帧 WPO 同时重置。换身体骨架重新解析骨索引与绑定变换。
- 异步装备请求身份包含身体类型与身体网格；切换身体前取消旧请求并清理旧装配。不能只用装备 ID 去重，否则相同装备在 Jason／Kaitlin 间切换会保留旧骨架配件。
- 旧原生动画／骨架导入后，应由后台 commandlet 保存当前曲线元数据；编辑器链接的 `-game` 进程没有 `GEditor`，加载尚未迁移的旧曲线元数据可能触发编辑器事务空指针。保存前备份包，不能把动画资源落盘与实际动作验收混为一谈。
- 改夹层列数会改变 `Cell` 的行优先索引含义。先按旧网格校验并迁移，再按目录新网格校验，最后发布；不能先覆盖字段再解释旧位置。远征包 6×8→8×6 已发生过因此拒绝旧档的问题。
- 客户端上传在服务器物品净化后、最终结构校验前也执行共享布局迁移；不能只依赖本地读档／创建影子档案的较晚迁移。失败保留原档，不用初始角色覆盖。

## 发布与按需检查

- 新衣物配对统一走 [贴背与新增衣物制作](D:/FPS3D/FPSGAME/Docs/Characters/backpack-contact-workflow.md) 的 `Tools/BackpackFit/run.ps1`。按当前目录枚举双身体、上衣及裤装变体，用实际源散列补做变化组合；工装和裤腰制作入口已自动调用。`world_mesh_by_shirt`、`rigid_pack.mesh_by_shirt/location_by_shirt` 和单肩包动态配方成套发布。未制作的新衣物回退不代表已贴合。
- 双肩包已补显式受背带支撑的重力下沉，按款 0.4–0.6 cm；向后避让上限 0.65–0.75 cm，超限优先收小摆角。运动支撑边界/枢轴随上衣选择，只统计货舱，不包含前胸带。斜挎仍走带长与躯干接触的悬挂求解，不能把它的自由下垂直接套给双肩包。
- 参考姿态接触检查的新入口为 `BackpackCapacityAudit -ContactOnly -ReportDir=...`，动态枚举当前款式和上衣，记录斜挎稳定姿态及当前资源选择；它不替代实际动作和联机验收。新包体配对目录 `BackpackFit20261024` 已加入 Cook。

- 写 `player_body.json` 使用 `Tools/PlayerBody/config_transaction.py::commit`，声明具体字段。旧整款发布器可能覆盖新的动态字段，复用前确认现有修订归属。
- JSON 字符串不会自动成为 Cook 依赖。显式包含 `BackpackMotion20261022`、`PortableBackpackAlice20261019`、`ExpeditionBackpack20261022`、`SimpleSlingBag20261022`、`PathfinderBackpack20261023`、`FarreachBackpack20261024`、`SpecialDutyBackpack20261024`；材质纹理由网格资产依赖携带。ColdSteelData 原始 JSON 使用 Build.cs 的 UFS 规则。
- 用户要求检查时：`BackpackCapacityAudit -SyntheticOnly` 覆盖七款容量和旧布局（当前 111 项）；`-LifecycleOnly` 覆盖五款 × 六套上衣配置的实际组件纠偏、传送、清理、换衣重新绑定；两者可用 `-ReportDir=` 独立保存本轮回执。`-MotionOnly`／`-MotionOnly -OtherPacks` 检查既有单肩包／三款双肩包的原生动画动态，不能据此声称新增款已覆盖。无界面检查不写真实玩家档案。
- 当前实际 socket 入口为 `Tools/BackpackFit/run_network_review.ps1`，默认七款，也可用 `-Packs` 限定；`Tools/PathfinderBackpack/run_wire.ps1` 保留为开拓者兼容入口。仅用户要求联机检查时运行，自动等待 UE 批次互斥。独立 `ColdSteelProfile` 与 `UserDir` 隔离正式存档，各端 60 ms 延迟、3% 丢包，保留正常世界重力和异步预加载。每款规划 14 个男女身体、换包换衣、卸包、角色重建阶段，再同档重连检查最终状态；特勤款增加晚加入观察客机。只有实际生成且通过的回执才算覆盖，不以夹具代码代替结果。无界面检查不等于奔跑渲染、完整死亡流程、专用服或跨机打包验收。
- 组件模拟不等于 socket 联机。实际联机另列主机看客机、客机看主机／其他客机、换包换衣、晚加入／重连、延迟丢包及死亡重生；未运行就标待验收。
- 2026-10-25 本轮实际完成斜挎、行军、登山、重装远征、开拓者五款，各 15 阶段，共 75 项通过；用户要求在开拓者之后停止，因此远界、特勤和第三观察客机未继续执行。当前结果见 `Docs/Characters/backpack-network-review-20261024.md` 与 `SourceAssets/BackpackFit20261024/NetworkReview/final-review.json`。斜挎应检查挂点带长/躯干支撑，不能仅以包中心向下位移的正负判断悬空。
- 分别报告源码、构建、保存资产、配置引用、后台检查、用户认可和实际联机结果。历史回执及编译成功不能代表全部通过。

## 整理与源码交付

退役先检查制作链的导入和输入引用：例如 `SimpleSlingBag/author.py`、`save_assets.py` 虽属于早期阶段，仍被 GravityFitR3 和新包导入器复用，不能仅按版本名归档。旧发布器、一次性脚本、失败概念和回退快照可移入 `trash`，保留逐文件原路径、目标、字节数、SHA-256、理由与替代入口；不要移动仍被生产脚本读取的原模型、贴图、身体快照和中间母版。

公开源码清单应同时包含当前七款目录项、对应 `player_body.outfits`、Cook 目录、容量迁移、表现消费者和制作脚本。混合共享文件按当前索引构造本功能差量；尚未公开的联机宿主前置需列明并保留具名前置补丁，不能复制其他功能来凑完整构建。模型、纹理、UE 包和玩家／测试存档默认不公开；完整本机检查不等于干净检出构建。工程交付参考 `Docs/Publication/Backpacks20261023/README.md`，该历史清单未包含后增远界及特勤款。
