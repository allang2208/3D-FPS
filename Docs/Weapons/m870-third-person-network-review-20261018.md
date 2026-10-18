# M870 第三人称联机复查

范围：上一轮 M870 抵肩／瞄准轴、泵动支撑手、激光归零及其本机—服务器—观察者链路。双手锤不在本轮修改范围。使用枪械与复制技能，按用户本次要求增加定向检查。

## 发现并修正

1. **泵动同步提前降频。** 原采样只在射击后 0.15 秒内将无动作、无激光的枪视为活动表现；M870 拉泵从源时间 0.16 秒开始，恰好降为每 0.08 秒一次。增加已有表现通道中的 `Pump` 标识，保持完整泵动每 0.04 秒采样；主机同样请求这个更新频率。通道启停复用已有可靠边沿，连续数据仍走原有非可靠快照，不新增 RPC。标识不改变玩法 Idle、ADS、下一枪闭锁或弹量。
2. **装备与身体态乱序可能错用握点。** 原 `ApplyMotion` 在核对机械骨 schema 前就使用 `SupportGrip`，同型号不同实例的机械骨也只核对 schema。现在支撑握点、机械骨和世界可见性共用装备实例／schema／骨与附件数量匹配；不匹配的支撑手退回新装备待机握点，装备重建清除旧握点插值。避免旧 M870 的拉泵位置短暂驱动新枪。
3. **服务端原地瞄准读到旧相机缓存（后续双端检查发现）。** `APawn::GetBaseAimRotation` 调用 PlayerController 的相机缓存，而引擎 `PlayerTick` 中客户端相机更新受移动输入／速度门控；静止转向时该缓存可能落后于 CMC 更新的控制旋转。`SampleRemoteAuthorityState` 现改用服务端 Controller 的控制旋转，没有 Controller 时才回退；本机仍读取原相机瞄准，激光仍使用拥有者落点。对应引擎源码为 `Engine/Private/Pawn.cpp:1005`、`PlayerController.cpp:1001` 与 `PlayerController.cpp:5668`。

## 路径记录

| 路径 | 源码追踪结论／检查内容 |
| --- | --- |
| 本机及主机瞄准 | 当前 M870 抵肩与完整枪轴标定已进入共用 RifleHold；俯仰和偏航传给全身动画 |
| 客机→服务器瞄准 | 后续发现并修复相机缓存取向问题；服务器直接取自身 Controller／CMC 的瞄准旋转及意图，不相信表现包内的瞄准值 |
| 泵动支撑手和护木 | 同一源帧产生支撑握点与机械骨，现有 NetSerialize 包含两者；远端按同一插值系数应用 |
| 主机／客机泵动采样 | 修复 0.15 秒后提前降频，使用 Pump 通道及既有序列号、可靠边沿 |
| 切枪／换配件先后到达 | 新增实例及布局匹配，清除旧握点插值；定向用例包含同型号不同实例和错误 schema |
| 丢失结束包／断开 | 已有 0.6 秒表现租期清除旧接触；激光观察者亦拒绝过期样本 |
| 激光 | 拥有者描线落点经实例、配件槽、schema 校验转发，观察者复用落点；本地光束可按自身遮挡截断 |
| 射击事件 | 远端事件驱动音效、枪口、退壳，不再次播放机械泵动动画；没有发现双重泵动叠加 |

## 回归入口与边界

入口：`UnrealEditor-Cmd FPSGAME.uproject -run=ShotgunAttachmentAudit -M870Presentation -unattended -nullrhi -nosound`。执行代码：`Source/FPSGAME/Weapons/M870ThirdPersonAudit.cpp`。只在明确传入该参数时运行，使用隔离审计档案，无持久档案写入。

用例调用真实资源、生产 NetSerialize、服务器表现接收与远端应用入口。检查抵肩、五种改装枪托、实际泵动握点、ADS 门控、泵动采样、乱序与旧实例、租期、激光布局及落点。本入口不建立网络 socket，不包含丢包模拟、重连或真人双端观感验证，不能将其结果称为真实联机验收。

## 执行结果

正式 Editor 构建 `Saved/BuildEditor/build-20261018-010919.log` 返回 `Result: Succeeded`。本轮 29 项定向检查全部通过，commandlet 正常退出，exit code 0。

记录在 `SourceAssets/M870ThirdPersonAim20261018/NetworkReview/`：`result.json` 为逐项结果，`audit-receipt.json` 为退出回执，`completed-build.json` 记录源码散列与 DLL，`completed-build.log` 为构建日志副本。没有打开 GUI、运行地图或修改已保存资产／玩家档案。

首轮 25 项有 1 项枪托汇总用例失败：检查用例将加载器支持的包路径直接当作运行时装备对象路径，导致不能提取网格对象名。改为加载实际枪托对象，并将五种枪托拆成独立用例后，29 项全部通过。首轮证据归档于 `trash/m870-third-person-retired-20261018/NetworkReview/attempt-1/`；该项不是运行时枪托故障。

以上为第一轮隔离回归结果；当时尚未覆盖实际 socket 连接的双端传输、延迟／丢包模拟及新客机重新连接。后续补做结果如下，最终画面观感仍未验收。

## 后续真实双端检查

用户关闭 UE 后要求继续。新增显式参数 `-M870PresentationWire`，复用现有 ShotgunWireAudit 的监听服务器、客机和隔离审计档案。两端通过真实本地 UDP 连接，并使用 NetDriver 的 `SetPacketSimulationSettings` 设置各端 60 ms 延迟、5% 丢包。

六种场景：腰射抬枪、ADS 压枪及祝福激光、泵动握点、同型号新实例与骨架后托、客机暂停表现发送后的过期、恢复发送。第一客机退出后，新的客机进程连接同一服务器再执行上述场景；核对两方向身体态、实际应用握点、装备身份及激光落点。后台入口为 `SourceAssets/M870ThirdPersonAim20261018/NetworkReview/run_wire.ps1`。

此用例将真实源动画停在指定帧，隔离检验表现数据传输和应用；瞄准输入由夹具在控制器上设定。它不测试鼠标输入／CMC 压缩移动包、完整连续动作观感、真实互联网或重连后的档案持久化。场景使用 NullRHI，没有窗口、截图或渲染。

首次完整传输运行 `trash/m870-third-person-retired-20261018/NetworkReview/Wire/20261018-015041` 的握点／激光检查大多通过，但所有瞄准项失败，并有一项重连首个场景握点失败，不能作为通过记录。进一步确认两类原因：夹具停用角色 Tick 后漏同步本机相机组件，及上述真实服务端相机缓存问题。已分别修正夹具与服务端取向来源，并保留握点误差诊断。`trash/m870-third-person-retired-20261018/NetworkReview/Wire/20261018-015557` 在资源加载阶段中断，没有完成结果，不计为通过。

完成运行：`SourceAssets/M870ThirdPersonAim20261018/NetworkReview/Wire/20261018-094854`。

| 结果 | 数量／状态 |
| --- | --- |
| 首次连接 | 6 个场景全部通过 |
| 客机退出、新客机进程重新接入 | 6 个场景全部通过 |
| 主机汇总 | 12 个场景全部通过，脚本 exit code 0 |
| 运行时网络模拟参数 | 两端实际 NetDriver 均记录 60 ms 延迟、5% 丢包 |
| 瞄准、实例、泵动及应用握点 | 双向通过；原重连首个场景亦通过 |
| 激光及过期清理 | 双向落点匹配、暂停发送后的旧接触／激光清理均通过 |
| 活跃场景握点最大接收误差 | 0.00723 cm（源数据与接收数据比较，不是蒙皮视觉误差） |

传输结果在各角色的 `host.json`、`client.json`、`rejoin.json`，汇总回执为 `NetworkReview/wire-receipt.json`。本轮 Editor 正式构建日志为 `Saved/BuildEditor/build-20261018-015920.log`（排队后于 02:08 完成），构建及源码散列记录于 `wire-completed-build.json`。修复后的原有 29 项隔离回归也再次全部通过，正常退出，记录在 `NetworkReview/AfterWire/`。

随后完成 `FPSGAME Win64 Development` 增量构建，12 项编译／链接动作成功，exit code 0；独立运行的 `FPSGAME.exe` 也包含最新修正。日志及回执为 `NetworkReview/build-game-native.log`、`game-build-receipt.json`。没有启动该 EXE；上述双端检查使用 `UnrealEditor-Cmd -game -nullrhi`。

边界：通过的是本地 UDP、受控延迟／丢包、固定源帧和新连接表现重建；没有完成真实互联网、鼠标／CMC 输入端到端、断线后的持久档案恢复或有画面动作观感验收。本轮没有发现需要进一步修改的已覆盖表现问题。

构建期间另有设施检查文件阻塞：仅将 `FacilitySpawnRecheckCommandlet.cpp` 的 Actor 数组遍历从 `auto*` 明确为 `AActor*`，不更改其检查行为；该文件的其他并行修改保留。
