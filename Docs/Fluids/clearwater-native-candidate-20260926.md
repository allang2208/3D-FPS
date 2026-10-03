# Clearwater 原生光学候选（2026-09-26）

> 后续状态：用户已认可本候选，并授权推广。河流、喷泉池面和地牢积水已完成原生光学材质保存及基础 DLL 构建，详见 [全水体推广交付](native-all-water-20260926.md)。下文的“候选关卡限定”描述本候选最初交付范围。

用户同意采用评估建议：现有河道、地形、加载和全水体交互继续作为主线；Clearwater 的浅水表现留在专用候选关卡，补齐接入后再由用户决定推广。本次不替换丘陵河流、罗马喷泉和地牢积水，不新增实时 FFT 或全图流体模拟。

## 实现

- 水面改用 UE `SingleLayerWater`。真实场景深度、吸收、散射、折射、反射、光照与阴影由引擎水渲染路径处理；移除候选运行材质对手算天空、固定 160 cm 光学水深和 Unlit SceneColor 采样的依赖。Clearwater 的每米吸收/散射系数转换为 UE 要求的每厘米单位。
- 继续使用已有 48 分量近似波谱，波数、初相位、角频率和振幅烘成材质常量；统一为 UE XY 水平面、Z 向上。波高用厘米，法线使用无量纲解析斜率。短于网格可表现尺度的波形只进入法线，避免高频顶点位移混叠。保留 `WaveHeightScale` 控件。
- 命中直接复用 `SourceAssets/RiverPilot20260923/RippleField.hlsl`：8 个全局击水槽、4 个尾流槽，显式 RGBA 连接。时间为命中绝对游戏时间，年龄由材质的当前时间相减得到。C++ 复用注册表已经绑定的 MID，删除候选自己的 4 槽更新器，避免重建 MID 使击水写入失去接收者。
- 32 张已有焦散帧制作成 4096×2048 图集，格内保留周期边界，材质插值相邻两帧。一个 RGB 压缩图集，显式 LOD0、不生成串帧 mip；常规 BC1 约 4 MiB。不增加运行时 RT。远距淡出焦散细节。
- 焦散落在普通受光海床上，不发光；按实际床面至水面的垂直距离投影，随缓存的场景方向光方向和强度更新（4 Hz），夜间减弱。序列本身仍是固定太阳和平均水深烘焙的近似，不宣称实时光线聚焦或与每次击水物理耦合。
- 水下后处理按视线在水下的实际长度衰减，向上出水的视线只计算到水线；限制在水面水平边界内，12 cm 过渡带，30 Hz 平滑混合。默认 `UnderwaterAmount=0` 为中性材质，运行 MID 设为 1 后由组件权重驱动。
- 自动生成仅允许 `L_ClearwaterWater`，兼容 PIE 前缀；显式放置的同类水 Actor 仍支持。资源在项目中存在不会再导致共享 GameMode 在其它地图生成水面。
- 当前范围是单玩家表现，未加入游泳、浮力、多人同步或水动力学。

## 资产与生产入口

新主材质：`/Game/Clearwater/M_ClearwaterWater_Native`、`M_ClearwaterSeabed_Native`、`M_ClearwaterUnderwater_Native`。三个原 `MI_Clearwater*` 路径保持稳定，改指新主材质；旧主材质仍保留。每轮安装前将原三个 MI 复制到 `/Game/Clearwater/History/BeforeNative_<时间>/`，保护原参数与父链。

旧关卡的海床直接绑定旧 master，本轮仅将 `ClearwaterSeabed` 标签的床面改绑稳定的 `MI_ClearwaterSeabed`，水面网格槽绑定 `MI_ClearwaterWater`。同时修正生成器把方向光朝向太阳而非沿光线方向照射的错误：仅对仍保持旧 `(pitch=31,yaw=6)` 的 `ClearwaterSun` 改为 `(-31,186)`，已调整过的太阳保持不动。无需重建关卡或重导网格；保存前在源目录 `BeforeNative_<时间>/Content` 保留目标包。原始全量作者入口默认改为调用原生候选制作器，不再重造旧 Unlit 水面。

1. 外部生产：`Tools/Fluids/build_clearwater_native_data.py`，输出到 `SourceAssets/ClearwaterNative20260926/`，包括图集、HLSL 和 `production.json`。
2. 常规构建：`Tools/Build/Build-Editor.ps1`。类成员布局已变化，先更新基础 DLL，再制作依赖资产，不用 Live Coding 交付。
3. 材质生产：`Tools/Fluids/author_clearwater_native.py`，进行必要材质编译、保存及 MI 父链接入。首次创建使用 Python commandlet，带 `-AllowCommandletRendering` 启用材质着色器编译；没有启动游戏或调用画面渲染。编辑器已经开着时走 `Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript`。PIE 或目标资产未保存时停止，保留现场。
4. 已保存材质的续接入口：同一 commandlet 加 `-ClearwaterBindingsOnly`，重新编译并保存已有三套主材质，加载候选地图完成海床、网格及光照绑定，不删除材质节点。单独加载 UWorld 包不会初始化 Actor 遍历，因此后台使用 `EditorLoadingAndSavingUtils.load_map`。UE 5.8 对 commandlet 启动时已驻留的材质表达式执行 `DeleteAllMaterialExpressions` 会触发 `IsRooted` 断言；制作器现在在写入前阻止这种重复重建，现有图的后续编辑使用已有编辑器批次。

原生源码：`Water/ClearwaterWater.*`；共享系统只新增取注册 MID 和提交显式水面命中的接口（`RiverPilotFXSubsystem.*`），原有弹道、伤害、采样和水花预算保持原实现。新增材质和源数据限定在 Clearwater 目录。

## 交付状态

- 波谱代码、焦散图集、作者入口与运行源码已制作；既有水体主线保持原实现，Clearwater 作为候选关卡交付。
- **基础 DLL 已构建并落盘**：用户关闭编辑器及独立游戏后，`Tools/Build/Build-Editor.ps1` 完成 255 项操作，`Result: Succeeded`，约 145 秒。日志：`Saved/BuildEditor/build-20260926-190331.log`。
- **新材质和绑定已保存**：图集、三套 Native 主材质、三个稳定 MI 和水面网格，见 `SourceAssets/ClearwaterNative20260926/assets-saved-20260926_190638.json`。首次保存后的旧资产备份在同目录 `BeforeNative_20260926_190638/Content` 及 `/Game/Clearwater/History/BeforeNative_20260926_190638/`。
- **候选关卡已保存**：续接阶段完成 1 个海床材质绑定和 1 个太阳方向修正，保存 `L_ClearwaterWater`。三套 Native 主材质最终编译均返回空错误列表；commandlet 正常退出（退出码 0）。保存回执：`SourceAssets/ClearwaterNative20260926/bindings-saved-20260926_191028.json`；日志：`Saved/ClearwaterNative20260926/author-native-commandlet-03.log`。
- 首轮后台创建成功；第二轮在尝试重复清空已保存图时触发上述引擎断言，未改写这三套主材质。第三轮从保存的材质续接完成，不再重复删除节点。旧 master 因恢复备份被加载时的历史着色器错误，不代表最终 Native 主材质编译失败。
- **未启动交互式编辑器、游戏、截图、运行测试或性能测量**。材质编译、资产保存和原生构建属于制作；视觉效果及运行表现由用户测试，尚未宣称验收或优于现有主线水体。

上游来源：[Clearwater](https://github.com/Aureliengmz/clearwater)，MIT；许可文本见 `ThirdPartyNotices/Clearwater.md`。UE 光学路线依据 [Single Layer Water](https://dev.epicgames.com/documentation/unreal-engine/single-layer-water-shading-model-in-unreal-engine) 和本机 5.8.2 的 `MaterialExpressionSingleLayerWaterMaterialOutput.h`（系数单位 1/cm）。
