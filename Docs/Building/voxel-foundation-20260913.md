# 20 cm 木材／石头体素建造初版

用户指定最小单元为 20 × 20 cm，本次按立方体解释为 20 × 20 × 20 cm。`wood`、`stone` 是材料类型；墙、地板是同一材料的使用方式。当前阶段为单机自由建造原型，材料不限量，不改现有背包或伪装为已经完成 Crafting。

## 架构与职责

沿用 FPSGAME 运行模块，依赖现有 GeometryCore／GeometryFramework、UMG／Slate。结构为 PlayerController → VoxelBuildComponent → VoxelBuildWorld → 体素分块；显示控件只读取建造组件。材料资源由 VoxelBuildPalette 提供，不依赖 EBS 的角色、GameMode 或背包。

| 所有者 | 责任／接口 |
| --- | --- |
| `UVoxelBuildPalette` | 稳定材料 ID、名称、PBR 材质、20 cm 示例网格与放置预览材质 |
| `AVoxelBuildWorld` | 20 cm 整数坐标、16³ 单元分块、外露面贪心合并、碰撞、编辑、撤销、保存 |
| `UVoxelBuildComponent` | 本地玩家生命周期、射线选格、刷子、输入拦截、状态提示 |
| `UVoxelBuildWidget` | 当前材料、刷子尺寸、放置状态、自由建造标识与按键说明 |

公开的 Blueprint 接口以材料选择、建造模式、世界编辑和保存为边界，内部网格数据不暴露给 UI。构造函数只建立轻量组件，地图准备完成后加载世界存档；离图时清理预览及控件。首版仅允许 Standalone，不声明多人复制支持。

## 行为范围

- 单格、1 m 地板、1 m 墙面刷子；墙面可 90° 旋转。每次确认作为一个编辑记录，支持撤销。
- 放置预览与实际提交共用选格和合法性逻辑，拒绝重复占格及与角色重叠；新结构须连接现有体素或接触场景支撑面。
- 删除只处理本系统创建的体素，不挖原场景地形。首版不做悬空结构坍塌、圆角自动塑形、家具、Crafting 配方或生产队列。
- 用世界坐标连续铺设 PBR 纹理；邻接块不保留内部面，跨分块边界编辑会刷新相邻分块。建筑碰撞响应 Visibility，供天气遮雨与枪械射线使用。
- 建筑保存独立于玩家背包：玩家档案 + 地图身份；丘陵再加入 WorldId。采用版本化、明确 20 cm 格距的独立存档，不改丘陵种子档。编辑先保存后公布，保存失败撤销本次修改。

## EBS 与美术来源

[Easy Building System V10](https://www.fab.com/listings/b2c5a428-e9af-4c6a-9daf-d10b8b04bddf) 下载目录为 `D:/FPS3D/EasyBuildingSystemV10`，模板声明 UE 5.3。已将其 `Content/EasyBuildingSystem` 导入本工程同名内容目录，未安装模板角色、GameMode 或 Config。它的 BuildingComponent、BuildingObjectSettings、SocketTransforms、Requirements、BuildingLists 面向整件吸附建筑。本次作为模块化建筑参考库，体素数据和保存由本项目维护；不声称已经把 EBS 的整套复制、支撑、所有权机制迁移到体素，也未进行 EBS 在 UE 5.8 的运行兼容测试。

木材、石头使用工程已存在的 Normandy 表面贴图，生成本项目独立材质和 20 cm 示例资产；源贴图不改动，Fab 原始与生成的派生二进制保留本机，不公开再分发。作者脚本记录实际引用。

参考方向：[Enshrouded 官方建造介绍与开发者答疑](https://enshrouded.com/en-US/news/enshrouded-world-design-team-reddit-ama-recap)。本次建立体素基础，不宣称复刻其完整表面塑形算法。

## 使用方法

重启已打开的 UE 编辑器以加载新原生模块，在当前四个游戏世界中进入已有玩家档案：日夜场景、Normandy、战壕、温带丘陵。丘陵需要等待世界生成完成。

| 操作 | 按键 |
| --- | --- |
| 进入／退出建造 | V；Esc 也可退出 |
| 木材／石头 | 1／2 |
| 单格／1 m 地板／1 m 墙面 | 鼠标滚轮 |
| 旋转墙面 | R |
| 放置／拆除 | 鼠标左键／右键 |
| 取样已建材料 | 鼠标中键 |
| 撤销上一次编辑 | Ctrl + Z |

单格尺寸为 20×20×20 cm；地板为 100×100×20 cm；墙面为 100×20×100 cm。绿色预览表示可以放置，红色表示受阻；右侧提示显示原因。编辑后自动保存，最多保留本次会话最近 32 次撤销记录。打开背包等已有菜单会退出建造。

## 资源与重建

已生成的资源位于 `Content/Building/Voxels`：

- `SM_Voxel20_Wood`、`SM_Voxel20_Stone`：20 cm 示例静态网格及简单碰撞。
- `M_Voxel_Wood`、`M_Voxel_Stone`：木纹／石面贴图、法线、粗糙度；世界坐标连续投射，接入 `MPC_FPS_Weather.WeatherWetness`。
- `M_Voxel_Preview`：20 cm 网格线与有效／受阻颜色的半透明放置预览。
- `DA_VoxelBuildPalette`：稳定 ID 为 `wood`、`stone` 的材料定义，运行组件默认引用它。

`Tools/Building/import_ebs.ps1` 可从下载目录导入参考库；目标已存在时保留现有内容。编译 Editor 目标后，用 `Tools/Building/create_voxel_assets.py` 在 UE Python 中生成本项目体素资产；需要已有 Normandy 贴图与天气参数集合。作者脚本只保存本次资产，不保存地图或其他脏包。资源制作记录留在 `Saved/VoxelFoundation20260913/authoring.json`；EBS 数据表来源摘录在同目录 `ebs-definitions.json`。

## 交付状态

Editor 目标编译完成。资源作者脚本已执行成功并保存木材、石头、预览和调色板资源。该 commandlet 进程仍因工程已有的 GameFeatureData 配置条目及本机 8000 端口占用错误返回 1；这与 Python 作者脚本的成功结果分开记录，本次未修改这些全局设置。

用户规则：仅开发、资源制作与必要构建；不主动启动游戏、运行测试、截图或渲染，交由用户测试。
