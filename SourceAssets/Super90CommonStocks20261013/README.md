# SUPER90 通用后托与连接杆

2026-10-13：在当前 SUPER90 原装结构上接入五款既有通用后托。沿用公共配件 ID、属性、金属框图标和 Parts 存档，不新增独立连接杆槽位。

## 制作与运行入口

- `read_inputs.py`：从当前 UE 资产导出母件、供体与材质参数；`inputs.json` 保存来源和提取时散列。
- `measure_inputs.py` / `measurements.json`：制作所需的制造岛、接口和坐标测量。
- `author_models.py`：制作五套连接杆组合。`*_Editable.blend` 保留后托、原装前接颈、连接杆、锁紧环与入口过渡为独立对象；`Meshes/` 为合并导出。
- `FactoryStock.blend` / `NativeStockNeck.blend`：从当前模型提取的原厂后托及保留前接颈。
- `author_factory_icon.py`：制作原厂恢复选项的真实模型图标；五个通用选项引用既有共享图标。
- `install.py`：导入并保存专用材质、五套网格、原厂隐藏分组和图标。逐项写 `install_receipt.json`，失败时保留已完成项。
- `integrate_catalog.py`：只更新 gunsmith.json 的 `ue_super90.options.stock`，公共参数取自当前 M4 目录。
- `check_assets.py` / `check_models.py`：用户要求收尾时执行的资产读回与原模型保持检查；不会启动游戏。
- 运行组件：`Source/FPSGAME/Weapons/Super90StockAssets.*`，由既有 `SetGunsmithStock` 调用；图标预加载及第三人称装备捕获同步识别。

## 安装契约

坐标为当前 SUPER90 骨骼网格的组件绑定空间。Blender 用米，FBX/UE 用厘米，运行时挂在 `WPN_root` 并使用完整参考绑定变换的逆。不可套用其他步枪的安装偏移或仅写死 0.01 缩放。

原厂后托 4038 个三角形分到三个 `S90_FactoryStock_*` 材质组，保留各自原材质。原生产骨骼网格只修改材质分组；不制作新的手臂、骨架、权重或动画。原厂后握把的独立分组继续保留。

通用组合保留原装前接颈至组件空间 Y=-22.5 cm（Blender），然后由真实边界轮廓过渡到直径 23.2 mm 的封闭杆。杆轴向后下倾 6°；各通用后托保留原尺寸，实际入口有独立封闭过渡。骨架、轻型、高性能后托维持原肩托后端平面；两款较长战术后托允许向后延伸，避免压缩本体或把入口埋入握把。

连接杆随整个后托切换和拆卸；加载失败保留原厂外观。`false` 恢复原厂后托，不留下转接件。世界装备捕获同时复制替换件与原厂隐藏组，既有目录、应用、取消、保存、掉落及动态预览沿用统一装配入口。

## 材质与依赖

主体金属和连接杆使用 SUPER90 的 WS1 深色金属参数；聚合物、橡胶维持非金属身份。保留通用模型 UV 和适用的源结构法线/粗糙度；新连接面用独立 UV 和材质，不采样枪身图集。保留可调式后托原有香槟色饰条和红色嵌片。原装前接颈沿用当前 SUPER90 聚合物参数及原 UV 纹理。WS1 材质沿用已有湿润层。

供体均为本工程既有资产，来源见 `inputs.json`；本轮不新增第三方下载或授权。原版 Cransh/Benelli 来源继续由 `SourceAssets/BenelliM4Super9020261006/` 管理。

## 交付边界

`install_receipt.json` 已记录五套后托组合及共 26 个资产保存完成，原厂后托 4038 个三角形的独立显示分组已写入当前生产网格。图标只制作新增原厂恢复选项，公共五款继续使用共享图。

早期正式构建曾被库存模块及过期反射头阻塞，历史记录为 `build-resume-console.txt`。本轮重新生成 UHT 后，`FPSGAMEEditor Win64 Development` 构建成功；日志为 `Saved/Super90StockCloseout20261013/Editor-UHT.log`，收尾以 [收尾发布说明](../../Docs/Weapons/super90-common-stocks-closeout-20261013.md) 为准。

收尾修复了旧位置阈值多选的 120 个扳机护圈邻近三角形：后托聚合物改按独立连通网格选取，这些面保留在原枪并从替换件删除。

收尾发现保存后的自定义元数据标签为空；`install.py` 已改为按三个真实 `S90_FactoryStock_*` 材质组判断是否完成拆分。重复导入可以更新静态后托，但不再次拆分生产骨骼网格。`read_inputs.py` 拒绝覆盖已经安装后的拆分前母件，后续重建复用保留的 `Inputs/` 和 `inputs.json`；不要先重新导出覆盖基线。

用户授权的离线检查确认：原生产网格 39960 个顶点位置、63172 个三角形索引完全一致；权重、全部 UV 和骨骼绑定帧一致。最终 FBX 读回法线在小数点后五位的比较精度内一致；初次分组的 0.028° 读回差已不再出现在修正后的结果中。五套新连接杆、锁紧环、入口过渡均闭合，无零面积面；前接颈只保留原机匣接触口，后端无开放边。五套 UE 资源、材质引用、目录选项和公共图标均已读回。

后台导入需要 `-AllowCommandletRendering -RenderOffscreen`；`-NullRHI` 下骨骼 FBX 导出会触发 SkinnedMeshComponent 的 MeshObject 断言。结构化交付状态见 `delivery.json`。

本轮未启动交互编辑器、PIE 或游戏。五套连接结构做了离线灰模侧向检查，UE 实际材质和游戏视角未验收。原厂与替换件的装配、恢复、异步图标资源、第三人称隐藏组和已有 Parts 保存入口已做源码检查；游戏里的 ADS、换弹观感和双端联机实测仍由用户确认。
