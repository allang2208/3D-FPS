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

## 1. 当前状态（最后更新：2026-10-01 13:45，M4 编译过、丘陵验证被用户暂停）

- M1-M3 全部闭环；主仓闪退已修（用户编辑器已带修复运行）。
- **M4 世界同步代码完成且编译 Succeeded**（worklog 上一版所列十处改动）。
- **M4 首轮丘陵验证定位到关键阻塞**：客户端网络 travel 到重资产图（丘陵/DayNight 同病根）1.3s 静默失败 `Travel Failure: Failed to load package 'L_TemperateHills_Initial'`（直开同图正常——主机 50s 即 HILLS_READY seed=-2051251055 全 14/14 格）。**规避方案已实现并编译**：`UColdSteelNetConnectSubsystem`（`-MPConnect=<addr> -MPConnectDelay=<秒>`，客户端先本地直开把资产编译热，再从进程内 open 连线，旅行重载命中热缓存）。
- **验证被用户暂停**（"先暂停吧"）：暂停前主机第二轮 HILLS_READY 已就绪，客户端尚在本地直载阶段（无关键行）。**恢复=重跑 §4 丘陵姿势**（客户端带 -MPConnect=127.0.0.1:7777 -MPConnectDelay=150 直开丘陵图），断言客户端 `connect issuing` → `Welcomed` → **`MPTEST hills client session: seed=-2051251055`（与主机同种子=确定性重建成立）**。
- M4 之后的余项：挖坑编辑 OnRep 双端一致实测、传送门 seamless travel、昼夜一致性观察、重图 travel 失败的根治（当前只有规避）。

### ⚠️ worktree 特殊构造（接手必读）### ⚠️ worktree 特殊构造（接手必读）### ⚠️ worktree 特殊构造（接手必读）### ⚠️ worktree 特殊构造（接手必读）### ⚠️ worktree 特殊构造（接手必读）

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

## 3.9 PIE/联机客户端视口修复（2026-10-01，TransitLoadingSubsystem.cpp，未入分支提交）

**症状**：PIE 双人（Listen Server）或联机客户端视口卡在过场加载进度条（纹丝不动）；服务器侧登录/档案链全绿。
**根因链**：①过场遮罩 View 的完成条件是单机流程旗标（bDestinationLoaded 等），联网客户端世界永远凑不齐；②BeforeMap 置位的 `bMapLoading` 在 AfterMap 里被 `World->GetGameInstance()!=GetGameInstance()` 守卫挡住不清理（PIE 多实例/网络旅行下判定不等），后续 Tick 全部在 `if(!View||bMapLoading)return` 提前退出，遮罩淡出/移除代码永远不跑——进度条冻结在"准备完成"。
**修复**（`Tick` 顶部，注入在 StartupView 检查之前）：
```cpp
if(View&&FinishedAt==0&&GetWorld()&&GetWorld()->GetNetMode()==NM_Client
    &&UGameplayStatics::GetPlayerPawn(GetWorld(),0))
{
    UE_LOG(... net-client bypass ...);
    bStartupChosen=true;bDestinationLoaded=true;bCompletePreload=true;
    bMapLoading=false;bPreparationFailed=false;
    RestoreGameplayInput();
    if(View.IsValid()){RemoveOverlay();View.Reset();FinishedAt=0;} // 当场撕遮罩，不走依赖旗标的淡出路径
    return;
}
```
**坑**：Build.bat/UBT 的 Live Coding 检查在引擎层全局生效——主仓编辑器开着会挡住 worktree 构建（连直接调 UBT dll 也挡）；需主编辑器 Ctrl+Alt+F11 或关闭。引擎自带 dotnet 在 `Engine/Binaries/ThirdParty/DotNet/10.0/win-x64/dotnet.exe`。

## 3.8 M3 战斗权威化改动清单（2026-10-01，未入分支提交，重放即生效）

> 游戏模块侧；插件侧（通道命中上报/回执/分块上传/合成射击钩/模块注册）已提交分支。

**① `Skills/ColdSteelSkillRules.h/.cpp`**：命名空间内新增
- `using FColdSteelNetHitForward = bool(*)(AActor*, const FHitResult&, float, const FVector&, const FColdSteelSkillShot&)` + `NetHitForward()`（函数指针存取）；
- `AwardKillByOwner(UGameInstance*, AController* Instigator, AActor* Victim, int64 XP)`：按射手归属选档案（远端玩家 pawn 的 `GetNetShadowProfile()` 优先，回退单例）；
- `ApplyHit` 顶部一行：`if(Shooter&&!Shooter->HasAuthority()&&NetHitForward()&&NetHitForward()(Shooter,Hit,Damage,Direction,Shot))return 0.f;`

**② `Monsters/FPSCombatHealthComponent.h/.cpp`**：Health 改 `ReplicatedUsing=OnRep_Health`、MaxHealth 加 `Replicated`；`GetLifetimeReplicatedProps`(DOREPLIFETIME×2)+`OnRep_Health`（测试期 Warning 日志）；BeginPlay `SetIsReplicated(true)`；cpp 加 `Net/UnrealNetwork.h`。

**③ 六处击杀奖励**（HandBrain/FleshHand/HundredEyedSlag/PoisonMaggot/NurseZombie/Wolf 各 .cpp）：`PC->IsLocalController()&&GetGameInstance())...GetSubsystem...AwardKill` → `GetGameInstance())ColdSteelSkills::AwardKillByOwner(GetGameInstance(),PC,this,ExperienceReward)`；五文件头部加 `#include "../Skills/ColdSteelSkillRules.h"`。

**④ 坑**：5.8 的 FHitResult 用 `FActorInstanceHandle HitObjectHandle`（不是 FHitObjectHandle），赋值 `Hit.HitObjectHandle=FActorInstanceHandle(Target)`；模块类继承 `IModuleInterface`（FDefaultModuleInterface 不存在）；怪物 cpp 原先不含 SkillRules 头。

## 3.7 M2 档案权威化改动清单（2026-09-30，游戏模块 6 处，未入分支提交，重放即生效）

> 与 §3.6 同规则：文件=主仓 WIP 覆盖层+以下改动；插件侧（通道组件+GameMode 装配）已提交分支。

**① `Source/FPSGAME/FPSGAMECharacter.h`**（RearGripAttachment 声明后加）：
```cpp
    /** M2 联机：远端玩家在服务端的影子档案（ColdSteelNet 通道组件注入；主机自己的 pawn 不用，走单例）。 */
    UPROPERTY(Transient) TObjectPtr<class UColdSteelStatusModel> NetShadowProfile;
    class UColdSteelStatusModel* GetNetShadowProfile() const { return NetShadowProfile; }
```

**② `Source/FPSGAME/UI/ColdSteelStatusModel.h`**（`Snapshot()` 声明后加）：
```cpp
    UColdSteelStatusModel* CreateShadowModel(const FColdSteelProfile& GuestProfile);
    void AdoptNetMirror(const FColdSteelProfile& External);
```

**③b `Source/FPSGAME/UI/ColdSteelProfileRuntime.cpp`（2026-10-01 追加）**：`CreateShadowModel` 里 `NewObject<UColdSteelStatusModel>` 的 Outer 必须传 `GetGameInstance()`（子系统类 ClassWithin=UGameInstance，传 TransientPackage 撞 UObjectGlobals:3480 断言崩进程）。

**③ `Source/FPSGAME/UI/ColdSteelProfileRuntime.cpp`**：
- `Publish` 定义后新增 `CreateShadowModel`（NewObject 影子；复制 Definitions/WeaponAmmoGroups/AmmoTypes/StaminaTuning/全部技能定义成员；`Publish(GuestProfile)`；`bPersistenceBlocked=true`）与 `AdoptNetMirror`（=Publish）；
- `PersistState` 闸门改判：`bPersistenceBlocked||NetMode==NM_DedicatedServer` 才拒（放开监听服/客户端写各自磁盘副本）。

**④ `Source/FPSGAME/Monsters/FPSCombatHealthComponent.cpp`**（DamageAfterArmor 模型查找）：
```cpp
    else if(auto* NetCharacter=Cast<AFPSGAMECharacter>(GetOwner()))Model=NetCharacter->GetNetShadowProfile(); // M2: 远端玩家防御走影子档案
```

**⑤ `Source/FPSGAME/Items/FPSPotionUseComponent.cpp`**：TryBegin 判据去掉 `||GetNetMode()!=NM_Standalone`。

**⑥ `Source/FPSGAME/Skills/FPSLightningComponent.cpp`**：Trigger 判据去掉 `||GetWorld()->GetNetMode()!=NM_Standalone`。

**架构注记**：防循环依赖（插件依赖 FPSGAME，游戏模块不能反过来依赖插件）的关键=角色上的 `NetShadowProfile` 指针作为两侧交接面；上行心跳固定 0.8s 全量快照（LAN 无压力，WAN 增量化记入 perf 台账）；建造存档闸（VoxelBuildWorldSave）按计划留 M5（其初始化闸本就阻止联机形态启用，M2 拆了也无功能面）。

## 3.6 M1 门禁/喂料改动清单（未入分支提交，重放即生效）

> 基线=主仓 WIP 覆盖层同步后的 worktree 文件；以下为叠加在其上的全部改动，逐处可粘。

**① `Source/FPSGAME/FPSGAMECharacter.h`**（EndPlay 声明后加）：
```cpp
    /** M1 联机分叉：档案（GameInstance 单例）只允许挂到本机玩家的 pawn 上。 */
    virtual void PossessedBy(AController* NewController) override;
    virtual void OnRep_Controller() override;
private:
    /** 幂等的本地档案挂载：非本机控制的 pawn 一律不挂（防止监听服上远端 pawn 抢走主机档案）。 */
    void TryAttachLocalProfile();
    bool bLocalProfileAttached = false;
public:
```

**② `Source/FPSGAME/FPSGAMECharacter.cpp` BeginPlay（原 `Profile->AttachPawn(this)` 行替换）**：
```cpp
    // M1 联机分叉：单机维持原时序；联网形态下 BeginPlay 时 Controller 常未就绪，
    // 真正挂载点挪到 PossessedBy（服务端）与 OnRep_Controller（客户端自主 pawn）。
    if (GetNetMode() != NM_ListenServer && GetNetMode() != NM_DedicatedServer) TryAttachLocalProfile();
```

**③ `Source/FPSGAME/FPSGAMECharacterProfile.cpp`（EndPlay 实现后追加三个函数）**：
```cpp
void AFPSGAMECharacter::PossessedBy(AController* NewController)
{
    Super::PossessedBy(NewController);
    TryAttachLocalProfile();
}
void AFPSGAMECharacter::OnRep_Controller()
{
    Super::OnRep_Controller();
    TryAttachLocalProfile();
}
void AFPSGAMECharacter::TryAttachLocalProfile()
{
    if(bLocalProfileAttached)return;
    if(!IsLocallyControlled())return;
    bLocalProfileAttached=true;
    if(GetGameInstance())if(auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())Profile->AttachPawn(this);
}
```

**④ `Source/FPSGAME/Characters/FPSPlayerBodyComponent.cpp` TickComponent（`else DisplayState=ReplicatedState;` 前插服务端分支）**：
```cpp
    else if(GetOwner()->HasAuthority())
    {
        // M1 联机：监听服上的远端玩家 pawn——服务端按权威运动状态采样并发布，
        // 客户端 OnRep 消费。装备数据源要等 M2 档案权威化，这里只发布身体状态。
        DisplayState=SampleLocalState();
        ReplicatedState=DisplayState;
    }
```

## 3. 下一步队列（按序执行，改动前先读计划文档对应节）

### 3.0 闭合 M1 末跳（最近的动作，前置=机器空闲窗口）
直接用 §4 的现成命令重跑一轮（带登录插桩的 NetGameMode 已在分支里）。判读法：
- 主机 `MPTEST Login enter` 之后 5 秒内没有 `Login exit` → Login 内部卡（SpawnPlayerController 链），看卡前最后一条日志定位；
- `Login exit` 有 PC 但没有 `PostLogin`（远端玩家）→ 连接在 PostLogin 前被关，查客户端 LoadMap 是否又失败；
- 客户端 `Welcomed by server` 后 `Failed to load package` → 客户端 travel 地图加载中止（疑与连接被关互为因果，轻量图 GameDefaultMap 已改，观察是否复现）。
- **机器负载是当前最大变量**：用户在用机器时主机 240s 起不完；挑空闲窗口跑，或把客户端轮询拉到 15 分钟。
- 备选消歧实验：客户端先直开轻量图（probe 命令见坑#7 姿态），进世界后从进程内控制台 `open 127.0.0.1:7777`（绕开占位图路径）。

### 3.1 M1 续：玩家本地门禁
`FPSGAMECharacter::BeginPlay` 的 `Profile->AttachPawn`（`FPSGAMECharacter.cpp:339`）按本地拥有者分叉（监听服上远端玩家 pawn 会抢主机档案）。`FPSGAMECharacter.cpp:349-360` 的输入模式直写已有 Cast 判空保护（实证：客户端进程没崩在那）。
### 3.2 M1 续：身体组件服务端喂料
服务端 `ApplyColdSteelProfile` 后调 `SetAuthoritativeState/SetAuthoritativeEquipment`（`FPSPlayerBodyComponent.h:23-24`，全库零调用）。当前只有"客人看主机"方向通（复制字段仅 locally-controlled 时本地采样写入）。
### 3.3 M1 验收
双进程互见位置+身体；单机零回归冒烟。之后进 M2（三闸门+档案权威化，计划文档 §3）。

## 3.5 冒烟战况记录（2026-09-30 下午，按轮次）

| 轮次 | 形态 | 结果 | 关键发现/修复 |
|---|---|---|---|
| 1 | 裸 FPSGAME.exe 双进程 | 双双启动暴毙 | 引擎 `BaseGame.ini:116 bShareMaterialShaderCode=True`（09-08 遗留）+ 全机无 GlobalShaderCache-*.bin ⇒ **裸 exe 未打包形态在本机根本跑不起来**（=主线"-game 15秒崩"悬案解剖）；已加项目级 False 覆盖 |
| 2 | UnrealEditor.exe -game 窗口 ×2 | 主机 55s 后崩 | 崩在 PythonScriptPlugin（StateTreeToolset 的 init_unreal.py 在 -game 态空指针）；已禁 Python 插件 |
| 3 | 窗口 ×2 | 主机被关窗退出 | 测试窗口弹在用户桌面被手动关闭（ViewportClosed→Logout PC_0）；改离屏 |
| 4 | RenderOffscreen ×2 | 客户端 92s 扫描饿死握手+DDC 编译 OOM | 首轮必扫 81GB 资产注册表；握手 20s 超时被打死；后续主机 D3D12 GPU 崩溃（750 Ti 双进程） |
| 5 | nullrhi ×2 | 主机"近植物人" | nullrhi 监听服不泵网络包（零 accept），弃用 |
| 6 | offscreen+超时 180s | **客户端 Welcomed by server ✅** | 超时修复让握手熬过启动停顿；主机收到 Login request；末跳（Login→PostLogin#2）仍未闭合，客户端 travel 地图加载失败（"Failed to load package"，直开同图秒成功——网络 travel 上下文特有） |
| 7 | 轻量图 L_PoisonMaggot | 客户端仍 OOM | 发现客户端连 IP 时引擎先载 **GameDefaultMap=DayNight 当占位世界**（拖全武器目录）；已把 worktree GameDefaultMap 改指轻量测试图 |
| 8 | 同上+机器被用户重度占用 | 主机 240s 未起完 | 判定：抢资源必输，停止磨测试，落提交+文档收尾 |

## 4. 冒烟测试标准姿势（复制即用，2026-09-30 19:50 修订）

```bash
# 主机（worktree 根目录下执行；轻量图 + 离屏 + 免 Python；形态原因见 §5 坑#7）
MSYS_NO_PATHCONV=1 "E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe" \
  D:/FPS3D/FPSGAME-mp/FPSGAME-Online.uproject \
  "/Game/Tests/PoisonMaggot/L_PoisonMaggot?listen?game=/Script/ColdSteelNet.FPSNetGameMode" \
  -game -log=MPHost.log -RenderOffscreen -ResX=640 -ResY=360 -nosound "-LogCmds=r.RayTracing 0" &
# 客人（主机 MPTEST NetGameMode active 出现后再启动；断言词是 Welcomed 不是 Join succeeded）
MSYS_NO_PATHCONV=1 "E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe" \
  D:/FPS3D/FPSGAME-mp/FPSGAME-Online.uproject 127.0.0.1:7777 \
  -game -log=MPClient.log -RenderOffscreen -ResX=640 -ResY=360 -nosound "-LogCmds=r.RayTracing 0" &
# 断言（UE 日志时间戳是 HH.MM:SS 点分隔，grep 时别写冒号；taskkill 后 sleep 6 再读）
grep -a "MPTEST\|Login request" Saved/Logs/MPHost.log        # 期望出现第2个 PostLogin/NumPlayers=2
grep -a "Welcomed by server\|MPTEST\|Possess" Saved/Logs/MPClient.log
taskkill //IM UnrealEditor.exe //F
```

注意：双进程共用 Saved；档案槽 `?ColdSteelProfile=` 隔离；监听服形态下 PersistState 被 standalone 闸门拒写（M2 拆），不会写坏档案。

## 5. 已知坑与事实（踩过的都记这里，接手前通读一遍省半天）

1. **FAB 站内搜索**参数是 `q` 不是 `query`；fab.com 直抓 403 要走 IAB；FAB 详情页 goto 常超时但页面其实在加载（等 5s 再 snapshot）。
2. **主仓 git 视图不可信**：`git status` 报 Source 只有 7 个改动，实际全量 diff 有 **527 个文件**不同（与"git diff 展示会错序"旧案同源）。**任何"以主仓当前状态为准"的操作必须用文件级 diff/copy（`Tools/mp_overlay_sync.py`），不能用 git status。**
3. **HEAD 不可编**（老毛病"坏的是提交版"）：直接从 HEAD 检出的 Source 编不过（缺类/缺文件）。解法=坑#2 的覆盖层同步，同步后清掉 `Intermediate/` 再编（否则 UBT 的 SourceFileCache/TargetMetadata 缓存着 HEAD 版本的首包含信息，会报假 IWYU 错误"Expected X.h to be first header included"，文件明明是对的）。
4. **Bash 调 .bat 的三层坑**：直接执行引号路径失败；`cmd //c 'mklink ...'` 双引号内反斜杠被吞（要用单引号）；8.3 短路径（PROGRA~2）在 E 盘被禁用。**最终可用姿势：`powershell -NoProfile -Command "& 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAME Win64 Development -Project=D:/FPS3D/FPSGAME-mp/FPSGAME-Online.uproject"`**。
5. **引擎 `Engine/Config/BaseGame.ini:116` 有 `bShareMaterialShaderCode=True`**（2026-09-08 19:43 改的，疑似打包会话遗留）。后果：未打包游戏进程在 `FShaderCodeLibrary::InitForRuntime` 直接暴毙。已在 worktree `Config/DefaultGame.ini` 项目级覆盖 False。**主线修复建议同款**（这很可能就是主线"-game 15 秒崩溃"悬案的一半）。
6. **`Engine/GlobalShaderCache-PCD3D_SM6.bin` 全机不存在**：裸跑 `Binaries/Win64/FPSGAME.exe`（未打包、装版引擎）必死于"built to load COOKED content"。这是悬案的另一半。装版引擎的正确 -game 姿态见坑#7。
7. **-game 的正确姿态 = `UnrealEditor.exe <uproject> <map>?… -game`**（编辑器二进制游戏模式，按需编着色器），**不是**裸 FPSGAME.exe。这要求 worktree 编过 **FPSGAMEEditor 目标**（UnrealEditor-FPSGAME.dll 等）。UnrealEditor-Cmd 跑命令行同理。双进程冒烟全部用这个形态。
8. UE5.8 里 `AGameModeBase::ChoosePlayerStart` 是 BlueprintNativeEvent：C++ 侧重写 `ChoosePlayerStart_Implementation`。
9. 平铺布局模块（无 Public/Private 分层，如 FPSGAME 主模块）的头文件默认对外不可 include：外部插件 Build.cs 要 `PublicIncludePaths.Add("$(ProjectDir)/Source/FPSGAME")`。
10. 双进程共用 Saved：日志用 `-log=MPHost.log`/`-log=MPClient.log` 分名；玩家档案槽用 `?ColdSteelProfile=` 隔离；监听服形态下档案写入本来就被 standalone 闸门拒绝（M2 拆），不会写坏。
11. `taskkill //F` 强杀后日志缓冲可能未落盘，grep 前先 `sleep 5`。
12. **UE 日志时间戳是 `HH.MM:SS` 点分隔**（`[2026.09.30-10.57.13:255]`）——grep/awk 窗口匹配别写成冒号，连续踩了两次。
13. **`Plugins/` 整个被 .gitignore 忽略**（和 Content 同款）——提交新插件要 `git add -f Plugins/ColdSteelNet`，且插件内自建 `.gitignore`（Intermediate/Binaries/），否则构建产物进库。
14. **裸 `Binaries/Win64/FPSGAME.exe` 未打包跑不起来是机器现状**（引擎缺 GlobalShaderCache-*.bin + BaseGame.ini 的 bShareMaterialShaderCode=True）——这解释了主线"-game 15 秒崩"悬案。**-game 唯一可靠形态=UnrealEditor.exe**（坑#7）。
15. **客户端连 `IP:7777` 时引擎先加载 GameDefaultMap 当占位世界**——客户端的重量由 GameDefaultMap 决定，与主机地图无关。冒烟已把 worktree 的 GameDefaultMap 改指轻量测试图（`Config/DefaultEngine.ini:5`，主线无关）。
16. **握手超时与启动停顿的赛跑**：客户端首载 30-90s 停顿会打死默认 20s 初始连接超时。worktree 已配 `[/Script/Engine.GameNetworkManager] InitialConnectTimeout=180 ConnectionTimeout=180`（`Config/DefaultEngine.ini:174`）。正式玩家用裸 exe 无此问题，接入主线时回调。
17. **双 D3D12 离屏进程在 750 Ti 上会 GPU 崩溃**（D3D12Util.TerminateOnGPUCrash，约 4 分钟窗口）；nullrhi 的监听服不泵网络包（零 accept）。当前冒烟姿态=offscreen+`r.RayTracing 0`+轻量图，加入完成后尽快收尾。
18. **`?game=` URL 覆盖、地图直开、+覆盖直开** 三种形态都验证可用（probe A/B），排除该嫌疑。
19. 机器被用户重度占用时主机 240s 起不完——冒烟要挑空闲窗口，或接受失败重试。
20. （持续追加……）
