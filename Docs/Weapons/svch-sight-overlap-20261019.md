# SVCh 重叠机械瞄具修复

## 根因

`M4FoldingSights.cpp` 过去用网格名包含 `FoldingSights` 判断是否安装独立 M4 瞄具。新模型叫 `SK_SVCH_RealFoldingSights`，自身已经包含一对 SVCh 瞄具，却也命中了该条件，于是额外挂载 `SM_M4_RearSight` 和 `SM_M4_FrontSight`。

2026-10-19 在现有 UE 会话只读采集到，两只独立 M4 瞄具均挂在使用新版 SVCh 网格的 `AKMViewmodel/WPN_root` 下。当次采集时用户已切到近战，枪和这两只附件均隐藏；组件归属仍明确证实错误创建。没有为了采集切换用户装备或结束 PIE。

现场记录：`SourceAssets/SVCHReplacement20261018/SightOverlap20261019/runtime_sights.json`。

## 修改

仅修改 `Source/FPSGAME/Weapons/M4FoldingSights.cpp`：

- 独立 M4 瞄具只匹配当前正式 M4 网格的完整资产路径，取消名称子串判断。
- QBZ191、A762、LMG201 保留已有的独立瞄具分支。
- 更新瞄具时，对不使用这些独立瞄具的枪清理已经创建的旧组件和折叠状态，覆盖当前 SVCh 实例残留。
- 新 SVCh 内置机瞄、导轨位置、材质、V9、手掌接触与所有源动作不变。

## 接入与排查范围

当前编辑器已运行，本次仅修改现有函数逻辑，使用已有 MCP 批次互斥执行 Live Coding；不启动新编辑器。补丁结果记录在 `SightOverlap20261019/livecoding-result-01.json`。

本轮 Live Coding 已返回 `Result: Success`，修改已编译应用到当前编辑器。补丁后采集时，当前实例已切到其他武器，没有观察到 SVCh，因此不将该次读回当作重叠已消除的运行证明。

补丁后的只读组件结果记录在 `SightOverlap20261019/after_patch.json`。它只判断 SVCh 是否还拥有额外 M4 瞄具，不代表完整 ADS、换弹、弹道或其他武器回归。

Live Coding 的当前进程补丁与普通基础 DLL 构建分别记录；没有常规构建回执时，不能称为基础 DLL 已更新。

用户确认保存关闭编辑器后，等待已有后台资产批次释放互斥锁，再完成 `FPSGAMEEditor Win64 Development` 常规构建。2026-10-19 10:31:47（本地时间）构建成功，正式 `UnrealEditor-FPSGAME.dll` 已链接落盘。构建记录为 `SightOverlap20261019/build_receipt.json`；汇总为 `repair_receipt.json`。

构建后没有重新打开编辑器或运行游戏。错误创建原因有现有实例组件归属及源码证据，修复后实际持枪、切枪和加装光学瞄具效果仍由用户体验。
