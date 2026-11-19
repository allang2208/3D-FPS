# 丘陵村工匠与酒馆

本批收录 Jason 强壮派生体、铁匠与木匠、冷钢对话与交易、学徒制作任务，以及酒馆残破和修复两套布置。村庄由开房的主机创建或续读。客机使用房主同步的丘陵种子、世界 ID 和修复状态，个人角色保留自己的学徒进度与购买记录。

## 如何恢复

1. 先恢复丘陵村、修女、工坊事务和角色的资产依赖。Jason R4 母版与工匠身体各有独立路径。两名工匠共用已带肩臂姿态修正的身体，各自装配头部与工作服。酒馆房壳、窗、厅堂和后厨使用同一村庄子关卡。详见[资产清单](assets.md)。
2. 工程的 `Source/FPSGAME` 提供独立的对话视口、逐句播放和酒馆陈设组件。本目录的 [Implementation](Implementation/Source/FPSGAME) 保存居民原地转身及其他依赖完整本机宿主的功能源码。[Integration](Integration/GAMEPLAY.md) 给出共享文件的补丁基线与恢复顺序。[Configuration](Configuration) 中的配方与物品按键合并，保留目标工程里的其他条目。
3. Jason 制作配方在 `Tools/JasonStrongVariant`，两名工匠的部件制作配方在 `Tools/VillageBlacksmithNPC` 与 `Tools/VillageCarpenterNPC`。铁匠沿用修女的四视图生成设置；已有修女管线的工程直接复用，其他工程可把[所需共享模块](Prerequisites/Tools/ChapelNun/meshy_head.py)放入 `Tools/ChapelNun/`。酒馆房壳和家具配方在 `Tools/WorldGeneration/AbandonedVillage` 与 `Tools/WorldGeneration/VillageTavern`。

## 已归档的验证记录

以下结果来自本机完整工程当时使用的模块。监听服记录包含房主、两名不同身份的客机及原玩家重连。该轮使用 NullRHI，图像、动作观感和公网连接未覆盖。归档发布期间未启动 UE、重新构建或重跑这些用例。

| 历史用例 | 通过 |
| --- | ---: |
| [监听服交易、教学与重连](Evidence/listen-server.json) | 30/30 |
| [制作、领取、废弃和重试](Evidence/crafting-branches.txt) | 39/39 |
| [教学材料发放](Evidence/lesson-materials.txt) | 22/22 |
| [共享货架与结算](Evidence/shared-stock.txt) | 15/15 |
| [客机个人存档](Evidence/guest-save.txt) | 14/14 |

## 清理与找回

本次移入本机 `trash/ArtisanVillage20261119` 的普通文件共 3,545 个、8,259,584,499 字节，含 160 张检测图，未发现本次生成的 GIF。18 个目录联接另存目标记录。美术和测试宿主分别使用 `Art/manifest.json`、`Network/manifest.json`，逐项记录原路径、归档位置和 SHA-256。找回某个文件时，先匹配散列并确认原路径可用。见[归档统计及清单散列](archive-summary.json)。

正式角色、衣料与头部制作输入、酒馆家具和纹理、外部授权素材、正式存档及 UE 二进制保存在本机。Git 提供源码、原创建模配方与恢复说明；从公开检出恢复完整场景仍需上述资产和共享宿主。
