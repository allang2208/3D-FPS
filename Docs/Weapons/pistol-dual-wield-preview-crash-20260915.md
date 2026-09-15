# 双持副枪附件初始化崩溃修复

用户报告：玩家启动并恢复双持装备时发生 `EXCEPTION_ACCESS_VIOLATION`，读取地址 `0x158`。堆栈为 `ApplyColdSteelProfile → RefreshEquipment → CopyLeftAttachments → UColdSteelPickupStudio::Acquire → AFPSGAMECharacter::BeginPlay → UProductionToolComponent::BeginPlay`。预期是恢复两把枪及附件后进入游戏。

## 原因

副枪通过 `UColdSteelPickupStudio` 创建独立的 `FPreviewScene` 角色，以取得附件层级。UE 的 `AActor::PostActorConstruction` 在全局 `BeginPlayCallDepth > 0` 时也会调用新角色的 `BeginPlay`，即使它位于另一座尚未开始游戏的预览世界。

`AFPSGAMECharacter` 的预览判断位于 `Super::BeginPlay()` 后面；父类先调用所有已注册组件的 `BeginPlay`。生产工具组件仅检查 `NM_Standalone`，而预览世界同样返回该模式，因此随后解引用不存在的 `GameInstance`。`RuneSwordComponent` 使用的 `IsGameWorld()` 也包含 `GamePreview`，存在同一路径下的同类问题。

## 修改

- `ColdSteelPickupStudio` 在生成附件展示角色和临时拾取展示对象前设置 `bTemporaryEditorActor`。UE 在分发 `BeginPlay` 前识别该标记，阻止整条角色及组件启动链。
- 武器图标、枪匠独立展示角色使用相同的生成标记，覆盖复用角色的三个预览入口。
- 生产工具和近战组件明确要求非空 `GameInstance` 以及 `Game`／`PIE` 世界后才初始化。此边界不依赖 `WITH_EDITOR`，用于非编辑器构建中的预览角色。
- 编辑器标记保持在 `WITH_EDITOR` 条件内；玩家正常装备、附件复制和前一版手臂动作继续使用原流程。

## 交付状态

代码修复完成，`FPSGAMEEditor Win64 Development` 构建成功，新 DLL 已生成。构建日志为 `Saved/BuildEditor/dual-preview-crash-fix-20260915.log`。

按用户规则，未启动 PIE、游戏、自动测试或渲染复现；运行结果由用户重新打开工程后测试。
