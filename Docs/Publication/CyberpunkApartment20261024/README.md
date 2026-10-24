# 公寓与海湾制作、同步修补的源码发布

本批对应现有 `/Game/GameMaps/L_CyberpunkApartment`：分房间重建、灰黑柜体、门窗/卫浴、电视与设备、近岸楼群、条形/点缀窗灯、广告和探照光束、道路车流、水面反射，以及阳台左右玻璃栏杆。不是新的场景版本，也不覆盖本机已接续的卧室样板或角色动作精修。

## 发布与恢复边界

- `SourceAssets/CyberpunkApartmentRebuild20261022`、`CyberpunkBayLayered20261022`、`CyberpunkBayBuildings20261022` 等目录公开作者脚本、设计参数和材质代码。旧版本仍承担下游作者/材质库依赖，不能按编号删除。
- `ApartmentAtmosphere`、`ApartmentDeviceControl`、`ColdSteelSlidingDoor`、`ColdSteelSceneContainer` 和限定网络夹具公开当前本批代码。共享角色、控制器、HUD、相机和动画消费者仅重放本批差量，其他未提交功能保留本机。
- **公开切片不等于干净检出可直接构建或运行的完整公寓。** 共享个人搜索基础仍未在本仓库完整发布。恢复本机对应基础后，按 [前置清单](integration-prerequisites.json) 的规范化 SHA-256 应用 `Integration/container-viewers.patch`、`warehouse-close.patch`、`furniture-initial-state.patch`。基线不匹配时合并语义，不盲目覆盖文件。
- 当前坐卧动作已经使用另一轮 FurnitureRest 精修。其精确角色键、源文件与配置散列见 [本机动作依赖](body-routes-required-local.json)，本批没有将它们装作自己的动作配置提交，也没有把旧 V14 动作恢复为默认。V14 原始制作脚本保留历史恢复能力，但发现较新 Rest.Apartment 路由时会拒绝重写。
- 地图、uasset、Blend/FBX、图片、视频、音频、DDS/cubemap、字体、原素材和密集骨骼采样均留本机。已许可使用不等于可以重新分发；复用的地牢家具、人物骨架、天气与水体仍须合法取得。

## 本机增量恢复

1. 恢复合法 Content、作者输入、生成装配清单及各版 `assets_saved.json`/`installed.json`；公开脚本不是这些资源的替代品。先确定目标地图和当前作者来源，不把历史诊断/TODO 当成当前状态。
2. 常规结构/材质从各版作者和导入脚本恢复；下游 `apply_upgrade` 在成功安装回执存在时才继续重放。V19 是当前亮窗与四组新增广告，V20 是侧面玻璃栏杆，V21 是统一表现时钟及灯具关联。
3. V14 场景尺寸/摆位可通过 `install_level.py` 重放；当前动作配置继续归后续坐卧作者所有。不要重跑历史 V14 动画发布器覆盖它。
4. V21 在原动态材质的副本中接入共享时差，记录 Actor/组件/槽位及源材质，仅恢复仍匹配自己源绑定的槽位；不会整张地图回滚到旧快照。
5. UE 操作继续走现有互斥，默认后台导入保存，不自动启动编辑器、PIE 或游戏。仅开发预览使用 `open /Game/GameMaps/L_CyberpunkApartment`；地图尚未加入正式 MapsToCook，不宣称打包版本可加载。

## 退役内容

退役地图/配置备份、Blender 自动备份、Python 缓存、首轮失败构建和未完成的 wire-01 已归入 `trash/cyberpunk-apartment-20261024/`，逐文件原路径、归档路径、大小、散列与替代物见 [归档清单](archive-manifest.json)。当前正式 Content、可编辑 .blend、制作脚本、最终 wire-02 证据和后续 BedroomPilot 均保留。归档目录不公开上传；需要恢复历史备份时按清单原路径回放，不能把整个旧备份覆盖当前工作区。

## 检查记录

上一轮已授权的本机整合 Editor/Game 构建、保存地图配置检查，以及主机/客机/晚加入三进程 UDP 六阶段通过，见 [历史检查摘要](historical-audit.json)。柜门多人查看、重开、晚加入、断线清理、设备开关时间和注入休息状态均有对应记录。

本轮整理仅做归档散列、发布范围、索引差异、敏感内容/大小及远端回读检查；没有重跑 UE、游戏、视觉或性能验收。历史结果不是本次裁剪公开树的编译证明。仍未覆盖物品并发转移、同档断线恢复、跨机器/打包联机及真实上下床腿部画面。
