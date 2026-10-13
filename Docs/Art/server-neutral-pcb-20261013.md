# 网卡、阵列控制卡与处理器：白银黑配色

> 收尾更新：旧绿色纹理备份与撤回的原生迁移构建入口已移入trash，正式旧路径纹理别名继续保留。归档映射与恢复链见 [整理发布](../Publication/SearchCollectibles20261013/README.md)。

> 白银黑配色继续使用；图标朝向的后续调整见 [按占格居中与显卡 2×1](collection-icon-layout-r2-20261013.md)。

2026-10-13。按用户要求替换三件机房收集物的绿色表面，沿用现有零件结构、尺寸与占格，更新可编辑模型、导出模型、PBR 材质和背包图标。

| 物品 | 新配色 | 细节处理 |
| --- | --- | --- |
| 服务器网卡 | 白色 PCB、银色接口与散热片、黑色芯片 | 正反阻焊层和板边改为灰白；走线与丝印用深浅灰区分；网口绿色灯珠改为浅白色镜片 |
| 阵列控制卡 | 石墨黑 PCB、银色金属件、白色标识 | 主板和缓存副板均改黑；板边、过孔、走线和标签去除原来的绿色调 |
| 服务器处理器 | 银色顶盖、黑色封装基板和保护托 | 顶盖四周外露基板和边缘改黑，元件及丝印采用中性灰白 |

电路板保持非金属阻焊层质感，接口、散热片及处理器顶盖使用金属材质。金手指和处理器背面触点保留镀金本色；配色调整不把整件板卡刷成同一种金属。

制作源与回执位于 [ServerNeutralPCB20261013](../../SourceAssets/ServerNeutralPCB20261013)。网卡和阵列卡沿用 4K 图集，处理器沿用 2K 图集；每件均包含 BaseColor、ORM 与 Normal。UE 资产使用新目录 `/Game/Items/ServerNeutralPCB20261013`，旧版资产保留。物品目录只切换这三件的外观引用和说明，原 ID、价值、稀有度、堆叠与占格不变。

三张背包图标均沿用左上 45° 的主轴规则：

- [服务器网卡](../../Content/ColdSteelData/Icons/ServerNeutralPCB20261013/search_network_card.png)
- [阵列控制卡](../../Content/ColdSteelData/Icons/ServerNeutralPCB20261013/search_raid_controller.png)
- [服务器处理器](../../Content/ColdSteelData/Icons/ServerNeutralPCB20261013/search_processor.png)

旧存档兼容采用资源更新：同步原网卡、阵列卡和处理器所引用的六张 BaseColor / ORM 纹理包，以及三张旧路径 PNG。因此旧物品的模型和图标引用仍能显示新配色；不增加原生存档迁移。替换前的原资源保存在本批 `PreviousRuntimeAppearance`，回执为 [legacy-appearance.json](../../SourceAssets/ServerNeutralPCB20261013/Receipts/legacy-appearance.json)。

曾尝试构建存档迁移，但 Editor 构建遇到现有 `FPSPerformanceMetrics.h:440` 的 C2487 错误，Game 构建未继续。该次结果保存在 [native-build.json](../../SourceAssets/ServerNeutralPCB20261013/Receipts/native-build.json)。最终方案使用上面的资源兼容更新，撤回本次增加的迁移条件，配色交付不依赖新增原生二进制。

已保存资源见 [交付记录](../../SourceAssets/ServerNeutralPCB20261013/delivery.json)；实际资源安装和目录切换分别记录在 [installation.json](../../SourceAssets/ServerNeutralPCB20261013/Receipts/installation.json) 与 [publication.json](../../SourceAssets/ServerNeutralPCB20261013/Receipts/publication.json)。重新启动游戏后加载已更新的模型纹理与图标缓存。

17 件图标的批量制作入口已加入此版本；拼图工具改为读取当前物品目录中的实际图标路径。先前展示的拼图保留为当时版本，本次没有追加预览或运行游戏测试，由用户测试。
