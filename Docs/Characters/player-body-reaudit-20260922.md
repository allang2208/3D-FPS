# 玩家第三人称动作复审 — 2026-09-22

本次应用户“回头检查一遍，审计一下”进行只读审计。覆盖本轮第三人称动作采集、程序姿势、装备表现及其相邻的视角／阴影调用链，对照现用第一人称动作执行器的状态语义。未修改源码或资产。

后续用户已要求修复；源码处理及构建状态见 [复审修复记录](player-body-reaudit-fixes-20260922.md)。下文保留修复前的审计证据。

结论：发现 6 项 P2 问题，应修正后再评价完整表现。第一、第三人称动作可以不同，但出手侧、装备占用、取消动作及支撑释放应与玩法状态相符。以下结论来自代码路径和公式复算，未启动编辑器或 PIE，不等于视觉实测。

## 1. [P2] 第三人称阴影条件写反，并造成逐帧重复切换

- 位置：`Source/FPSGAME/Characters/FPSPlayerBodyComponent.cpp:107`；相邻调用为 `FPSPlayerBodyCamera.cpp:52-58`、`:78`。
- 触发：F6 开启第三人称，摄像机正常位于人物后方。
- 证据：`bCast = FPSPlayerBodyWorldBodyShadowEnabled() && !IsThirdPersonViewEnabled()`，第三人称时结果始终为 false，与上一行“第三人称下身体是可见主体，阴影必须保留”的意图相反；身体、世界武器、配件和服装随后均应用 false。
- 额外影响：每次第三人称 `CalcCamera` 都调用 `UpdateWorldOwnerVisibility`，先将 `CastShadow` 写为 true，再由 `ApplyWorldBodyShadow` 写回 false。现有字段差异判断无法阻止 true→false 的重复变化。引擎 `UPrimitiveComponent::SetCastShadow` 在字段变化时调用 `MarkRenderStateDirty`；这里能确定存在重复标脏，未测量实际帧耗时。
- 修正方向：一次计算最终阴影策略并供所有入口使用；第三人称保留阴影，第一人称按对应开关控制。翻越收起装备也应参与同一最终策略。

## 2. [P2] 双持施法没有收起第三人称副手枪

- 位置：`Source/FPSGAME/Characters/FPSPlayerBodyEquipment.cpp:227-240`；手部施法覆盖位于 `FPSPlayerBodyAnimInstance.cpp:261-262`。
- 触发：装备两把手枪后使用左手施法。
- 证据：世界武器的隐藏条件只包含 Vault/Mantle。所有 `WorldWeapons` 使用同一个可见性判断，没有 Cast 状态或左右手判断；左手同时被移动到施法目标。
- 对照：现用 `PistolDualWieldComponent.cpp:523-531` 明确在施法时隐藏副手的 `WPN_root` 和附属配件。世界副本在 `RebuildWeapons` 内重新加载资产、采样 Idle，不会继承源组件的 HideBone 状态。
- 影响：第三人称施法手仍带着副手枪，表现与“释放左手施法”的状态冲突。
- 修正方向：为世界装备及其配件保留所属手信息，Cast 时只收起副手，并按收手过程恢复；右手仍可独立射击。

## 3. [P2] 双持左手近战的击打转腕被加到右手

- 位置：`Source/FPSGAME/Characters/FPSPlayerBodyAnimInstance.cpp:231`、`:244-255`；`FPSPlayerBodyPoses.h:98-109`。
- 触发：双持快速近战轮换到 `PistolBashLeft`。
- 证据：进入双持分支前始终调用 `RightHand(..., Targets[0])`。该函数对所有非 RifleBash 的 GunBash 都向右手增加 `0.8 * Lift` 的转腕，没有识别 Left/Right。后续循环按 Striking 分配击打位移，但不分配击打旋转；没有换弹时，左手旋转保持原值。
- 公式复算：接触时刻 Lift=1，因此左手出击时，额外约 45.84° 的击打旋转实际施加在右手上。这是附加目标旋转，非实测屏幕角度。
- 影响：位移选择的是左手，击打转腕选择的却是右手，左右轮换只有部分表现正确。
- 修正方向：按出手侧统一生成对应手的位移和旋转，另一手使用明确的避让姿势。

## 4. [P2] 施法提前收手会重新向完整施法姿势抬手

- 位置：`Source/FPSGAME/Characters/FPSPlayerBodyPoses.h:134-139`；通用手部短过渡位于 `FPSPlayerBodyAnimInstance.cpp:269-280`。
- 触发：未完成聚能／准备时进入 Recover，例如技能取消回调或尚未完成聚能的实体提前结束。优先级抢占直接设置 None 的路径不属于此触发条件。
- 证据：Gather 使用当前进度插值；Recover 却重新构造 `Lerp(Gather, Push, ReleaseFraction)`，以 `1 - Smooth(recoveryProgress)` 为权重，没有保存取消瞬间的第三人称姿势。`HandReleaseFraction` 是掌心旋转相关参数，不能表示被取消时的聚能位移。
- 公式复算：聚能进度 10% 时目标权重仅 0.028；进入 Recover 后，按源码默认 0.50 s 恢复时长计算，0.10 s 时目标权重仍为 0.896，而通用 0.10 s 切换过渡已结束。固定 Base 的情况下，手部目标会先从接近持握位置重新向 Gather 抬起，再落下。上述数字为公式中的目标权重，实际手腕位置还受 IK 可达距离限制。
- 对照：`FPSFireballComponent.cpp:58-65` 保存被打断的阶段与进度，第一人称恢复使用该源姿势；第三人称没有利用等价的入口信息。
- 修正方向：在进入 Recover 时捕获实际第三人称手部变换，并在整个恢复区间从该姿势回到当前持握位置。

## 5. [P2] 翻越双手在玩法释放时刻仍完全锁住障碍物

- 位置：`Source/FPSGAME/Characters/FPSPlayerBodyAnimInstance.cpp:265`；源时序为 `Movement/FPSTraversalExecution.cpp:163-170`。
- 触发：翻越或攀爬进入 Release 后的退出区间。
- 证据：第三人称 Plant 的退出项是 `1 - Ease((progress - release) / (1 - release))`，到 release 时仍等于 1，此后才开始减小，到动作结束才为 0。玩法表现的支撑权重在 `Release - .12` 至 `Release` 已由 1 降到 0，释放后执行撤手。
- 边界复算：在释放时刻，第一人称支撑权重为 0，第三人称 Plant 为 1；在释放到结束区间的中点，第三人称 Plant 仍为 0.5。完整 IK 权重还乘以 MotionWeight。
- 影响：身体继续离开障碍物时，第三人称双手仍被拉回旧支撑点；实际拉伸、滑动程度需要画面确认。两套动画不同不要求逐帧相同，但此处把“完成释放时刻”当作“开始释放时刻”。
- 修正方向：在 Release 前完成解除支撑，再独立执行撤手和恢复持械；中断翻越时也应从当前姿势退出。

## 6. [P2] 双持装备动作仍未映射

- 位置：`Source/FPSGAME/Characters/FPSPlayerBodyActions.cpp:48-61`；`FPSPlayerBodyAnimInstance.cpp:249-255`、`:402`。
- 触发：从非双持装备切换到两把手枪。
- 证据：`PistolDualWieldComponent.cpp:184` 将角色全局 WeaponState 置为 Idle，随后各手独立启动 equip（`:136`、`:189`）。身体采集只记录各手 Reloading、Progress 和 LastShot，不记录 equip 类型；双持手部仅在 Reloading 时使用 Progress，上身装备动画又明确排除了 bDual。
- 影响：第一人称和玩法仍执行装备流程，第三人称直接进入固定双持姿势，缺少取出／举起过程。
- 修正方向：左右手分别携带动作类型及进度，补充独立的装备进入曲线，保留现有装备期间输入限制。

## 已核对的边界

- 当前 `player_body.json` 中身体和动画共 60 个资源引用，对应本地 `.uasset` 文件均存在。这仅确认文件存在，不等于引擎加载、骨架兼容或画面通过。
- 当前配置仍指向 `SKM_Manny_PlayerSkin`；已有 `body_skin_install.json` 记录身体两个材质槽使用 `MI_PlayerBodySkin`。本次未加载编辑器重新读取材质槽或渲染，不将历史回执当作当前视觉验证。
- `Saved/BuildEditor/build-20260922-175139.log` 确实记录 `Result: Succeeded`；本轮相关动作源文件在前序 `173854` 日志中有 Compile 记录。当前 Editor DLL 仍为 2026-09-22 17:51:31、11,472,384 字节。本次未重新构建。
- 蹲走仍使用步行接触相位、缩短步幅和膝盖 pole 修正，没有发现本轮将其重新切回跑步循环。是否仍滑步、脚掌穿地或动作僵硬，需要实机观察，不能由源码审计判定已解决。
- 双持大幅抬头／低头时的手部可达性、左右手握枪方向、铲子握点、滑铲腿部接触和武器穿身尚无本次视觉证据，保留为待观察项，不列作已经复现的缺陷。
- 各枪第三人称机械动作、喝药／回填、地形脚部 IK、普通受击及完整多人玩法同步仍是原记录中的未完成范围，本次未把它们计作新增回归。

建议先处理阴影最终策略和左右手动作／装备归属，再修正施法与翻越退出时序，最后补双持装备动作。本次只新增审计记录，未修复上述六项。
