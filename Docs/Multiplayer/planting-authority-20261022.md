# 种植多人接入（2026-10-22）

本轮范围：在已完成的 V3 单人种植玩法上接入现有多人架构。保留原工作台尺寸、冷钢样式、四作物规则与单人档案路径。不新增联网服务、独立 RPC 系统或另一套世界存档。

交付状态：实现已落盘；最终 Editor/Game 后台构建均成功，静态检查 28 项、0 失败；本轮运行测试为 0。运行授权仍待用户答复，未启动测试会话。没有尚在运行或排队的本任务编译命令，未提交/推送 Git。

本轮仅授权实现、后台 Editor/Game 编译与静态检查。**没有运行本轮自动化、服务器、客户端、PIE、游戏或 UE 图形编辑器。** 前一轮 40 项单人隔离测试属于旧实现回执，不能作为本轮多人验证结果。

## 现有约定与归属

依据 `ColdSteelAuthorityContext`、`ColdSteelPlayerState`、`ColdSteelSharedInventorySubsystem`、`ColdSteelInventoryRequests`、`ColdSteelWorldNetwork`、`VoxelBuildNetwork` 和篝火事务代码。

现有建筑编辑以有效房间玩家、实际 Pawn、真实建筑 Actor 和距离为界，没有按建造者锁定的地块 ACL；篝火也是公共使用。因此采用相同规则：房间内有效、存活且可达的玩家可以播种和收获公共种植地，产出进入实际操作者的背包，不增加“仅播种者可收获”的新规则。

拒绝没有正确 Pawn/PlayerState/影子档案身份的调用，以及其他 World、伪造/被替换的地块身份、已移除或下落的构件、超距和无视线操作。服务端逐次核对，不以客户端打开过面板作为授权。

## 权威与事务

1. 复用 `RequestInventoryAction` / `ServerInventoryAction`，在原枚举末尾新增 Planting，保持旧枚举编号。
2. 请求仅表达播种或收获、目标 Actor/建筑锚点、种植格、作物 ID、地块 InstanceId 与期望植株 GUID。现有通道附加 Sequence、当前库存版本和 Pawn。
3. 客户端库存基线未被服务端确认时拒绝发起种植，不因本次种植请求上传一份替换库存。实际扣料与容量检查始终针对现有服务端玩家模型/客机影子档案；沿用项目已有的入房角色档案导入合同，不另建整套库存反作弊机制。
4. 服务端核对连接身份、存活状态、库存版本、真实地块、350cm 距离和视线；0.15 秒请求节流。成熟时间、占格、扣料、产出、随机变种和变换全部从服务端规则及植株记录取得，忽略请求中的通用 Count/Eye/Origin 等字段。
5. 多人植株保存在 `FColdSteelSharedInventoryData::PlantingCrops`，并有独立 PlantingRevision。请求在游戏线程顺序处理，当前世界占格决定胜者；旧植株 GUID 或已占格的播种拒绝，不会因重发变成再次收获/重新播种。
6. 提议中的库存与共享世界完整快照通过原 `SharedInventory::Commit` 提交，复用库存回执版本、玩家保存槽、事务日志和恢复顺序。背包放不下则不提交提议，不清除成熟植株。
7. 付款前先确认真实地块身份已落盘。跨档案保存未确认时沿用原冻结/恢复规则，不凭失败返回值猜测磁盘没写入，也不以旧快照继续自动覆盖。

地块移除/替换后的植株清除和首次种子化属于世界单独写入，复用已有完整世界 redo 日志信封和恢复入口（历史类名 `UColdSteelSharedFoodJournal` / `_FoodTransaction`，其 After 一直是完整共享世界数据）。不修改 VBX 字节格式。

## 单人、多人档案边界

单人继续使用原角色档案中的 PlantingCrops 与原 CommitState，保留上一轮闭环。多人共享数据仅在服务端共享世界槽落盘，客户端接收的公共植株只进入种植子系统的世界镜像，不复制到本地 FColdSteelProfile。

按既有共享采集的约定，单人世界和多人世界是两个持久化范围。监听主机首次初始化某建筑 WorldKey 的多人种植时，仅把自己单人档中该世界、地块身份仍有效且不冲突的植株种子化一次；保留原变种与变换。客机上传的单人植株从不种子化公共世界。之后多人世界独立保存，不把其他人的公共植株回写任何人的单人档。本轮以项目已有监听服为交付范围；代码为非本地主机的权威路径保留保护，不宣称已实现或验证整套专用服务器生命周期。

## 同步与 UI

- 普通公共状态沿已有压缩、分片、带宽限制的世界快照通道同步，晚加入和重连拿到完整当前植株；不添加每株 Actor 或逐株 Tick。
- 操作者的库存回执同时带当前公开种植世界状态，使成功和业务失败都能更新占格。比较种植版本，较老的批量世界快照不能覆盖较新的操作回执。
- 增加 PlayerState 的 owner-only 服务端 UTC 小样本，每两秒更新，客户端以本地单调时间外推，不读取本地系统日期作为成熟依据；该小样本不会令整个世界快照每两秒强制重发。最终收获仍按服务端真实 UTC 重新判断。
- 变种、朝向、尺寸、根位置和播种时长/产出快照作为原植株记录完整同步。客户端只是选阶段网格和显示，不能选择服务端变种、尺寸或奖励。
- 植株先到、建筑 Actor 后到时保留世界镜像并重试表现，不由客户端删除“孤株”。原最多 36 个异步网格缓存与 ISM 分组继续使用；专用服务器不创建作物表现组件。
- 原工作台外壳、尺寸、选中/悬停/禁用、焦点与开合不变；多人入口已解锁。等待服务端结果时禁止提交，状态栏显示服务端原因；换 Pawn、换 World 和断线时清理待请求上下文。

## 文件

新增：`Source/FPSGAME/Building/ColdSteelPlantingNetwork.cpp`、`Source/FPSGAME/Multiplayer/ColdSteelPlantingAuthority.cpp`。

窄接点：原 PlantingTypes/System、VoxelBuildWorld Tick、共享库存数据、原库存请求/回执、世界快照、PlayerState UTC 复制和断线清理，以及原种植面板/HUD/交互提示。没有改其他工作台配方、角色动作、作物资产二进制或平衡配置。

工具：`Tools/Crops/run_planting_multiplayer_build.ps1`、`check_planting_multiplayer_static.py`、`launch_planting_multiplayer_manual.ps1`。备份、清单、构建日志与状态放在 `SourceAssets/PlantingMultiplayer20261022/`。

完整工程构建中另有两处机械性修正：`Dungeons/DungeonGlassRenderPreparation.h` 的组件模板指针不额外加 const，以匹配 NewObject 的可写模板参数；`Movement/FPSFurnitureRestComponent.cpp` 的复制参数命名为宏所需的 OutLifetimeProps。未改这些系统的玩法逻辑，修正前文件已单独备份。

## 本轮验证口径

静态脚本只读取源码/配置/36 个模型磁盘路径并写回执，不执行 C++ 玩法或 UE。构建和静态结果以本轮 `delivery-status.json`、`static-validation.json`、`build-editor-status.json`、`build-game-status.json` 为准。历史单人通过记录仍在 PlantingGameplay20261022，未覆盖为本轮结果。

已执行静态检查 28 项、0 失败。最终 Editor 构建日志 `build-editor-20261023-001337.log`，2026-10-22 16:13:53 UTC 成功；最终 Game 构建日志 `build-game-20261023-001543.log`，16:15:50 UTC 成功；均 exit 0、`Result: Succeeded`。日志文件名采用本机时间，回执 UTC 为上述时间。

过程中曾等待既有进程 18464 释放本项目 DLL，未关闭或重启它；两处机械性错误已修正。另一轮编译遇到并行角色动画头文件与生成宏行号不一致，后续重新生成已对齐；又一轮遇到并行 Kukri 旧接口引用，其文件随后由并行工作更新，本任务未修改 Kukri。全部尝试及失败日志保留在 `build-history.json` 和对应日志中；最后两份成功回执没有用旧版结果替代。无当前编译阻碍。

未验证：真实 RPC/复制顺序、多人竞争、断线重连、服务器重启/事务恢复、实际 UI/输入焦点、网络丢包/延迟、Cook/打包。本轮实现和静态合同不等于这些运行结果。

## 待另行批准的具体测试

已准备人工真实联机启动脚本，**没有执行**。一次授权需明确允许启动 **2 个可见游戏运行进程：监听主机＋一个客机**，均以 `-game` 运行，不打开 UE 编辑器界面。允许回连及只关闭本次脚本记录的测试进程，不触碰其他会话进程。该脚本是会话启动器，**不包含自动断言，不应称为已准备好的多人自动化测试**。此前讨论过的专服三进程方案已收窄，避免把未验证的专用服扩大为本轮承诺。

建议的实际命令：

```powershell
& 'D:\FPS3D\FPSGAME\Tools\Crops\launch_planting_multiplayer_manual.ps1' -LaunchAfterExplicitAuthorization -Port 17977
```

脚本实际调用：

```text
UnrealEditor.exe FPSGAME.uproject /Game/GameMaps/DayNight_Lighting?listen -game -windowed -ResX=1280 -ResY=720 -port=17977 -ColdSteelProfile=PlantingMP_Host -UserDir=<run>/Host
UnrealEditor.exe FPSGAME.uproject 127.0.0.1:17977 -game -windowed -ResX=1280 -ResY=720 -ColdSteelProfile=PlantingMP_ClientA -UserDir=<run>/ClientA
```

`<run>` 是每次新建的 `SourceAssets/PlantingMultiplayer20261022/ManualRun-时间-GUID`。两套 UserDir/角色槽、主机上的客机影子档、共享世界/建筑存档、日志全部位于该临时范围。脚本不复制或读取正式存档。重新启动/重连时可在两个旧测试进程均结束后传 `-ReuseRunRoot '<run>'`，保留同一临时世界与身份。主机加载完成后客机可能需要通过游戏控制台 `open 127.0.0.1:17977` 回连。

启动器要求本轮最终 Editor 和 Game 构建均成功；有构建阻碍时不会以较早 DLL 启动测试。脚本本轮只解析语法，没有运行。

人工用例：

1. 临时角色通过现有正常开发/物品入口准备种植材料和种植地，不借用正式背包；两客户端看到同一地块和四种选择。
2. 两人争抢同格/相交 2×2 占格；仅成功者扣一次材料，两端最终一致。
3. 重复点击播种、重复收获、另一人先收获后旧操作到达；不多扣料、不多发奖励、不把旧收获变成播种。
4. 材料不足、背包满、移动超过 350cm、隔墙操作、地块拆除/替换、角色死亡/换 Pawn；显示权威拒绝原因且无部分变更。
5. 生长中客户端重连/晚加入，三阶段保持同一变种、尺寸、朝向和根位；改客户端系统日期不能提前收获。
6. 只重启本次测试服务器后从原临时目录恢复，确认占格和库存不重复；另行准备故障注入才能验证磁盘写入未确认/恢复分支，普通手工重启不能代替故障注入测试。
7. 核对客户端本地档只包含自己单人植株，公共/他人植株仅在服务器共享世界槽中；原其他工作台正常。

低层重复 RPC、未授权身份伪造、精确保存故障注入、带丢包的自动断言仍需后续实现专用隔离测试夹具，不能由人工启动器伪称覆盖。若用户只允许后台无游戏进程的测试，应先批准另制并运行此类 commandlet 夹具，不启动上述 2 个进程。
