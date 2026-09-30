# 联机开发工作日志（断点续接指南）

> 本文件是联机系统开发的**活文档**：任何人接手，从「当前状态」读起，按「下一步」继续。
> 策略与总体计划见 [MultiplayerStrategyAndPlan20260930.md](MultiplayerStrategyAndPlan20260930.md)（M0-M6 里程碑、审计证据、架构决策）。
> 规则：每完成一个动作就更新本文件；记录"做了什么/证据在哪/下一个动作"，宁细勿略。

---

## 0. 环境坐标（接手前先读）

| 项 | 值 |
|---|---|
| 主仓 | `D:\FPS3D\FPSGAME`（git，main 分支，主线并行会话在飞，**不要动**） |
| 联机 worktree | `D:\FPS3D\FPSGAME-mp`（分支 `feature/multiplayer`，基点 main@da91c6d6） |
| 引擎 | `E:\Program Files (x86)\UE_5.8`（EngineAssociation=5.8） |
| 构建命令 | `& 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAME Win64 Development "-Project=<worktree>/FPSGAME.uproject"` |
| 构建前置 | **必须**先查 UBT/cl.exe 进程（错峰三条，见主仓 WORKFLOW.md「构建串行化」节）；引擎级单实例互斥 |
| 冒烟测试 | 双 `-game -Windowed` 进程（**禁用 -RenderOffscreen**，2026-09-18 起约 15s 崩溃）；日志用 `-log=MPHost.log` / `-log=MPClient.log` 区分，位置 `<worktree>/Saved/Logs/` |
| Git Bash 坑 | URL 里 `/Game/...` 要 `MSYS_NO_PATHCONV=1` 前缀，否则前导斜杠被转义 |
| worktree 拆除坑 | 先 `rmdir` 断 junction（DDC 等）再 `git worktree remove`（既有教训） |

## 1. 当前状态（最后更新：2026-09-30 17:15，M1 进行中）

- M0 完成：计划文档定稿。
- M1 已完成：worktree 隔离环境、ColdSteelNet 插件骨架、**Game 目标编译 Succeeded**（16:41 产出 FPSGAME.exe 352MB）。
- M1 进行中：**FPSGAMEEditor 目标编译中**（双进程冒烟必须用 UnrealEditor.exe -game 形态，见 §5 坑#7）。
- **下一个动作**：Editor 编完后跑双进程基线冒烟（§4 命令已改用 UnrealEditor.exe 形态）→ 证据落日志 → 玩家本地门禁（§3.1）。

### ⚠️ worktree 特殊构造（接手必读）

主仓 `.gitignore:83` 排除了整个 `/Content/*`（81GB 重资产不在 git 里，只 44 个 JSON 强跟踪）。因此 worktree 采用**混合构造**：
- `Source/ Config/ Docs/` 等 = HEAD 检出 + **主仓工作区覆盖层**（`Tools/mp_overlay_sync.py` 同步，原因见 §5 坑#3）；
- `Content/`、`DerivedDataCache/`、`Plugins/AutoFootstep/`、`Plugins/VoxelFree/`、`Source/ThirdParty/Blast/Lib/` = **junction 指回主仓**（资产/预编译件共享，并发安全）；
- **git 纪律**：在 worktree 提交时**严禁 `git add -A`**（会把 junction 造成的"已删除"和主仓 WIP 覆盖层一起提交）；只 `git add Plugins/ColdSteelNet Tools/mp_overlay_sync.py Config/DefaultGame.ini Docs/` 等自己名下的显式路径；
- 拆除 worktree 前先 `rmdir` 掉全部 junction 再 `git worktree remove`。

### 分支提交状态
- `feature/multiplayer`（基点 main@da91c6d6）**尚未做任何提交**——所有产物还在工作区。建议冒烟通过后做首个提交（只含 Plugins/ColdSteelNet + Tools/mp_overlay_sync.py + Config/DefaultGame.ini 的 shader 覆盖 + Docs 三件）。

## 2. 时间线

### 2026-09-30（M1 启动：隔离环境 + 插件骨架 + 基线冒烟）

- [x] 计划+审计定稿（三路审计结论全部带 file:line 进计划文档附录）
- [x] worktree 建立：`git worktree add D:/FPS3D/FPSGAME-mp -b feature/multiplayer main`（基点 da91c6d6）+ Content/DDC junction（原因见上 ⚠️）
- [x] ColdSteelNet 插件骨架：
  - `Plugins/ColdSteelNet/ColdSteelNet.uplugin`（Runtime 模块，依赖 FPSGAME 主模块）
  - `AFPSNetGameMode : AGameMode`——出生点会话占用表（重生复用原点/断线释放/满员轮转错开）、PostLogin/Logout 的 MPTEST 日志行（冒烟断言锚点）、`bUseSeamlessTravel=true`（M4 前置）、MaxPlayers=4
  - 启用方式=URL 覆盖：`?game=/Script/ColdSteelNet.FPSNetGameMode`（**不改任何 ini**，主线零接触）
  - 有意不做的：传送门安装/天气补种（AFPSGAMEGameMode 的单机向逻辑，M4 再多人化）
- [x] Game 目标编译 **Succeeded**（16:41，352MB）。排障链：缺插件(junction AutoFootstep/VoxelFree)→缺 FPSBlast 预编译库(junction Blast/Lib)→HEAD 不可编(§5 坑#2/#3，覆盖层同步 529 文件+清 Intermediate)→插件自身三处编译错(APlayerStart 前置声明/ChoosePlayerStart_Implementation/公共包含路径)→过。
- [x] 冒烟第一轮失败→根因链两连：引擎 `BaseGame.ini:116 bShareMaterialShaderCode=True`（09-08 遗留）+ 全机无 `Engine/GlobalShaderCache-PCD3D_SM6.bin` ⇒ **裸 FPSGAME.exe 未打包形态在本机根本跑不起来**（=主线"-game 15 秒崩"悬案的解剖，§5 坑#5/#6/#7）。worktree 已加项目级 False 覆盖。
- [ ] FPSGAMEEditor 目标编译（进行中，双进程冒烟的前置）
- [ ] 双进程基线冒烟 + 证据采集（改用 UnrealEditor.exe -game 形态，§4）

### 基线冒烟的预期结果判读（先写好再跑，防止误读）

- **应当通**：客户端加入成功、两端 pawn 互见（ACharacter 移动引擎自带）、客人能看到主机的第三身身体/装备（主机是 locally controlled→身体组件在服务端采样写复制字段）。
- **预期不通（正是后续 M1/M2 要修的，出现=符合预期不是事故）**：
  - 主机看不到客人的身体/装备（复制字段只有本地采样路径，服务端喂料 `SetAuthoritativeState` 是 M1 下一步）；
  - 客人侧 hub 图无天气（FPSWeatherManager 服务端 spawn 不复制）；
  - 若客人进程崩在角色 BeginPlay（`FPSGAMECharacter.cpp:349-360` 对 Controller 直写输入模式、`:339` AttachPawn 抢档案）→ 属已知坑，本地门禁修复项。
- 日志锚点：`grep -E "MPTEST|Join succeeded|Possess" Saved/Logs/MPHost.log MPClient.log`。

## 3. 下一步队列（按序执行，改动前先读计划文档对应节）

1. **M1 续：玩家本地门禁**——`FPSGAMECharacter::BeginPlay` 的 `Profile->AttachPawn`（`FPSGAMECharacter.cpp:339`）与输入模式直写（`:349-360`）按本地拥有者分叉；远端 pawn 在客户端 BeginPlay 时 Controller 为空，注意 `Cast` 后判空防崩。
2. **M1 续：身体组件服务端喂料**——服务端 `ApplyColdSteelProfile` 后调用 `SetAuthoritativeState/SetAuthoritativeEquipment`（`FPSPlayerBodyComponent.h:23-24`，目前全库零调用），让主机能看到客人的身体/装备（当前只有"客人看主机"方向是通的，原因：复制字段只在 `IsLocallyControlled||Standalone` 时本地采样写入）。
3. **M1 验收**：双进程互见位置+身体+开火表现；单机模式零回归冒烟。
4. 之后进 M2（三闸门拆除+档案权威化，计划文档 §3）。

## 4. 冒烟测试标准姿势（复制即用，2026-09-30 修订为 UnrealEditor 形态）

```bash
# 主机（worktree 根目录下执行；UnrealEditor 形态见 §5 坑#7）
MSYS_NO_PATHCONV=1 "E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe" \
  D:/FPS3D/FPSGAME-mp/FPSGAME.uproject \
  /Game/GameMaps/DayNight_Lighting?listen?game=/Script/ColdSteelNet.FPSNetGameMode \
  -game -log=MPHost.log -Windowed -ResX=1024 -ResY=576 &
# 客人（等主机进图后启动，编辑器形态启动约 1-2 分钟要有耐心）
MSYS_NO_PATHCONV=1 "E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe" \
  D:/FPS3D/FPSGAME-mp/FPSGAME.uproject \
  127.0.0.1:7777 -game -log=MPClient.log -Windowed -ResX=1024 -ResY=576 &
# 收尾与断言（taskkill 后 sleep 5 再 grep，坑#11）
taskkill //IM UnrealEditor.exe //F
grep -aE "MPTEST|Join succeeded|Possess|SendJoin|Login request" Saved/Logs/MPHost.log
grep -aE "MPTEST|Join succeeded|Possess|SendJoin" Saved/Logs/MPClient.log
```

注意：双进程共用 Saved 目录；玩家档案 slot 用 `?ColdSteelProfile=MPClient` 隔离（命令行换槽，`ColdSteelProfileRuntime.cpp:108-113`）；监听服形态下 PersistState 本来就被 standalone 闸门拒写（M2 拆），不会写坏主机档案。

## 5. 已知坑与事实（踩过的都记这里，接手前通读一遍省半天）

1. **FAB 站内搜索**参数是 `q` 不是 `query`；fab.com 直抓 403 要走 IAB；FAB 详情页 goto 常超时但页面其实在加载（等 5s 再 snapshot）。
2. **主仓 git 视图不可信**：`git status` 报 Source 只有 7 个改动，实际全量 diff 有 **527 个文件**不同（与"git diff 展示会错序"旧案同源）。**任何"以主仓当前状态为准"的操作必须用文件级 diff/copy（`Tools/mp_overlay_sync.py`），不能用 git status。**
3. **HEAD 不可编**（老毛病"坏的是提交版"）：直接从 HEAD 检出的 Source 编不过（缺类/缺文件）。解法=坑#2 的覆盖层同步，同步后清掉 `Intermediate/` 再编（否则 UBT 的 SourceFileCache/TargetMetadata 缓存着 HEAD 版本的首包含信息，会报假 IWYU 错误"Expected X.h to be first header included"，文件明明是对的）。
4. **Bash 调 .bat 的三层坑**：直接执行引号路径失败；`cmd //c 'mklink ...'` 双引号内反斜杠被吞（要用单引号）；8.3 短路径（PROGRA~2）在 E 盘被禁用。**最终可用姿势：`powershell -NoProfile -Command "& 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAME Win64 Development -Project=D:/FPS3D/FPSGAME-mp/FPSGAME.uproject"`**。
5. **引擎 `Engine/Config/BaseGame.ini:116` 有 `bShareMaterialShaderCode=True`**（2026-09-08 19:43 改的，疑似打包会话遗留）。后果：未打包游戏进程在 `FShaderCodeLibrary::InitForRuntime` 直接暴毙。已在 worktree `Config/DefaultGame.ini` 项目级覆盖 False。**主线修复建议同款**（这很可能就是主线"-game 15 秒崩溃"悬案的一半）。
6. **`Engine/GlobalShaderCache-PCD3D_SM6.bin` 全机不存在**：裸跑 `Binaries/Win64/FPSGAME.exe`（未打包、装版引擎）必死于"built to load COOKED content"。这是悬案的另一半。装版引擎的正确 -game 姿态见坑#7。
7. **-game 的正确姿态 = `UnrealEditor.exe <uproject> <map>?… -game`**（编辑器二进制游戏模式，按需编着色器），**不是**裸 FPSGAME.exe。这要求 worktree 编过 **FPSGAMEEditor 目标**（UnrealEditor-FPSGAME.dll 等）。UnrealEditor-Cmd 跑命令行同理。双进程冒烟全部用这个形态。
8. UE5.8 里 `AGameModeBase::ChoosePlayerStart` 是 BlueprintNativeEvent：C++ 侧重写 `ChoosePlayerStart_Implementation`。
9. 平铺布局模块（无 Public/Private 分层，如 FPSGAME 主模块）的头文件默认对外不可 include：外部插件 Build.cs 要 `PublicIncludePaths.Add("$(ProjectDir)/Source/FPSGAME")`。
10. 双进程共用 Saved：日志用 `-log=MPHost.log`/`-log=MPClient.log` 分名；玩家档案槽用 `?ColdSteelProfile=` 隔离；监听服形态下档案写入本来就被 standalone 闸门拒绝（M2 拆），不会写坏。
11. `taskkill //F` 强杀后日志缓冲可能未落盘，grep 前先 `sleep 5`。
12. （持续追加……）
