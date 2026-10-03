# 主界面（开始菜单）规划 — 2026-10-02

## 1. 目的与范围

把原项目 `game-dev` 的开始界面（`menu-layer.js` + `panel-theme-backpack.css` 冷钢版）移植为 UE 主菜单：开局叠在已加载的主神空间上，由 `TransitLoadingSubsystem` 的启动弹层扩展实现；新增"多人游戏"入口，联机 MVP 走 P2P 直连（开房 `?listen` / 按 IP 加入）。

交付阶段：菜单结构 + 单人进入 + 联机弹层（昵称/开房/按 IP 加入/状态行/最近连接）。设置与操作说明做最小占位页，后续再填。

## 2. 信息结构

```
主页面 Main
├─ eyebrow：轮回档案 // 接入终端
├─ 标题：无尽轮回 ／ 副题：第一人称动作 RPG ／ 版本号
├─ 开始游戏（浅色主键）→ 页 StartChoice
│    ├─ 快速测试（沿用 ChooseLoadingMode(false)）
│    ├─ 完整预加载（沿用 ChooseLoadingMode(true)）
│    └─ 返回
├─ 多人游戏 → 页 Multiplayer（加入区块内联本页，少一次点击）
│    ├─ 昵称（SEditableTextBox，存 config，进 PlayerState->PlayerName）
│    ├─ 创建房间（主机）→ OpenLevel(当前图, "listen?Name=…")
│    ├─ 分隔线 + 加入区块：地址输入（IP[:端口]）+ 连接按钮
│    │    → OpenLevel(addr, "Name=…")
│    ├─ 最近连接列表（config，最多 4 条，点击即连）
│    ├─ 状态行（连接中/已开启/失败原因）
│    └─ 返回
├─ 设置 → 页 Settings（占位：预加载模式说明 + 返回）
├─ 操作说明 → 页 Help（占位：核心键位静态表 + 返回）
├─ 退出游戏（danger 语义色描边）
└─ info 卡：快捷操作提示两行（沿用原版文案）
```

页面切换走 `SWidgetSwitcher`，全部页一次构建、索引随 `State->Page` 变；输入框控件常驻引用在 View 状态上。

## 3. 布局

- 居中玻璃面板：宽 `min(560, vw-48)`，沿用现 StartupOverlay 的 SOverlay+SBox 骨架与视口自适应 lambda；竖向可滚（SScrollBox）兜底矮窗。
- 主键 52px 全宽、次键 44px、次级双格 grid 两列等宽——映射原版 `menu-btn / start-btn / menu-secondary-actions`。
- 弹层页与主页同面板内切换，不另起遮罩层（原版 start-game-choice 是独立遮罩，这里内嵌减少层级）。

## 4. 视觉角色

`ColdSteelUI` 主题值一一对应 bp-ui 变量：`GlassTint`↔shell、`TextPrimary/Secondary/Tertiary`↔text、`Accent`↔accent、`Border`↔line、`ButtonStyle()`↔menu-btn。主键浅色反色 = 自绘 `FButtonStyle`（`Gray(214)` 填充 + 深色文字 `Gray(18)`），不用主题外颜色。eyebrow/版本号用 `NumberFont`（等宽），标题 `TextFont(26,true)`，按钮文字 `TextFont(13,true)` letterspacing 由字号+padding 近似（Slate 无原生 letter-spacing，用字面空格或字号差表达层级）。

## 5. 数据合同

| 字段 | 来源/去向 |
|---|---|
| 昵称 | `GGameUserSettingsIni` `FPSGAME.Menu.Nick` 持久化；进游戏前 `PlayerState->SetPlayerName`；加入时走 `?Name=` URL option（引擎 InitNewPlayer 落到服务端 PlayerState→`BuildGuestSlotName` 槽位） |
| 创建房间 | `UGameplayStatics::OpenLevel(Hub, "listen")`；昵称先 `SetPlayerName` 落本机 |
| 加入房间 | `UGameplayStatics::OpenLevel(Address, "Name=<nick>")`；成功后地址写入 `FPSGAME.Menu.RecentHosts`（逗号分隔、去重、头插、上限 4） |
| 预加载两档 | 沿用 `ChooseLoadingMode(bool)`/`FPSGAME.Loading Mode` 既有合同 |
| 退出 | `UKismetSystemLibrary::QuitGame` |

## 6. 状态与输入

- 菜单持有：世界暂停（沿用 `bStartupPausedWorld`）、UIOnly 输入、光标常驻；Esc 在主页面不退出（避免误关菜单），在子页面=返回主页。
- 开始游戏两档点击 → `RequestedMode` → Tick 收 `ChooseLoadingMode`——不动既有链路。
- 创建房间/加入房间：先 `bStartupChosen=true` 拆菜单再走 OpenLevel；listen 重载后 `ShowStartupMenu` 的 `bStartupChosen` 分支自然放行不再弹菜单。
- 连接失败/非法地址（空、非法字符）→ 状态行红字，不旅行。
- NM_Client / 非本地控制器 / 无 FSlateApplication 一律不显示（沿用既有门槛）。

## 7. 文件与资源范围

- 改：`Source/FPSGAME/UI/TransitLoadingSubsystem.h/.cpp`（FStartupLoadingView 扩展、ShowStartupMenu 重建、页面方法）。
- 不改：`ChooseLoadingMode` 链路、BeginTransition/AfterMap、联机既有 RPC。不新增 .umap/资产。
- 退役：无（原启动弹层被新菜单原地替换）。
