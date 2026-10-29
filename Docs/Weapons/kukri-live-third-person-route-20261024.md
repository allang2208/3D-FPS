# Kukri F6 第三人称实际接线排查（2026-10-24）

用户反馈 V2 实机攻击几乎没有变化。之前 156 组夹具检查不构成 F6 实机验收；本次未宣布动作修复完成。

## 已从用户当时运行的游戏读取

- 工程：`D:/FPS3D/FPSGAME/FPSGAME.uproject`，编辑器 21:02:32 启动，晚于当时的模块构建。
- 游戏世界：`/Game/GameMaps/UEDPIE_0_L_CyberpunkApartment.L_CyberpunkApartment`。
- 本地玩家：`PersistentLevel.FPSGAMECharacter_0`。
- 主身体：`CharacterMesh0`，模型为 `/Game/Characters/ModularOutfit20260924/JasonPlayer20261003/EquipmentFit20261003/SK_Jason_Base.SK_Jason_Base`。
- 动画实例：`/Script/FPSGAME.FPSPlayerBodyAnimInstance`。
- 复制身体状态：`Weapon=ue_kukri, Family=Kukri`；读取时是 Idle，**没有捕获到实际攻击帧**。
- 实际动画实例的 `Clips` 表中，13 个 `Kukri.FullBody.*` 均指向 `Kukri20261024/FullBodyV2/Animations`。
- 身体与裤装、鞋、上衣的 Leader Pose 都指向该主身体；第一人称 `KukriViewmodel` 是另一个独立组件。
- 用户确认复现视角为 F6 第三人称／固定第三人称。

因此可以确认修改目标与实际第三人称身体一致、V2 已加载；尚不能据此确认攻击时的最终输出正确。

原始证据：`SourceAssets/KukriThirdPerson20261024/FullBodyV2/live-body.json`、`live-read-receipt2.txt`，以及当次游戏日志的 `getall FPSPlayerBodyComponent ReplicatedState` / `getall FPSPlayerBodyAnimInstance Clips` 输出。

## 找到并修正的独立问题

`FPSPlayerBodyAnimInstance.cpp` 的 Uppercut 脚步覆盖判断只依靠 HeavyStrike 和 `Uppercut` 名称，没有排除 Kukri。弯刀挑斩会进入双手剑／战锤额外的跑步覆盖分支，覆盖它自己的完整动作腿部。

已在源码增加 `!HasKukriAction`。这是挑斩的具体接线修正，不作为“普攻几乎无变化”的根因结论。

## 诊断差异与当前限制

实际 Jason 身体保留 `ABP_Body_PostProcess`，上一轮夹具强制关闭它。本次诊断默认保留后处理，并提供 `native-only` 参数作对照。21:35 完成 156 对开关对照，所记录的脚踝、骨盆、手腕位置及膝关节弯曲角最大差值为 0；夹具中未发现后处理覆盖，不把它认定为根因。摘要见 `SourceAssets/KukriThirdPerson20261024/FullBodyV2/post-process-comparison.json`。

编辑器于 21:15:13 退出，之后的只读实时骨骼采样没有运行。未主动打开编辑器或 PIE。

后台启动先遇到磁盘空间不足，D 盘当时约剩 1 GB；临时诊断日志改放 `C:/Users/allan/AppData/Local/Temp/KukriRuntimeDiagnosis20261024`。之后两次后台启动在 AssetRegistry / UnrealNames 初始化时断言退出，未执行到动作诊断。使用本机引擎支持的 `AssetGatherAll=false` 后完成对照，脚本成功生成两份报告；进程仍因其他资源包的 AssetRegistry 错误返回 1，不能把进程视为整体通过。没有修改或清理这些资源包。

21:26:03，共享 `Source/FPSGAME/Characters/FPSPlayerBodyComponent.h` 变成 0 字节。随后的 Editor 构建因该类型缺失失败（exit 6）。按并行工作规则保留空文件现场，没有用旧 Git 版本覆盖。21:35:45 该文件恢复至 22159 字节，保留本次弯刀声明；此后重试必要构建，最终状态以独立构建回执为准。

修复后仍须捕获用户 F6 场景中的实际攻击状态与最终腿部骨骼，不能把加载路径或夹具数值替代视觉验收。

头文件恢复后，Editor（149.88 秒）及 Game（144.01 秒）完整构建均成功，挑斩隔离修正已链接。两目标最终回执为 `SourceAssets/KukriThirdPerson20261024/FullBodyV2/final-builds.json`。未对挑斩修正作实机验收；用户 F6 普攻反馈尚未闭环。
