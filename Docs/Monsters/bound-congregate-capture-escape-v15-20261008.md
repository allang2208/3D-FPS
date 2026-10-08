# 缚群 V15：宽扇形起手与快速近战挣脱

> 历史阶段记录。2026-10-08 用户否定整体衣物并暂停；V18、V19 均未获认可。当前状态、最新参数和已归档证据的取回位置以[暂停与发布记录](bound-congregate-paused-publication-20261008.md)为准。

## 范围与接入

- 甩鞭起手由正前方 ±30° 改成 ±60°（总角度 120°），保持现有攻击距离、高差、视线、2 秒 CD 和动作流程。
- 缠绕只限制角色移动，保留视角、第一人称持械显示和快速近战输入，不再设置控制器的通用 IgnoreMoveInput。
- 复用 F 快速近战完整动作，在动作的唯一接触时刻击打身上的缠绕触手；每次计 1，下达第三次接触后立即通过原有 CancelTentacle / Release 进入收回。普通射击、剑刃挥砍和空手左键不累计。
- 沿用快速近战的体力、动作占用和恢复时间。挣脱计数由权威端维护、复制，单次动作由现有 bContactDone / bQuickCombatContactDone 保证仅结算一次；新一次捕获从 0 开始。不改写既有快速近战客户端施放限制。
- 不修改已接入的衣物、骨架、触手抽打动画及伤害数值。

## 底部提示布局、数据与状态

- 在现有底部动作提示栏上方增加单独文字行，底部中央锚点，距体力行向上 57 屏幕像素；现有动作提示为 25 像素。最大宽 600 像素，窄屏限制为视口宽减 24 像素并允许折行，高 42 像素。
- 文案为“被触手缠绕 · 按 F 快速近战挣脱（0/3）”，随实际接触更新 1/3、2/3；第三次释放后隐藏。仅读取本地角色的捕获组件，不扫描世界、不加载新资源、不增加 Tick。
- 复用 ColdSteelUI 字体、Warning 色和现有文字阴影，不接收鼠标或键盘焦点。背包／外部抽屉打开时隐藏；未被捕获、死亡或捕获源失效时隐藏。
- 布局和状态在现有 UpdateStaminaLayout 中更新，仅进度改变时重建文案；无存档字段或资源迁移。

## 文件与交付状态

- Monsters/BoundCongregateTentacle.cpp：起手角度。
- Monsters/BoundCongregateCaptureComponent.h/.cpp：移动限制、挣脱计数和释放。
- FPSGAMECharacter.cpp：将被捕获状态接入现有移动输入门控。
- Skills/FPSQuickCombatComponent.cpp、Weapons/RuneSwordComponent.cpp：快速近战接触分支和命中反馈。
- UI/ColdSteelHUDWidget.h、UI/ColdSteelStaminaHUD.cpp：独立挣脱提示。
- UI/ColdSteelSoulCounter.cpp：构建阻塞修复，仅将局部 `Slot` 改名 `DeltaSlot`，避免遮蔽 UWidget 成员；不改行为。
- 必要构建：FPSGAMEEditor / FPSGAME Win64 Development。
- 当前源码已保存，`FPSGAMEEditor Win64 Development` 与 `FPSGAME Win64 Development` 均构建成功。原生 Editor 模块和 `Binaries/Win64/FPSGAME.exe` 已链接落盘；本次不涉及资产重导入。
- 期间遇到的其他界面头文件错误已由现有修改恢复，本任务没有覆盖该文件；必要构建继续进行，没有发送跨任务消息。
- 构建记录位于 `Saved/BuildBoundCongregateEscapeV15/`，成功日志为 `build-FPSGAMEEditor-ready.log`、`build-FPSGAME-final.log`。
- 用户未要求测试；不启动编辑器、PIE、测试或截图，由用户体验。
