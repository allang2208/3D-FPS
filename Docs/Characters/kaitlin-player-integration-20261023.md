# Kaitlin 女性玩家制作

## 2026-10-24 审查缺项补齐

本轮按用户“继续完成”处理审查列出的两处联机问题、家具同步和夹克背包配对，源码及运行资产均已落盘。

- 联机整档回传保留本地最新 `PlayerHeadId/PlayerHairId`。客户端分别记录实际完整上传中的外观身份；库存快捷分支要求该身份已经上传，库存回执不能把尚未发送的外观变更当作已同步。心跳、物品请求和篝火上传均携带对应快照身份；不新增 RPC 或存档字段。
- 18 个女性床铺映射已发布，其中 12 个进出动作重新跟随当前 `BedHandDriveV10` 来源，6 个未变化的已保存 Idle 资源复用。另从当前女性原生面部眼位和实际动画生成 54 条家具眼位轨迹，身体切换时重建缓存，坐卧相机按对应女性轨迹采样。
- 六款背包各补 Jason/Kaitlin 工装夹克配对，共 12 份 `WorkJacketR2` 骨骼资产，均已保存三档 LOD。`world_mesh_by_shirt`、刚性包体位置、斜挎包挂点、带长与躯干代理按同一配方发布。保留源骨骼、蒙皮、UV、材质与动态遮罩。首次逐点投影的中间版本未发布；最终采用保留径向厚度的平滑变形场，没有新增退化面片。

两次字段事务分别发布家具 19 个字段、背包 44 个字段，回执位于 `SourceAssets/KaitlinCompletion20261024/furniture_publication.json` 和 `packs_publication.json`。完整交付记录为 `SourceAssets/KaitlinCompletion20261024/delivery.json`。本轮 `build-completion-20261024-FPSGAMEEditor.txt`、`build-completion-20261024-FPSGAME.txt` 均记录 `Result: Succeeded`。

沿此前用户要求的排查范围，用隔离动画图定位了 Jason→Kaitlin→Jason 的椅子、沙发、床铺 Idle，女性姿态能够播放，启停原生后处理结果一致；该定位不覆盖实际 E 键焦点、StartRest 条件或网络传输。没有启动交互编辑器、游戏、PIE 或实际主客机测试。实际按 E 坐卧、换性别后立即操作物品、迟到回传、晚加入、重连、死亡重生及换图仍需实机确认；脸部与 Fab 的还原度、头发距离切换和穿模也不以此次构建或落盘认定通过。

以下内容保留为此前批次的历史记录。

2026-10-23 晚间按用户要求完成后台检查，补齐六个已更新的女性沙发起身动作。当前为 239 个动作映射、216 个独立片段；配置组合与 454 个目标资产的读回结果见 [检查记录](kaitlin-player-audit-20261023.md)。未运行游戏、视觉穿模或联机验收。以下 18:18 的数量及“未测试”说明保留为首次交付记录。

2026-10-23 18:18 已完成本地接入。用户选择的 Kaitlin 已完成 Epic 授权、自动绑定、High 级装配、完整身体与装备制作；两个运行配置已写入 `body_variants.kaitlin`，`ready=true`。下次启动游戏可在 F6「基本调参」→「角色外观」切换男性／女性。未启动游戏或进行测试，视觉、动作接触与实际联机由用户体验。

## 最终保存与接入

| 内容 | 已保存／接入范围 |
| --- | --- |
| 原生身体与头脸 | 301 个原生资源包；完整身体 30,455 顶点、60,816 三角面、342 骨骼；换装身体保留 17 个覆盖分区 |
| 衣物 | 142 份女性派生网格，覆盖当前 24 款服装、世界／本人视角、裤腰配对、鞋靴配对和法袍内层 |
| 背包 | 当前五款、各六个裸身／上衣组合，共 30 份；含制作期间新增的探路者背包 |
| 头部装备 | 五款的女性安装参数；含新增 ST6 贝雷帽，保留原帽尖、帽檐及羽毛动态 |
| 全身动画 | 当前 238 个映射、215 个实际使用的独立女性片段；已补入最新沙发休息动作 |
| 第一人称手部 | 47 份 V9 皮肤派生；保留已认可的原生手型、权重、JC 矫正和机械时序，使用独立女性肤色实例 |
| 法袍 | 世界／本人两份布料资产；66 个从女性身体截面制作的碰撞形状，分组到实际骨骼；两份内层皮肤材质保留裙摆可见性逻辑 |
| 头发与面部细节 | 原生长直发、眉毛、睫毛的 Groom 绑定及角色材质；长发使用身体碰撞组件，隐藏时暂停相应模拟 |
| 身体标定 | 女性饮食嘴部目标、死亡镜头、姿态比例和本人身体前向偏移 |

`SourceAssets/KaitlinPlayer20261023/published.json` 为本地接入回执，记录 142／30／238／215／5／47 的上述数量。玩家配置使用字段事务，回执为 `Saved/PlayerBodyConfigWrites/20261023T101821.504433Z-d5b80a43/receipt.json`；服装配置只插入自己的女性变体字段，保留男性根配置及并行修改。

必要的 `FPSGAMEEditor` 与 `FPSGAME` Development 构建均成功；最终构建回执为 `build-female-streaming-20261023-FPSGAMEEditor.txt` 和 `build-female-streaming-20261023-FPSGAME.txt`，两者均为 `Result: Succeeded`。切换预加载仅收集当前衣裤／鞋靴配对、内层和正在使用的武器骨架。角色选择沿用原档案外观字段；没有改装备容量、属性或动作业务时钟。

所有资产保存阶段已完成，未运行自测、静态检查、游戏、截图或联机验收；编译与落盘不等同于实机无穿模或接触验收。以下记录保留制作过程中的中间状态。

## 已取得的资源

- Fab：[MetaHuman - Kaitlin female character editable](https://www.fab.com/listings/ebbc58e2-f745-482c-bb9a-9d73b6379d93)。
- 用户下载文件：`D:/FPS3D/VaultCache/FabLibrary/MetaHuman_-_Kaitlin_female_character_editable-ebbc58e2/metahuman/UE_5.8/mhc_kaitlin.mhpkg`，111,786,051 字节。
- 包内是单个 `MHC_Kaitlin.uasset` 加 Manifest/FileList；类型为 `Character`，不是已装配角色。原始包标识路径为 `/Game/EditableCharacters/Kaitlin/MHC_Kaitlin`。
- 已按原包路径保存到 `SourceAssets/KaitlinPlayer20261023/AuthorHost` 的独立制作工程，未替换 Jason 或开启不可用的女性选项。来源、散列与原 Manifest 已保存于同目录上级。
- 原包加载类型为 `MetaHumanCharacter`，`has_high_resolution_textures=true`；初始未绑定状态现已通过云端自动绑定完成。

## 当前装配依赖

首次制作时，本机 `E:/Program Files (x86)/UE_5.8` 缺少 MetaHuman Creator 的 Optional 内容目录。现用户已补装，以下依赖均已可读取，本轮装配已越过此前的核心数据阻塞：

- `WI_Hair_L_Straight`
- `WI_Eyebrows_L_Shaded`
- `WI_Eyelashes_L_ThickCurl`
- `WI_DefaultGarment`

这些条目不是 Kaitlin 下载包里缺失的独立文件，而是指向引擎 `/MetaHumanCharacter/Optional` 内容的引用。没有依赖时，UE 在加载中会剔除缺失的外观选择，因此不能直接保存这一状态冒充完整导入。

早晨日志 `assemble-20261023-093401-555.log` 记录 EOS 已于本地 09:35:52 成功打开系统浏览器授权入口，但服务持续返回 `authorization_pending`。09:45:52 授权等待结束，自动绑定报告 `Login Failed`，命令退出 -1。下午用户已完成新授权，后续绑定和装配成功；该早晨日志仅保留为失败历史。

首次制作脚本还遇到本机 Python 枚举拼写与示例文档不一致的问题，已经把 `JOINTS_AND_BLENDSHAPES` 改为按本机 `JointsAndBlendShapes` 导出的 `JOINTS_AND_BLEND_SHAPES`；本轮已实际调用并进入云请求。首次后台退出码 -1，日志为 `SourceAssets/KaitlinPlayer20261023/assemble-20261023-001450-374.log`，没有生成角色网格。

## 2026-10-23 下午继续制作

- 用户要求重新打开授权网页，13:53 成功重新打开；用户完成授权后，日志记录 `Login complete: EOS_Success`。
- 绑定请求经系统代理 `127.0.0.1:7897` 出现 TLS 失败，而服务直连能够返回正常 HTTP 应答。只在独立 AuthorHost 的 `DefaultEngine.ini` 中为 `mh-uemhc-autorig-service.eeeb.live.use1a.on.epicgames.com` 设置 `HTTP.HttpNoProxy`；没有修改系统代理。
- `assemble-20261023-135619-174.log` 记录云端 DNA 返回、面部骨架生成，14:00:36 保存了绑定后的 `MHC_Kaitlin`。后续读取可直接继续装配，不需要重做已完成的绑定。
- High 级装配的 TextureGraph 烘焙未初始化，导致预烘焙毛发及眼睛贴图缺失，故没有产出完整角色。根据本机引擎 `TextureGraphEngine.cpp` 的正式开关，在 AuthorHost 启用 `TextureGraph.AllowCommandlets=1` 并选用 DX12/SM6，重跑装配。没有将失败的装配回执当作已接入。
- `prepare_fit_inputs.py` 保存当前配方快照与去重后的 607 条网格输入（包含衣物组合、原生绑定与姿态来源，并非 607 件物品）、196 个动作入口。`extract_fit_inputs.py` 已导出全部 607 项，`FitInputs/captured.json` 保存逐项源散列。首次长批次在第 418 项后因页面文件不足退出，随后改成每进程 24 项续接；`capture-20261023-145558-080-0.log` 至 `-7.log` 均退出 0，最后保存数 607/607。
- TextureGraph 后续已正常烘焙；原生面部控制图自动升级时报告重复断开 reroute 连线，Python 把该信息作为异常延迟抛出。脚本仅识别两份指定原生图的该类信息，随后重新编译并逐项保存。`assemble-20261023-141436-210.log` 实际退出 0；`assembly_receipt.json` 记录 300 个已保存资产、4 个骨骼网格和原始升级消息。
- `migrate_native.py` 已按原 `/Game/Characters/KaitlinPlayer20261023/Native` 路径迁入主项目，`native_install_receipt.json` 保存每包散列。没有覆盖已存在且内容不同的包。`extract_native.py` 已执行退出 0，`NativeGeometry`、`native_components.json`、`native_dependencies.json` 已保存实际形体、骨架、材质、Groom 绑定和依赖信息。
- 原生已穿衣装配会裁掉被默认衣物覆盖的身体表面：导出的 BodyMesh 为 23,780 顶点、342 骨骼，胸腹被裁切。因此该网格仅作为原生成品，不作为换装母版。`export_full_body.py` 改为从已绑定角色的完整编辑网格复制独立的 `Native/Kaitlin/BodyFull/MHC_Kaitlin_Body`。
- 完整身体首次调用官方 `ExportGeometry`，在其无条件 Slate 提示处断言退出；随后改用 `AssetTools.duplicate_asset`。Python 不暴露 `set_skeleton`，最终通过已反射的 `call_method('SetSkeleton', ...)` 赋值，16:28 保存成功。`full_body_receipt.json` 及 `extract_native-20261023-162917-857.log` 记录完整身体和退出 0 的几何导出：30,455 顶点、60,816 三角面、342 骨骼。安装回执更新为 301 包。
- 主工程中已打开的编辑器没有被关闭；AuthorHost 仅写自己的独立内容树。

## 2026-10-23 傍晚制作进度

- 刷新制作输入到当前 GarmentWaist 配对版本：656 条去重网格路径、232 个动作入口。增量源提取已完成，旧回执保留历史输入，`FitInputs/capture_status.json` 的当前范围为准。
- 通过双方原生 UV 建立 30,455 个顶点的一对一对应；两版本约半数三角形对角线不同，覆盖分区从对应顶点的邻接面迁移。女性原始身体形体保持不变，`Body/saved_asset.json` 记录 17 个覆盖分区和现有 LOD 策略的保存身体。
- `WorldGarments/manifest.json` 有 142 份女性衣物几何稿，包括世界／本人视角、裤腰配对、普通／靴型和法袍内层。保存曾在一批 LOD 生成时退出，已有 38 份落盘；后续每进程最多 4 份继续。以 `saved_assets.json` 与 `save_world_garments_status.json` 为准。
- `retargeted_assets.json` 保存 209 个独立片段，`retargeted_clips.json` 保留 232 个映射。首次退出出现异步压缩缓存断言，改为显式完成资产编译后续接；后续 26 个批次退出 0，`retarget_status.json` 已完成。
- `Backpacks/saved_assets.json` 保存全部 24 份：四款各裸身与五件上衣。包体使用刚性变换，固定带段按女性表面拟合，缝接端共享包体变换；单肩包的挂点、长度、接触探针和六段躯干凸代理同步生成。`mounts.json` 尚待最终发布。
- `Headwear/mounts.json` 生成四款头部装备的 Kaitlin 安装参数，按各自接触高度读取头部宽深，保留帽尖、帽檐和羽毛原生骨架。
- 第一人称保留已认可 V9 的握持手型、原生参考姿态、JC 形状、扭转轨道和机械时序；以原生女性前臂反照率标定独立肤色实例，再复制原生皮肤跟随网格，保留形状数据。旧 Manny 全身 Body profile 只作武器姿态参考，不作为女性第一人称皮肤输入。
- `death_head_tracks.json` 从已保存的女性死亡片段数据模型读取；`calibration.json` 已生成饮食嘴部坐标、身体姿态比例、自视身体前向偏移和死亡镜头。该步骤是镜头制作，不是动作验收。
- 法袍碰撞制作入口新增 `BuildMageRobeDrapeForBody`，女性碰撞配方从自己的身体截面生成；旧 Jason 制作入口保留。新增源码正在等待必要构建，尚不能将法袍布料保存标成完成。

## F6 开发内容

- 位于现有 F6「基本调参」页底部「角色外观」，仅一个按钮，文字随当前身体显示「切换女性角色」或「切换男性角色」。沿用 ColdSteelUI 的按钮和字体，不新增窗口或输入模式；文字保持横向。
- 当前身体与加载状态显示在按钮下方；加载中、没有受控角色、死亡或目标资源未接入时禁用。沿用面板可见时的状态更新，不增加 Tick。
- 选择经已有 `SetPlayerAppearance` 外观事务保存到当前档案的头型／发型字段，身体按兼容头型映射；不改变装备、属性、物品容量或业务动作时钟。
- `player_body.json.body_variants.kaitlin` 已保存完整女性身体配方并设为 `ready=true`。`modular_outfits.json.body_variants.kaitlin` 提供对应衣物、皮肤和各原生手部绑定；男性根配置继续保留。
- 切换前异步加载目标头发、身体、动作及当前已装备物品；随后重建身体驱动、自视身体与装备。清理旧材质覆盖、动作片段和死亡镜头轨迹，避免多次切换累计旧数据。
- 早晨的按钮源码构建记录为 `build-20261023-094451-FPSGAMEEditor.txt` 和同前缀 `FPSGAME.txt`，当时资产未齐，女性选项未启用。最终构建与完整接入已完成，见本页顶部回执；未运行游戏或测试。

## 继续制作入口

1. 原始源已就绪，`Tools/KaitlinPlayer/prepare_source.py` 不覆盖已编辑的制作副本。
2. 补齐核心数据后执行 `Tools/KaitlinPlayer/run_authoring.ps1`。它使用既有资产批次互斥，自动等待当前引擎／构建工作结束，然后运行无界面制作命令。`assemble.py` 先确认原生头发依赖可用，再调用 MetaHuman 的绑定与 High 级 Optimized 装配。
3. Epic 授权、绑定和装配均已完成，正常继续无需再次登录或重跑装配。保存的原生资产位于 `Content/Characters/KaitlinPlayer20261023/Native`。
4. 本轮所有制作和保存阶段已经完成，无需重跑。`run_production.ps1 -Stage <脚本名>` 保留分批续接入口；已有资产由保存回执定位，后续重做形体或同路径源修改应使用新修订，不能跳过已保存版本的归属判断。
5. `publish.py --publish` 已执行，运行配方保存在 `RuntimeRecipes`。只写两个配置的 `body_variants.kaitlin`，不覆盖男性根配置。后续新增装备须同时提供女性配方，不能将男性回退资源称为女性适配完成。

原始及派生资源仅本地使用，未提交或公开分发。没有启动交互 UE 编辑器或游戏，没有运行测试或验收渲染。后台 GPU 初始化用于必要的 MetaHuman 资产制作。
