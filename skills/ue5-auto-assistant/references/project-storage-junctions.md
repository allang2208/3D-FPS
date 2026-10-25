# FPSGAME 资产和缓存的目录联接

适用于本项目的 SSD 容量整理与恢复；仅在任务涉及这些路径时读取。2026-10-25 的入口是：

| 工程入口 | 实际位置／职责 |
| --- | --- |
| `D:/FPS3D/FPSGAME` | 唯一源码与 Git 工作目录；Config、Tools、Saved 和构建中间产物仍按工程规则保存 |
| `D:/FPS3D/FPSGAME/Content` | 联接到 `F:/FPSGAMEData/Content`，正式运行资产和 ColdSteelData 配置 |
| `D:/FPS3D/DerivedDataCache` | 联接到 `F:/FPSGAMEData/Caches/DerivedDataCache`，DDC／Zen／虚拟纹理块缓存 |
| `F:/FPSGAMEData/Builds` | 明确指定时的打包输出；不是源资产或 DDC |
| `F:/FPSGAMEData/Preserved_NoAutoDelete` | 迁移事故的留存资料；不是活动 Content，是否仍存在以现场为准 |

- 后续工具继续通过稳定的 D 盘工程入口读写；不另建一个普通空 Content 掩盖失效联接。任何迁移前先辨别普通目录、联接与解析后的目标，确认现有进程正在使用哪个路径。
- `Content`、`SourceAssets` 与 `Saved/SaveGames` 各有不可再生内容，不能按“缓存构建”一并处理。DDC 可以重建，不代表整个 Saved 或父目录可以清空。
- Windows 文件整理使用同一 PowerShell 调用的字面路径。禁止把一个 shell 枚举的路径拼给另一个 shell 执行递归移动／删除；命令中的引号变化可能改变删除范围。
- 先制作精确清单和备份，再执行已授权的具体移动。回读文件数／散列与联接目标属于迁移任务的必要步骤；不能用目录存在或 robocopy 启动成功代替完成证据。失败或范围不明时保留现场，不以扩大删除路径解决。
- 备份放 NAS 与实际运行路径是两件事；确认没有活动引用后才能按用户指令处置留存目录。文件夹名称不能代替引用核实。普通源码发布不移动或清理这个留存目录。

此页记录本项目路径选择，不能当作其他项目的通用迁移命令，也不授权自动清理。
