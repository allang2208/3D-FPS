# 免费流体基础：第一阶段

本阶段为 FPSGAME 建立可复用的原生流体资产与制作入口。项目启用 Niagara、Niagara Fluids、Water、Geometry Cache 和编辑器 Alembic Importer；SVT 属于引擎原生能力，不添加不存在的“SVT 插件”。已配置 Heterogeneous Volumes 与 Epic WaterBodyCollision 查询碰撞配置。

工程现有河道由 TemperateHillsStreaming 的 DynamicMesh 生成，没有 Landscape。本阶段提供不修改 Landscape 的 Water Custom 蓝图。现有河道、喷泉、枪口烟与技能火焰的引用没有替换；逐项替换和玩法接入属于后续升级工作，不能把本阶段素材库称为全场景水火升级完成。

## 已制作内容

内容浏览器目录：`/Game/Fluids/Foundation`。

| 资产 | 用途 |
| --- | --- |
| `Niagara/NS_Smoke2D`、`NS_Fire2D` | Epic 2D 流体模板的项目副本 |
| `Niagara/NS_Smoke3D_Local`、`NS_Fire3D_Local` | Epic 局部 3D 流体模板的项目副本 |
| `Actors/BP_Smoke2D`、`BP_Fire2D`、`BP_Smoke3D_Local`、`BP_Fire3D_Local` | 已绑定上述系统的可放置 Niagara 蓝图 |
| `Volumes/fluid_data` | 原创 Mantaflow 烟火的 Animated Sparse Volume Texture；72 帧、24 FPS、3 秒 |
| `Materials/M_SVT_Smoke`、`M_SVT_Fire` | Substrate 体积材质：密度消光、烟雾颜色、温度黑体发光 |
| `Actors/BP_SVT_Smoke`、`BP_SVT_Fire` | 已绑定缓存与材质；默认播放一次，不宣称无缝循环 |
| `Geometry/GC_Mantaflow_LiquidDrop` | 原创液滴落下后的表面网格动画；48 帧、24 FPS |
| `Materials/M_LiquidCache`、`Actors/BP_LiquidDrop_Cached` | 液体缓存基础材质与播放蓝图；不参与实时液体求解 |
| `Materials/MI_Water_CustomMesh`、`MI_Water_River`、`MI_Water_Lake` | Epic Water 材质的项目副本 |
| `Actors/BP_Water_CustomSurface` | WaterBodyCustom 入口；禁止地形雕刻，绑定官方自定义网格材质 |

上表资产必须结合 `SourceAssets/FluidFoundation20260923/delivery.json` 的实际交付清单使用。制作日志、缓存和交付清单不等于运行或画面验收记录。

## 使用入口

新启用插件在下一次正常打开 FPSGAME 时加载。本任务不关闭、重启现有编辑器。插件尚未加载时不要在当前会话打开新 Water 或 Niagara Fluids 资产。

正常重开项目后，在内容浏览器 `/Game/Fluids/Foundation/Actors` 选择对应蓝图放入关卡，或由已有玩法在需要的位置 Spawn Actor。3D 模拟先用于少量近景重点效果；大量重复烟火优先常规 Niagara、2D 或之后烘焙的序列图。此处没有给整个项目额外加全局高质量 CVar。

Water Custom 只提供官方自定义水面 Actor 入口，并不自动把现有 DynamicMesh 河道变成 WaterBody。迁移河道时仍需对接水位、流向、河岸、碰撞/浮力与地形破坏后的更新；不能只替换材质就宣称完成。

SVT 蓝图将 Blender 米制坐标缩放为 UE 厘米。VDB 导入通道来自本次实际缓存布局：Attributes A = density / flame / shadow / temperature；Attributes B.xyz = velocity。改变 Blender 输出网格后应同步修改导入/材质映射。烟火仅是 64 分辨率的可编辑基础素材，不是电影品质终版。

## 可编辑源与重建

- `SourceAssets/FluidFoundation20260923/Fire/Mantaflow_fire.blend`：烟火制作源、OpenVDB 缓存与 bake-manifest。
- `SourceAssets/FluidFoundation20260923/Liquid/Mantaflow_liquid.blend`：液滴制作源、液体缓存、`LiquidDrop.abc` 与 bake-manifest。
- `Tools/Fluids/bake_mantaflow_foundation.py`：后台建立并实际烘焙源文件，可指定 fire/liquid、分辨率与帧数。
- `Tools/Fluids/author_foundation_ue.py`：在专属 UEAuthoring 工程导入缓存、制作材质/蓝图并保存；不会打开关卡或运行游戏。
- `Tools/Fluids/publish_foundation.py`：只投递本任务清单里的新资产；遇到不同的现有包停止，不覆盖已加载资产。

例如后台重制烟火到**新输出目录**：

```powershell
& 'E:\Program Files\Blender Foundation\Blender 5.1\blender.exe' --background --threads 4 --python 'D:\FPS3D\FPSGAME\Tools\Fluids\bake_mantaflow_foundation.py' -- --kind fire --output 'D:\FPS3D\FPSGAME\SourceAssets\FluidFoundation20260923\FireRevision2' --resolution 96 --frames 96
```

`author_foundation_ue.py` 当前读取第一版 Fire/Liquid 路径；制作新版本时显式更新源路径和目标资产目录。保存着旧版资产的现有编辑器中不能用另一个 commandlet 强行覆盖同名资产。后续原位修改应通过现有 MCP 桥的批次互斥完成。

## 来源与付费边界

- Niagara 与 Water 的母版来自本机 Epic UE 5.8 安装，按 Unreal Engine 授权使用；未公开再分发这些原始资源。
- Blender 烟火、液滴的几何、模拟设置和生成脚本为本任务原创，没有引入第三方付费缓存。
- 采购费用为零。ZibraVDB 是可选的后续压缩后端，本阶段使用原生 SVT；未安装 ZibraVDB、GDS 或 FluidNinja，也没有代替用户领取授权、提交营收声明或购买订阅。
- 原始 `.vdb` 序列保留，未来取得 ZibraVDB 授权后可用于它的压缩管线，无需重做 Mantaflow 模拟。

## 交付范围

完成状态以素材导出、UE 导入/保存与 delivery.json 为准。不包含现有场景效果替换，不包含后续游戏帧率结论。未运行 PIE、游戏、截图、渲染、测试或验收，交由用户自行测试。
