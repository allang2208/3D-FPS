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
