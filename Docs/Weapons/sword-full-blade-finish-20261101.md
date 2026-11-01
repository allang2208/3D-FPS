# 符文长剑整段剑身材质覆盖

- 原因：模块在本地 Z=12.5 cm 拆分，剑根基座实际归属 guard。旧材质切换只修改 blade_1，遗漏了这段原生承接面。
- 运行装配在剑身与护手的金色／银色符文材质选择完成后统一设置材质模式。护手使用 BladeFinishGuardRoot=1，仅覆盖原生剑根承接区域；剑身使用 0，覆盖完整剑身。原厂模式仍为 0。
- 区域从既有 UV0 表面映射烘焙，采用两款 Meshy 护手制作时保留的原生承接面边界：Z>=4 cm，|X|<=5.2 cm。原厂与三款普通护手在这一范围内保留相同 UV；普通护手形变仅发生在 |X|>7.2 cm。两款 Meshy 护手的原生材质槽同样使用这一遮罩，宝石、外部装饰及埋入装配内部的 Join 封口保持独立。
- 打包遮罩：R=剑身原生符文，G=剑根原生符文，B=剑根覆盖区域。替换四路 PBR 节点的 Mask 输入，保留五种材质公式、原生发光、Substrate 和湿润链路。
- 外观缓存签名增加 root20261101，使已有装配按新覆盖规则刷新。
- 共用栏位显示名称改为“剑身”，原装选项改为“原装剑身”；内部 blade_1 ID、存档和数值不变。

制作入口：SourceAssets/SwordBladeFullSurface20261101/bake_mask.py 和 install_materials.py。后者在既有 SwordBladeMaterials、Damascus、MeteoricIron 制作流程之后执行；只接续材质，不重装数值目录。

初次保存和构建结果分别记录在同目录 material-receipt.json、build-receipt.json。初次交付未运行游戏测试、截图或视觉验收。

## 用户要求复查后的联机修复

原先第三人称 CaptureWeapon 会移除 MID，只留下持久材质父级。FPSBodyRuneVisual 仅恢复符文，因此 BladeFinishMode 与 BladeFinishGuardRoot 丢失，材质单独切换也没有进入世界装备缓存 Key。这会影响本人第三人称、主机看到客机以及客机看到其他玩家。

修复在 FFPSBodyAttachment 增加两项复制字段，Capture 从对应玩家的权威物品解析材质模式，未装符文时也记录。观察者在恢复符文之后调用与本地装配相同的 ApplyBladeFinish；Key 纳入模式和剑根标记。继续使用 ReplicatedWeapons 的持久复制状态，支持新相关和晚加入快照重建，不发送一次性的材质切换事件。

资料追踪范围：改造 Apply/CommitState → 客机档案提交/服务端影子档案 → ApplyColdSteelProfile/RefreshEquipment → CaptureWeapon → ReplicatedWeapons/OnRep_Equipment/RebuildWeapons。地面物品沿 SharedItem → OnRep_SharedItem → BuildConsumable → 共用装配，内部 blade_1 与 gunsmith_parts 不改名。AzureRunesword 目录已有 Cook 登记，新遮罩被两套主材质直接引用。

用户授权的定向后台检查入口：SwordBladeFinishAudit commandlet。组合范围为 4 款剑身、6 款护手、8 种符文状态、6 款材质及每组恢复原厂，共 1344 个组合/切换场景。检查实际装配、装备描述捕获、反射序列化回读、观察者 MID 重建、仅材质变化的 Key 更新、原生符文遮罩及宝石独立材质。另用 audit_saved_materials.py 回读保存后的材质图连接。结果见 network-audit.json、saved-material-audit.json。

上述组合与材质回读检查未建立真实网络连接；后续真实网络补充结果如下，画面验收仍单独区分。

已执行组合检查：1344 个场景，24480 项断言，0 失败。包括未装符文时的材质复制、普通符文叠层、金银原生符文遮罩、两款传说护手独立装饰材质及恢复原厂。Editor 构建已成功。

已保存材质回读：31 项，0 失败；两套主材质的四路 PBR 遮罩、线性覆盖贴图、Substrate 输出与发光连接均保留。源码复查未发现栏位改名影响内部存档键或材质适用范围。构建期间还仅调整了 ColdSteelPlayerState.cpp、KukriPairedHeavyHit.cpp 的首个包含头文件顺序，以满足现有构建规则，未修改其战斗逻辑。

## 真实联机补充完成

2026-11-01 用户要求继续修复后，完成本机 UDP 监听主机、客机与新进程重连检查，7 个场景全部通过，3 个进程均以 0 正常退出。正式装备 Capture、ReplicatedWeapons、OnRep_Equipment、RebuildWeapons 和材质 MID 恢复均参与运行，未用本地反射回读代替网络传输。

- 客机晚加入主机已装备的玄铁／大马士革配置。
- 只替换剑身材质，双方观察者更新剑身与基座。
- 金色／银色符文与双曜星环／星陨天枢护手组合切换。
- 切回原厂材质，双方参数恢复为 0。
- 卸下与重新装备，世界武器消失并按已安装改造恢复。
- 首位客机正常退出，再启动新客机连接；服务端保留的同一物品实例和改造配置恢复正确。

主机、首位客机和重连客机均从实际 NetDriver 读到 60 ms 延迟、3% 丢包模拟配置。这是注入配置，不代表实测 RTT。最多同时运行两个无渲染进程，独立 UserDir 和测试档案不使用用户正式存档。

证据：`SourceAssets/SwordBladeFullSurface20261101/wire-receipt.json`，详细断言与双方日志在 `Wire/20261101-114052/`，构建成功日志在 `Wire/20261101-113919/build-editor.log`，该次成功构建的 DLL 散列记录在运行目录 `inputs.json`。失败的准备尝试已带散列移入 `trash/SwordBladeFinish20261101`，未计为通过；成功运行的临时 UserDir 同样归档，目录根部的断言、日志和输入散列保留。

范围边界：本次实测为监听主机、实际 UDP 装备外观同步与服务端保留装备的断线重连。库存由隔离夹具设置；没有覆盖玩家改造台操作的上传事务、攻击 RPC、专用服务器、跨机器公网或最终渲染画面。既有目录/数值没有再次更改，未因测试通过重跑组合检查。

## 整理发布

本次发布范围、许可与历史证据边界见 [发布说明](../Publication/SwordBladeFinish20261101/README.md)。没有因归档或 SKILL 更新重新运行测试。
