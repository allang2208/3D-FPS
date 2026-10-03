# 无用参考工程清理 — 2026-10-03

用户先要求归到 trash，随后明确要求优先删除无用参考工程。本轮范围仅为下面的参考副本及已否决的 DGS Demo。全部先移入本轮 trash 子目录、记录散列并比对移动结果，再删除确认可清理的内容；trash 现保留清理记录，没有保留这些已删除工程的完整载荷。

已删除 **2679.0 个文件，14,268,716,725.0 字节（13.289 GiB）**。D 盘可用空间：清理前 28.297 GiB，清理后 41.588 GiB。可用空间还会受并行工作写入影响。

| 删除的原路径 | GiB | 删除依据与保留内容 |
|---|---:|---|
| `D:/FPS3D/FPSGAME/MilitaryTrenchMegascansSa` | 10.538 | 2024 个 Content 文件全部与正式 `FPSGAME/Content` 中对应文件 SHA-256 相同；独立参考工程只剩历史文档引用。保留正式内容及运行地图。 |
| `D:/FPS3D/DoorSystem` | 0.980 | 全部 525 个文件与 `D:/FPS3D/VaultCache/Untitlede28cc9a0a786V1/data` 相同。保留 VaultCache 原包和正式项目内 DoorSystem 资产。 |
| `D:/FPS3D/VolumeCloudUsingRayMarch` | 0.335 | 全部 73 个文件与 `D:/FPS3D/VaultCache/Material1ceacec75f17V1/data` 相同，活动制作脚本没有使用该独立工程路径。 |
| `D:/FPS3D/_dgs_demo/DGSDemo_427` 和同名 `.zip` | 1.436 | 已有草地方案明确记录“不采购、不采用”；仅删除解压的运行 Demo 及安装 ZIP。保留 `_dgs_demo` 中 Q&A 文本和全部原始截图。 |

## 本轮保留的参考与制作来源

| 路径 | 初始盘点 GiB | 保留原因 |
|---|---:|---|
| `D:/FPS3D/FabNatureExport` | 7.809 | 含独立植被、地表原始资产和导出制作源，不能视作整包重复。 |
| `D:/FPS3D/游戏动画示例` | 6.956 | Epic GASP 翻越等动作供体工程，保留独立原始动画与 UE 资产。 |
| `D:/FPS3D/AsianMaleJason` | 1.585 | `Tools/PlayerBody/prepare_jason.py` 直接读取该源工程。 |
| `D:/FPS3D/EasyBuildingSystemV10` | 0.495 | 虽然与 VaultCache 相同，`Tools/Building/import_ebs.ps1` 仍默认读取该路径，本轮保留以维持现有恢复入口。 |
| `D:/FPS3D/kimodo.cpp` | 13.848 | 已安装的动作生成工具与模型权重，仍被手臂技能和动作制作文档引用。 |
| `D:/FPS3D/test/uzi_ref` | 0.028 | `SourceAssets/RifleStockMelee20260918/extract_frames30.py` 仍读取其中视频。 |

正式 `Content`、`SourceAssets`、当前构建文件、玩家存档、VaultCache 都保留。本轮没有处理无明确废案依据的临时测试关卡。初始盘点中的大目录还有 `SourceAssets` 424.52 GiB、共享 `DerivedDataCache` 121.10 GiB、`Saved` 76.19 GiB；这些数字是占用量，不代表整目录可删。现有 UE/Zen 正在使用共享缓存，本轮没有修改它。

## 清单与恢复位置

- 本轮逐文件清单：`trash/reference-project-cleanup-20261003-01a1018d/manifest.json`。
- 完全相同副本的 SHA-256 证据：同目录 `reference-copy-evidence.json`。
- 实际执行脚本：同目录 `execute_cleanup.ps1`，仅供查看过程；清理已经完成，不要重跑。
- DoorSystem 和体积云源工程可从上述保留的 VaultCache `data` 目录重新复制。
- 战壕内容可从正式项目对应内容恢复；原参考工程外壳及被删除 Demo 没有完整载荷备份，manifest 本身不是备份。

没有由本任务启动、关闭或重启 UE，没有运行游戏、构建或游戏测试。本轮仅执行用户要求的文件占用调查、引用判断、副本散列比对和清理，游戏由用户自行测试。
