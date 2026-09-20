# 旷野地面模糊与进入加载检查（2026-09-20）

用户反馈：进入旷野后地面模糊，之前的层次效果消失；要求检查并把地面加载完成作为进入条件。

## 已确认的情况

1. 新版资产存在且引用正确。当前编辑器读取 `M_TemperateGround` 为 91 个表达式、`M_PebbleShoreGround` 为 130 个表达式；交点细化、随机干壳和分支采样参数仍在。`DA_TemperateHillsStreaming.GroundMaterial` 指向新版 `M_PebbleShoreGround`。两份资产最后保存于 00:09:57 / 00:10:01，并未被旧脚本覆盖。
2. `TemperateHillsStreaming.cpp` 用这个引用创建 `GroundMID`，动态地形块绑定该 MID。资产配置和代码接入链路未丢失；本轮还没拿到稳定运行中的丘陵材质实例快照。
3. 旧 `TickPreparation()` 在地形、PCG 和 PSO 准备后，仅用 `GetNumWantingResources()` 等待全局纹理请求，10 秒后无条件越过纹理等待。它既不主动请求地表高清 mip，也不判断地表 mip 是否驻留。零个全局请求同样不能证明地面已经清晰，因为纹理系统可能认为当前低清级别已满足需求。
4. 地形采用 `UDynamicMeshComponent`，材质使用 Custom 世界坐标采样。引擎 `UPrimitiveComponent::GetStreamingRenderAssetInfo()` 的通用回退按组件包围盒估算纹理密度，没有这套地表每层 2.1–7.5 m 的显式投影信息。现有地表流程未补充独立驻留请求。
5. 当前纹理池配置是 1000 MB，`r.Streaming.MipBias=0`、`r.TextureStreaming=1`。没有据此认定显存不足，也没有修改全局纹理池。

结论：升级资产没有丢失，加载保障存在确定缺口。低清 mip 是需要优先处理的候选原因；尚未完成“旷野中清晰度恢复”的实机确认，不能把这个候选原因写成已经排除全部其它因素的结论。

## 第一版修改（材质等待条件已被下文修正）

仅修改 `Source/FPSGAME/WorldGeneration/TemperateHillsStreaming.cpp`，保留此前河岸、天空、地貌破坏等未提交修改。

- 第一版要求实际地表材质的 shader map 完整；这项条件过严，导致用户后续报告的长时间等待，现已替换。
- 从实际 `GroundMID` 收集使用的 2D 纹理，而不是硬编码另一份纹理目录。
- 对该组共享地表纹理请求 5 秒驻留，每秒续期；进入旷野后继续续期，退出后自然过期，不改纹理资产的永久 `NeverStream` 标记。
- 在结束加载前逐张检查渲染资源已初始化、没有待处理流送、实际驻留 mip 达到当前平台与内容允许的非可选级别。
- 未完成时显示“正在载入清晰地面纹理 X/Y…”，保持加载遮罩与原有输入/移动锁。原来的 10 秒等待只保留给其它环境纹理，不能越过地表条件。
- `HILLS_GROUND resident` 记录每张贴图的驻留层数、目标层数与分辨率；`HILLS_READY` 新增 `ground_textures=X/Y`，可对照进入时序。

不新增类或修改资产 USTRUCT，不改地形碰撞及玩家存档，不重建两份已经正确接入的地表材质。

## 第一版构建记录

- 编辑器读取记录：`Saved/GroundLoadingFix20260920/inspect-bridge-02.txt`、`inspect-live-01.txt`。
- 曾进入现有丘陵存档，旧流程记录 `HILLS_READY`，耗时约 22.44 秒；随后试玩结束，未取得完成时的地表 mip 快照。此前 `ListStreamingTextures` 的 64×64 数据采自 DayNight 主世界，不能当作旷野模糊的运行时证据。首次加载资产时读出的 32×32 尺寸也不能代替稳定后的驻留检查。
- 后续编辑器退出，实时桥无法连接。未跨任务发协调消息。
- 必要 Editor 构建：`Saved/BuildEditor/build-20260920-131746.log`。本次 `TemperateHillsStreaming.cpp` 编译成功并生成新对象文件。
- 完整构建失败于已有的 `Source/FPSGAME/Combat/MonsterToughnessTypes.h:57`：`extern FPSGAME_API thread_local EMonsterAttackForm ActiveForm;`，MSVC C2492（具有线程存储持续时间的数据不能具有 DLL 接口）。本任务未修改该文件。

该构建阻塞是第一版当时的状态；随后项目已完成其它构建，用户实际运行到了新增材质等待条件。不能继续把第一版写为“未应用”。

## 用户反馈约 180 秒等待后的修正

### 证据与原因

- 本次用户日志 `Saved/Logs/FPSGAME.log`：05:57:47 UTC 记录 `HILLS_SURFACE_READY startup_cells=9 ms=2531.16`，到 06:00:39 日志关闭仍无 `HILLS_GROUND requested`、资源阶段完成或 `HILLS_READY`。出生点的 9 块地形已用约 2.53 秒完成，卡住的位置在原高清贴图收集之前。
- 对应 UI 停在“正在准备地面材质…”，原判断要求 `IsGameThreadShaderMapComplete()` 为真。UE 5.8 的 `FMaterial::SetGameThreadShaderMap()` 用 `IsComplete(this,true)` 设置该标记；按需编译允许已可渲染的 shader map 仍缺少未使用的变体，队列为空也不保证该标记为真。
- `UMaterialInstance::GetMaterialResource()` 会回退到父材质，不是 MID 没有父材质资源导致的必然空指针。
- 旧进入条件还等待完整 `ViewRadiusMeters`，默认约 384 m，并要求整个地形任务列表为空；并非生成整个 1 km 世界的高精度地面，但确实把进入前准备扩大到了远景视野。

### 当前实现

- 材质判断改为实际地表资源 `IsCompilationFinished()`（编辑器编译任务）和 shader map 的 `IsValidForRendering()`；不主动提交所有未用变体。附近网格已在加载遮罩下显示，由实际渲染请求需要的 pass。
- 地表贴图收集移到材质等待之前，能与附近地形、植被准备交叠；仍检查这组共享贴图的高清 mip。没有改成等待整幅世界逐块渲染，也没有放行低清地面。
- 若没有编译任务且渲染材质仍不可用，30 秒后显示可返回主场景的失败状态并记录资源/map 情况，不以超时强行进入。
- 初始 3×3 地块完成后，进入前只继续请求与角色周围 **96 m** 相交的地形网格；只有当地形、异步碰撞和附近树干碰撞完成才放行。入口检查和生成使用相同角色位置，避免摄像机偏移造成边界地块永远不被请求。
- PCG 进入条件限制为 `min(该层原半径,96 m)`；后台调度保留各层原半径。远处植被生成不再直接阻挡进入。
- 进入后地形恢复原详细/视野半径，继续最多两个工作线程任务、每帧一个网格提交和一个树干碰撞单元。低精度远景丘陵背景仍按原流程准备。
- `HILLS_GROUND renderable` 记录可渲染时的完整变体标记；`HILLS_READY` 记录入口半径、附近地形、PCG 和纹理数量，便于用户下次运行定位实际耗时。

范围限制：没有改全局纹理池、PCG 运行调度预算、全局资产/着色器队列处理和 PSO 预热；没有测量 GPU 帧耗时，不能承诺总加载时长。当前针对的是确定存在的错误等待条件及过大的初始地形等待范围。

### 构建与交付

必要 Editor 构建成功，`TemperateHillsStreaming.cpp` 编译及 `UnrealEditor-FPSGAME.dll` 链接均完成。日志：`Saved/BuildEditor/build-20260920-140931.log`，构建总耗时 20.86 秒（这是编译耗时，不是游戏加载耗时）。本次不主动启动 PIE 或追加运行验收，进入时间、清晰度与行走流送由用户实测。
