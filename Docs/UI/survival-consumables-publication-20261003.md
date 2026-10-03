# 生存状态与食水消耗品：归档、技能与源码发布

本次覆盖本对话的生存状态栏 A、等级区域压缩、清泉赐福、复活资源、矿泉水、法棍、普通面包、汽水、夹层快捷绑定／右键使用、吞咽音效与 SAN 归零惩罚。正式运行源码仍为本机 `D:/FPS3D/FPSGAME`；当前工作区的 Editor 与 Game 常规构建已完成，二进制已保存。本轮整理仅执行仓库发布检查，未启动 UE、游戏、PIE、截图、渲染或游戏测试，也未对筛选出的公开提交另做独立构建。

## 当前规则

三项初始／最大值 100。默认饥饿消耗 0.05 点／秒、水分 0.075 点／秒，活跃地牢 SAN 消耗 0.02 点／秒；怪物 SAN 系数保留目录接口。饥饿或水分任一归零，每秒损失当前最大生命的 10%，两者同时耗尽不重复叠加。死亡重生和蟠桃原地复活从 60／60／60 开始。

SAN 为 0 时食水消耗乘 2，六维总属性乘 0.5，显示“精神崩溃”；SAN 大于 0 自动解除。属性倍率在计算层应用，不改写分配点、装备或原始档案值。清泉赐福持续 12 分钟、消耗乘 0.9，重复补水刷新时长；SAN 为 0 时合成为基础消耗的 1.8 倍。

| 物品 | 占格 | 每次效果 | 次数 | 动作时长 |
| --- | --- | --- | --- | --- |
| 矿泉水 | 1×2 | 水分 +30 | 2 次，满／半瓶图标与水位 | 总计 4 秒，其中饮水 2 秒 |
| 普通面包 | 1×1 | 饥饿 +15，水分 −10 | 单次 | 2.4 秒 |
| 法棍 | 1×3 | 饥饿 +60，水分 −30 | 单次 | 2.7 秒 |
| 汽水 | 1×1 | 水分 +20，SAN +10 | 单次 | 2 秒 |

右键直接使用适用于背包和装备夹层；快捷栏预览与实际绑定接受相同库存范围。关闭背包前复制物品 ID，避免 Selected 被清空后接触结算失效。附魔卷轴归强化道具，通过强化台使用；旧实例按必要目录字段迁移并保留个体数据。

## 生产源与本机恢复

| 生产入口 | 保留的本机输入与输出 |
| --- | --- |
| `SourceAssets/MineralWater20261003` | 用户下载的 Plastic Water Bottle 缓存、当前 Blend、壳／盖／水体／满半瓶 FBX、材质、两张库存图标及实际导入回执 |
| `SourceAssets/Baguette20261003` | Quixel Baguette Bread 缓存、当前 30 cm Blend／FBX、原 PBR、法棍图标及导入回执 |
| `SourceAssets/Bread20261003` | `D:/FPS3D/资产/bread_ukjkbef_high.zip` 解包源、当前 Blend／FBX、PBR、面包图标及导入回执 |
| `SourceAssets/SodaCan20261003` | `VaultCache/FabLibrary/Soda_Can-685c71b6/fbx`、SWESH 原包装与三张 PBR、12.2 cm Blend／FBX、图标制作源及导入回执 |
| `SourceAssets/FoodGrip20261003`、`SodaCanGrip20261003` | 当前 V7 原生几何与蒙皮输入、本机对象网格，小型抓握参数、共用食物时钟与发布脚本 |
| `SourceAssets/ConsumableAudio20261003` | 用户提供的四个 MP3、转码 WAV、音效清单与实际保存回执 |

运行资产位于 `/Game/Items/Consumables/{MineralWater,Baguette,Bread,SodaCan}20261003` 与 `/Game/Audio/Consumables20261003`；背包图标在 `Content/ColdSteelData/Icons`。复原时先恢复合法取得的本机输入及 V7 作者输入，按各目录的准备／作者脚本生成模型与图标，再通过对应后台导入脚本保存资产，最后执行物品配置／动作参数发布。食物与汽水配置读取专属抓握参数，食物时钟共用 `natural_food_motion.py`。只复制脚本或纯源码克隆不能代替资产导入。

公开内容是原创 C++、目录／小型动作参数、Python／PowerShell 配方、技能说明及恢复文档。Fab／Quixel 原模型、PBR、原始几何／蒙皮数据、用户 MP3／WAV、图标 PNG、Blend／FBX、UE 包、插件、构建、缓存与导入回执保留本机；没有核准这些原始素材的公开再分发许可。当前作者保留来源，不能从“可用于本项目”推导为“可在 GitHub 公开原文件”。

## 共享文件发布边界

共享 C++ 与 JSON 以当前 HEAD 为基线，仅发布本对话的生存／消耗品改动。其他角色外观、武器、附魔与联机改动保留工作区；不全库暂存、不撤回他人内容。公开消耗品保持原有单机使用门禁，未发布的第三人称呈现不会被夹带。

两处依赖其他未发布实现的本对话增量保存为接入补丁：

- `SurvivalConsumablesPublication20261003/stamina-san-overlay.patch`：在体质驱动的 `StaminaMaximum` 上叠加 SAN 倍率；需先拥有该耐力公式与调参字段。公共基线仍使用原耐力公式。
- `SurvivalConsumablesPublication20261003/multiplayer-survival-overlay.patch`：服务端采纳客户端档案时保留权威生存状态，客户端合并权威镜像时采纳生存字段；需先拥有本机 M2 `ColdSteelPlayerState`。不公开整套未发布联机源码。

本机现有源码已包含这些增量；补丁是公开恢复交接，未声称已应用到公共基线。所公布原生子集未单独构建，完整本机工程构建成功与公开子集／游戏体验分开记录。

## 归档与技能

8 个已被选版和正式作者源替代的文件移至 `trash/survival-consumables-retired-20261003`，共 28,990,731 字节：7 张旧 A/B／耗尽候选、1 份法棍自动 `.blend1` 备份。清单 `SurvivalConsumablesPublication20261003/archive-sources.json` 记录原路径、目标、大小、SHA-256、原因、替代物及移动后回读一致。trash 不进 Git，未删除当前模型、图标、声音、作者源或合法来源。

保留的 refined A PNG 是等级框最终隔离为 64×56px 之前的历史设计参考，不能作为当前运行截图；现行 `ColdSteelTopVitals` 与作者脚本是布局真源。原计划中的旧 PNG 路径按归档清单映射恢复。

经验分别进入 `ue5-cpp-gameplay` 的生存状态与倍率、`ue5-item-asset-workflow` 的消耗品接入、`ue5-fps-arms-animation` 的食水抓握和非线性运动、`ue5-ui-umg-slate` 的状态栏布局。四份参考及入口均同步个人技能和工程镜像，默认工作方式继续为后台制作、必要编译与落盘，由用户进行游戏测试。
