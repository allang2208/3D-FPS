# 剩余候选清理记录

完成时间：2026-10-03T21:58:27.2692449+08:00。用户在四类候选报告后明确授权“帮我清理”。

已逐文件移入本批 trash payload，并读回 SHA256；随后永久删除该 payload，以释放 D 盘空间。共删除 **3,026 个文件，7.975 GiB**。

| 范围 | 文件数 | 已删除大小 |
| --- | ---: | ---: |
| 旧发布验证副本 Binaries / Intermediate | 1,232 | 5.782 GiB |
| 未引用的旧截图序列 | 1,781 | 1.453 GiB |
| 重复雕像内层 ZIP | 6 | 0.704 GiB |
| 与正式资产相同的旧保存临时文件 | 7 | 0.037 GiB |

执行前 D 盘可用 80.211 GiB；完成时可用 **88.198 GiB**。并行任务可能同时写入，磁盘净变化与本批删除字节数可能不同。

## 旧验证副本范围

只逐文件处理以下四个生成目录中的已列明旧文件，没有递归删除旧副本根目录或 Content：

- `D:\FPS3D\FPSGAME\Saved\TraversalPublication20260912\checkout\Binaries`：0.213 GiB。
- `D:\FPS3D\FPSGAME\Saved\TraversalPublication20260912\checkout\Intermediate`：2.765 GiB。
- `D:\FPS3D\FPSGAME\Saved\TraversalPublication20260911\BuildCheck\Binaries`：0.099 GiB。
- `D:\FPS3D\FPSGAME\Saved\TraversalPublication20260911\BuildCheck\Intermediate`：2.705 GiB。

## 其他范围

历史长序列仅删除预先确认的未引用编号 PNG；保留每段五张样本、命名静帧、短序列、明确引用的图片、视频、GIF、日志、音频、数据和作者工具。

- `Saved\GrassResponseAudit20260927` 的选定 PNG：0.361 GiB。
- `Saved\QuickCombatAudit` 的选定 PNG：0.276 GiB。
- `Saved\StairMovement` 的选定 PNG：0.291 GiB。
- `Saved\TraversalPublication20260911` 的选定 PNG：0.060 GiB。
- `Saved\TraversalPublication20260912` 的选定 PNG：0.464 GiB。

六个内层 ZIP 均在保留的外层下载包中存在同内容副本，所有成员也已完整解压并比对相同；原下载包、源模型、贴图与授权记录保留。七个 .tmp 与保留的正式 Content 资产 SHA256 相同，其余不同内容或较新的保存临时文件不动。

## 保留范围与记录

本批记录保留 685 个文件，2.285 GiB；另保留两个旧副本中的 **63 个 Content 链接**。

- 主工程及共享 DerivedDataCache / Zen、主工程 Binaries / Intermediate、模型和制作加速缓存保留。
- 旧副本中的作者源码、脚本、发布收据以及所有未选文件保留。
- 内容不同的 .blend1、.tmp、恢复备份、存档、源贴图和先前清理保留的样本不处理。
- 跳过候选：0 个。

清理后仅核对本批路径：候选源文件已不存在，清单内保留文件和 Content 链接仍存在，本批 payload 已删除。未启动、关闭或重启 UE，未运行游戏测试。

归档记录：`D:\FPS3D\FPSGAME\trash\remaining-priority-cleanup-20261003-01a1018d`。其中 `manifest.json` 记录原路径、归档路径、大小、SHA256、删除理由与保留替代物；`events.jsonl` 记录移动和删除，`approved-assessment.json` 保存原候选范围，`summary.json` 保存结果。**归档仅保留清单与证据，已删除的 payload 不可由此还原。**
