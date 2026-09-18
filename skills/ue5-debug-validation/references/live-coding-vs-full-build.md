# Live Coding 热补丁与全量编译的边界（FPSGAME 2026-09-16 实践）

结论先行：**函数体改动**可以用 `LiveCoding.CompileSync` 立刻在运行中的编辑器会话里验证；**任何改布局的东西**（UCLASS/USTRUCT 成员、新增 UFUNCTION、带资产属性的默认值）必须关掉编辑器做全量编译。热补丁只活在当前会话，磁盘上的 DLL 不会变。

## 可以热补丁

- `.cpp` 里的函数体、常量、平衡数值。
- 纯 C++ 结构体（非 `USTRUCT`）新增成员，且该结构只被本模块以指针或 `TUniquePtr` 持有：新代码按新的 `sizeof` 分配。**前提是没有旧实例存活**——热补丁时已在运行的旧实例还是旧尺寸的内存，新代码写新成员就是越界写。改这类结构前先确认活动会话（PIE 正在跑就先停）。

## 不能热补丁

- **带资产的 USTRUCT**（例如调色板数据资产里的 `FVoxelPhysicalMaterial`）改字段布局或默认值：热补丁后新 struct tag 与已保存资产不匹配，字段会整体读成 `None`，之后任何"读出来再写回去"的脚本都会把空值写进资产。必须：关编辑器 → 全量编译 → 再改资产。
- **依赖文件级 `static` 的跨补丁状态**：模块重载会把它复位，表现是"只有打过补丁的那个会话行为不对"。修法是要么改成 `UPROPERTY` 成员，要么在使用点从安全宿主（`UPROPERTY` 持有的 Actor / 组件）按名字重新解析。

## 验证边界与证据

- 热补丁成功与否只看日志 `LogLiveCoding: Display: Live coding succeeded|failed`，不看命令是否返回。
- 编辑器退出后热补丁消失：源码与磁盘 DLL 不一致。当次要么全量编译，要么明确告知"改动只在会话内"。
- 改 `.uasset` 必须在**运行中的编辑器进程内**做（Python 远程执行）。远程执行上下文里 `EditorAssetLibrary.save_*` 返回 `False`，可用 `EditorLoadingAndSavingUtils.save_packages([load_package(path)], False)`。
- 证据顺序：同进程读回不算证据。用**磁盘时间戳 + 字节扫描 + 独立进程读回**复核。
- 日志在 `Saved/Logs/FPSGAME.log`：排查先看限流过的诊断行（如 `VOXEL_AIM` / `VOXEL_REJECT` / `VOXEL_FRESH`）与 `Live coding` 行；全量编译的落地产物看 `Binaries/Win64/UnrealEditor-FPSGAME.dll` 的时间戳。

## 常用命令

```powershell
# 触发一次热补丁（编辑器必须在运行）
python Tools/AssetPipeline/ue_python_exec.py --statement "import unreal; unreal.SystemLibrary.execute_console_command(None, 'LiveCoding.CompileSync'); print('requested')"

# 全量编译（必须先关闭编辑器；Live Coding 会占住模块导致构建被拒）
& 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat' FPSGAMEEditor Win64 Development -Project="D:\FPS3D\FPSGAME\FPSGAME.uproject" -WaitMutex
```

## 症状 → 先查什么

| 症状 | 先查 |
| --- | --- |
| 同一个 bug 只在这个会话出现 | 文件级 `static` 是否被模块重载复位 |
| 资产字段全读成 `None` | 是否热补丁改过带资产的 USTRUCT；关编辑器全量编译后按清单修复 |
| "改了代码没反应" | 补丁是否真的 succeeded；是否改的是只在退出后才生效的东西（磁盘 DLL） |
| 编辑器关掉后行为回退 | 说明改动只是热补丁，从未落到磁盘 DLL |

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

## 热补丁类不能成为关卡/资产的依赖（2026-09-18 事故，青铜火把）

**症状**：摆好的一批 actor 在编辑器重启后"整批消失"，加载日志逐条报
`LoadErrors: Warning: 创建导出：资产"<ComponentName>"的外部容器加载失败：<Class> ... :PersistentLevel.<Actor>_1`。

**根因**：这些 actor 的类当时只存在于 Live Coding 补丁里（补丁成功、摆件、保存关卡都正常），但磁盘上的
`UnrealEditor-FPSGAME.dll` 仍是旧构建、不含这个类。编辑器一重启，类没了 → actor 建不出来（内存里 0 件）。
这正是本文开头那条"热补丁只活在当前会话"的后果。

**规矩**：

- 新增 C++ 类并且要**写进关卡/资产数据**时：先全量编译把类落到 DLL，再摆件；Live Coding 只用来验证函数体改动。
- 反过来：关卡里已经引用了补丁类时，**关编辑器之前先编译**，否则下次启动就是上面那条报错。
- 关卡出现"缺类"时**不要保存这张图**：内存里是残状态（actor 数量为 0 或半残），一保存就把磁盘上的 actor 抹掉。
  正确顺序：确认磁盘文件没被重存（时间戳 + 二进制里还能搜到 actor 标签）→ 先保住别人未保存的脏包
  （`EditorLoadingAndSavingUtils.save_packages`）→ **强制结束编辑器**（别走"正常退出"，它会弹"保存关卡"）
  → `Tools/Build/Build-Editor.ps1` 全量编译 → 重开编辑器，actor 会带着组件与属性自己回来。

**实测补充（2026-09-18）**：`LiveCoding.CompileSync` 在 UE 5.8 **可以新增 UCLASS**（本次 `ABronzeTorch`
补丁成功后 `load_class('/Script/FPSGAME.BronzeTorch')` 立刻可用，日志有
`LogClass: Function AdvanceGameTime is new or belongs to a modified class.`）。它不改变上面这条规矩——
补丁只活在会话里，一旦要落盘到关卡数据仍必须全量编译。
