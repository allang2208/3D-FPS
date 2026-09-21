# Live Coding 与常规 Editor 构建的边界（2026-09-19 更新）

日常执行方式以 [保持编辑器打开的开发规则](../../ue5-auto-assistant/references/editor-open-development.md) 为准。**已有函数体改动**可用 Live Coding 在当前编辑器应用；结构变化按影响范围选择常规构建，不能把所有头文件或新增 UFUNCTION 都归为引擎强制关闭。FPSGAME 带资产引用的 USTRUCT 变化，以及新 C++ 类写入关卡/资产前，仍先关闭编辑器完成常规目标构建。

Live Coding 可能生成补丁文件，但补丁成功不等于基础 Editor DLL 已更新；未完成常规构建时不保证下一次启动或打包已包含修改。常规目标构建允许增量，不默认 Clean/Rebuild。下列历史排查、单文件编译校验和落盘复核仅在用户明确要求时执行；必要构建与错误处理照常完成。

## 可以热补丁

- `.cpp` 中已有函数的实现、运行时计算和读取逻辑；构造函数默认值不一定更新已有实例。
- 纯 C++ 结构体的布局变化也要考虑旧实例和所有调用方；仅使用指针或 `TUniquePtr` 持有不代表可安全热更新。停止 PIE 不保证所有编辑器对象已释放，无法明确生命周期时优先常规构建后重新打开。

## 本项目的资产限制与状态处理

- **带资产的 USTRUCT**（例如调色板数据资产里的 `FVoxelPhysicalMaterial`）改字段布局或默认值：热补丁后新 struct tag 与已保存资产不匹配，字段会整体读成 `None`，之后任何"读出来再写回去"的脚本都会把空值写进资产。必须：关编辑器 → 全量编译 → 再改资产。
- **依赖文件级 `static` 的跨补丁状态**：不要假定模块更新会保留或正确重建状态。历史表现是"只有打过补丁的那个会话行为不对"；需要按生命周期修正持有方式，或在使用点从安全宿主（`UPROPERTY` 持有的 Actor / 组件）重新解析引用。

## 构建状态与按需验证

- 发起必要编译后读取该次结果，例如 `LogLiveCoding: Display: Live coding succeeded|failed`；命令已提交不等于编译完成。
- 常规构建完成前，明确说明"已应用到当前编辑器，尚未完成常规目标构建"，不将补丁成功写成基础 DLL 已更新，也不为证明重启后生效自动重启或测试。
- 改已加载的 `.uasset` 在**当前编辑器进程内**做（MCP/Python）。按目标保存并处理返回的错误；确需包级保存时可用 `EditorLoadingAndSavingUtils.save_packages([load_package(path)], False)`，不盲目保存所有脏包。
- 用户明确要求落盘验证时，再按范围结合磁盘状态与独立进程读回；同进程读回只能说明内存状态。日常制作不默认追加字节扫描、独立进程或验收。
- 日志在 `Saved/Logs/FPSGAME.log`：排查先看限流过的诊断行（如 `VOXEL_AIM` / `VOXEL_REJECT` / `VOXEL_FRESH`）与 `Live coding` 行；全量编译的落地产物看 `Binaries/Win64/UnrealEditor-FPSGAME.dll` 的时间戳。

## 常用命令

```powershell
# 触发一次热补丁（编辑器必须在运行）
python Tools/AssetPipeline/ue_python_exec.py --statement "import unreal; unreal.SystemLibrary.execute_console_command(None, 'LiveCoding.CompileSync'); print('requested')"

# 常规 Editor 目标构建（本项目先正常关闭编辑器；不默认 Clean/Rebuild）
& 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat' FPSGAMEEditor Win64 Development -Project="D:\FPS3D\FPSGAME\FPSGAME.uproject" -WaitMutex
```

## 症状 → 先查什么

| 症状 | 先查 |
| --- | --- |
| 同一个 bug 只在这个会话出现 | 文件级 `static` 是否被模块重载复位 |
| 资产字段全读成 `None` | 是否热补丁改过带资产的 USTRUCT；关编辑器全量编译后按清单修复 |
| "改了代码没反应" | 必要构建是否完成；是否仍在使用旧实例、构造默认值或已保存的属性覆盖 |
| 编辑器关掉后行为回退 | 常规 Editor 目标构建是否包含该改动；基础 DLL 与源码是否仍不一致 |

## 单文件编译校验的边界（2026-09-16）

- UBT 在 `Intermediate/Build/Win64/x64/<Target>/<Config>/<Module>/*.cpp.obj.rsp` 留下每个 TU 的完整编译命令（含共享 PCH）。**只改 `.cpp`** 时可以用它快速校验：
  `cmd /c ""<vcvarsall.bat>" x64 && cd /d "E:\Program Files (x86)\UE_5.8\Engine\Source" && cl.exe "@D:/FPS3D/FPSGAME/Intermediate/.../X.cpp.obj.rsp""`（工作目录必须是引擎 `Engine/Source`，共享 rsp 里的 `/I` 都是相对该目录）。
- **改过带 UHT 的头文件后这条路径无效**：`GENERATED_BODY()` 会拼出 `<文件ID>_<行号>_GENERATED_BODY` 宏名，头里插删行会让宏名对不上，出现 `缺少";"(在"<class-head>"的前面)`、`NativeConstruct 不是成员` 之类假错误——必须让 UBT 重跑 UnrealHeaderTool（完整构建）。
- 生成器为 `-SingleFile=` 时不带共享 PCH，会报引擎头里的 `C2143/C2039` 假错误，同样不能作为结论。

## 编辑器内远程执行的崩溃陷阱（2026-09-16）

不要在用 `Tools/AssetPipeline/ue_python_exec.py` 连到**正在运行的编辑器**时调用材质编辑器相关查询（`unreal.MaterialEditingLibrary.get_material_property_input_node` 等）：本机实测触发 `UnrealEditor-MaterialEditor.dll` 访问违例，直接把编辑器打崩且可能丢失未保存改动。材质图/属性接线查询放无界面 `UnrealEditor-Cmd -ExecutePythonScript` 进程；必须在编辑器内改材质时只用 `get_material_expressions` / `connect_material_expressions` / `recompile_material` / `save_loaded_asset`，并先用 Restart Manager 确认资产是否被编辑器独占。

## 构建被进程挡住的判定（2026-09-17）

- `Tools/Build/Build-Editor.ps1` 只要发现任何 `UnrealEditor.exe` 或 `UnrealEditor-Cmd.exe`（命令行含 `FPSGAME.uproject` 或为空）就直接拒绝构建、并且**不会**结束进程。并行会话跑的 headless 资源脚本（`UnrealEditor-Cmd -run=pythonscript`）也算，属于短暂占用：先用 `Get-CimInstance Win32_Process -Filter "Name='UnrealEditor-Cmd.exe'"` 看命令行和启动时间，等它自己退出（通常数秒到数十秒）再重跑，不要替别人关进程。
- 失败日志先分辨归属：`Saved/BuildEditor/build-*.log` 里报错的路径若是并行会话的文件（体素地形、建筑、怪物等），照 WORKFLOW 第 7 节保留对方改动，只在自己的文件上解决；同一文件混着双方未提交改动时按 hunk 精确暂存，不要整文件提交。
- **别人的文件编译不过时，完整构建走不到你的代码**（2026-09-21 实例）：并行会话新增的未提交 `Source/FPSGAME/Weapons/RuneGoldMaterialCommandlet.cpp` 先 include `UObject/SaveLoose.h`、改一版后又 include `EditorAssetLibrary.h`，两者在本引擎/本模块都不可用，UBT 在第一个编译动作就 `fatal error C1083` 退出——**没有链接**，本轮改动没进 `UnrealEditor-FPSGAME.dll`。处理：保留对方文件、不代改不代删、不反复重试等它，也不结束对方编辑器；仅在当前对话说明阻塞（禁跨会话协调）。
- 此时能证明的只有自己的 TU：`& '<Engine>\Build\BatchFiles\Build.bat' FPSGAMEEditor Win64 Development -Project="D:\FPS3D\FPSGAME\FPSGAME.uproject" -SingleFile=Source/FPSGAME/Weapons/X.cpp -WaitMutex -NoHotReload -NoUBTMakefiles`，把本次改动过的 `.cpp` 逐个跑一遍。**成功**说明该 TU 在本工作区能编过；**失败**可能是上面单文件校验一节说的无共享 PCH 假错误，不能当结论。两者都不等于完整构建/链接，更不等于运行验收——交付时如实写"未编译进二进制"。
- 对方修好后重跑 `Tools/Build/Build-Editor.ps1` 即可（增量构建会把本次 TU 补上）；`Target is up to date`（0 个动作）是**有效成功状态**，不必强推 rebuild。要确认"本次改动确实进了 DLL"，看 `Binaries/Win64/UnrealEditor-FPSGAME.dll` 的时间戳是否晚于自己全部源码——本轮 DLL 22:21:48、最晚源码 21:34:20，据此判定已包含（对方 22:17 修好文件后 22:21:48 的构建完成链接）。这仍不等于运行验收。
- **直接证明法**（2026-09-21 第二轮）：UE 的字符串字面量在 Windows 上是 **UTF-16LE**，所以在 DLL 里按宽字符搜自己新增的 CVar 名就能证明代码进没进二进制——`py -c "d=open(r'Binaries\Win64\UnrealEditor-FPSGAME.dll','rb').read(); print('fps.Tracer.Every'.encode('utf-16-le') in d)"` → `True`；顺手搜一个早就存在的 CVar 名作对照。按 ASCII 搜会全部 `MISSING`，不要据此误判成"没编进去"。被编辑器占用而反复被守卫拒绝时，等窗口重试（每 45–60 s，别人不关就别动它），窗口一出现增量构建会自己补上。

## 热补丁类不能成为关卡/资产的依赖（2026-09-18 事故，青铜火把）

**症状**：摆好的一批 actor 在编辑器重启后"整批消失"，加载日志逐条报
`LoadErrors: Warning: 创建导出：资产"<ComponentName>"的外部容器加载失败：<Class> ... :PersistentLevel.<Actor>_1`。

**根因**：这些 actor 的类当时只存在于 Live Coding 补丁里（补丁成功、摆件、保存关卡都正常），但磁盘上的
`UnrealEditor-FPSGAME.dll` 仍是旧构建、不含这个类。编辑器一重启，类没了 → actor 建不出来（内存里 0 件）。
这是当时基础 Editor DLL 未包含新类、重新启动时类型缺失的项目案例；不将它概括为所有 UE 版本都没有补丁文件或补丁加载机制。

**规矩**：

- 新增 C++ 类并且要**写进关卡/资产数据**时：先正常关闭编辑器、完成常规 Editor 目标构建、重新打开，再摆件与保存。Live Coding 可用于当前会话的迭代，但不替代本项目的新类落盘构建。
- 若关卡已经引用了补丁中新加的类，先保留当前完整的资产与源码改动，协调正常退出，再完成常规构建后重新打开；不要写成"关闭前先做需要关闭编辑器的常规构建"。
- 关卡出现"缺类"时**不要保存这张图**：内存里是残状态（actor 数量为 0 或半残），一保存就把磁盘上的 actor 抹掉。
  处理时先区分正常未保存改动与缺类导致的残缺包；只保存需要保留的正常包，协调未保存内容后正常退出，
  对残缺关卡不保存覆盖 → `Tools/Build/Build-Editor.ps1` 常规构建 → 重新打开。
  不以强制结束进程代替处理保存提示；是否恢复以及是否需修复资产须按实际结果说明，不承诺自动恢复。

**实测补充（2026-09-18）**：`LiveCoding.CompileSync` 在 UE 5.8 **可以新增 UCLASS**（本次 `ABronzeTorch`
补丁成功后 `load_class('/Script/FPSGAME.BronzeTorch')` 立刻可用，日志有
`LogClass: Function AdvanceGameTime is new or belongs to a modified class.`）。它不改变上面这条规矩——
新类一旦要成为已保存关卡/资产的依赖，本项目仍先完成常规 Editor 目标构建。

## 用 UBT 响应文件做全套语法编译（2026-09-21）

上面"单文件编译校验"的 `-SingleFile=` 路子**改过头文件就失效**（无共享 PCH）。还有一个更强的做法：
**直接复用 UBT 自己留下的每个 TU 响应文件**，它在编辑器开着时也能跑，且对头文件改动同样有效。

```powershell
# 关键：cwd 必须是引擎 Engine/Source，共享 rsp 里的 /I 是相对它的路径
cmd /d /c "call ""<vcvars64.bat>"" >nul && cd /d ""E:\Program Files (x86)\UE_5.8\Engine\Source"" && cl /nologo /Zs @""D:\FPS3D\FPSGAME\Intermediate\Build\Win64\x64\UnrealEditor\Development\FPSGAME\X.cpp.obj.rsp"""
```

- `/Zs` 只做语法检查、不产生 obj，所以**不需要写权限、不受 DLL 被锁影响**，可以在编辑器运行时验证。
- 逐个 TU 跑完，等于一遍"能不能编过"的完整前哨；本次用它一次覆盖 19 个 TU，**零 error**。
- **它能抓到肉眼会漏的真错误**：本次抓到 `if(x)UE_LOG(...); else UE_LOG(...);` → `error C2181: 没有匹配 if 的非法 else`。
  **`UE_LOG`/`UE_LOGFMT` 等宏展开成含内层 `if` 的多语句**，所以 `if/else` 两侧都要加花括号，不能写成单语句形式。
- 它**不能**替代完整构建：不做链接期检查（模板实例化等）、不生成/更新 `UnrealEditor-FPSGAME.dll`。
  交付时只能说"语法编译通过"，不能说"已编译进二进制"。
- 若某 TU 没有现成 `.rsp`（例如从未参与过该目标构建的新文件），可按同目录同构文件复制一份、
  只替换文件名与产物名，作为等价命令使用。

### 配套的"归因"习惯

模块级构建失败时，先从最新 `Saved/BuildEditor/build-*.log` 抽出「错误总数 + 涉及文件」，
再判断**有没有错误落在自己负责的目录**下：一条都没有，就说明是别人的文件挡住了整个模块
（UBT 用 `git status` 决定工作集，**未跟踪的新 `.cpp` 也会入集**），不必怀疑自己的改动。
`Tools/Building/run-checkpoint-b.ps1` 已把这套归因写进脚本。

## 无头 commandlet 的两个静默失败（2026-09-21）

都是"看起来没输出、其实没跑起来"，排查时先怀疑这两条，别先怀疑脚本逻辑：

1. **工程文件必须给绝对路径**。`UnrealEditor-Cmd.exe FPSGAME.uproject ...` 里的相对路径由**新进程的
   工作目录**解析，而它不保证是工程目录，于是引擎在初始化阶段就退出：stdout 只有约 4 KB 启动日志、
   自定义 `-log` 文件 **0 字节**、退出码 1，日志里写着
   `LogInit: Project file not found: FPSGAME.uproject` / `Failed to open descriptor file`。
   改用 `-Project`/工程文件的**绝对路径**后同一命令立刻正常（本次 63520 字节输出、exit 0）。
2. **自定义 `-log` 可能一直是 0 字节**，真正的输出在 stdout 里（配合 `-stdout` 抓）。
   只看 `-log` 文件会误判成"脚本没执行"。

另外注意：`Tools/Building/audit_voxel_placement.py` 在本环境以
`-run=pythonscript -nullrhi -unattended` 运行时**能跑完但产不出它自己的 `AUDIT layer …` 行**
（命令自报 `Success - 0 error(s)`、耗时 0.47 s，日志停在脚本第 24 行
`EditorLevelLibrary.get_editor_world()` 弃用警告之后，无 traceback）。仓库里找不到它曾经成功运行过的
产物作对照，所以**未确证**是脚本自身限制还是环境限制；要它出报告得换交互式/编辑器内方式。
不要把"没有 AUDIT 行"直接当成回归。
