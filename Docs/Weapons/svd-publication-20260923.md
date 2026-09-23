# SVD / PSO 源码整理与发布 — 2026-09-23

本批发布 SVD 开发链的制作脚本、所属运行接入、配件目录、来源记录和技能沉淀。当前手型由用户明确确认成功；最新材质与衔接件已经后台导入保存，未进行新的视觉或游戏测试。

## 当前入口与恢复

| 内容 | 本机制作入口 | 当前资源 |
| --- | --- | --- |
| 用户认可的换弹抓握 | `SourceAssets/SVDThumbUp20260923` | 原厂及四类握把的普通／空仓换弹，共 10 个当前动画 |
| 表面与接口细化 | `SourceAssets/SVDRefinedFinish20260923` | 37 组干湿表面、22 个网格绑定；5 种前握把、通用桥架及 SVD 骨骼网格共 7 个模型更新 |
| 后托拆分与连接杆 | `SourceAssets/SVDStockAdapter20260923` | `StockAdapter20260923/SK_SVD_ModularStock` 与四种替换枪托 |
| 通用改造件 | `SourceAssets/SVDAttachments20260923` | `Accessories20260923` 的模型、动作、湿润映射和图标 |
| 原厂 PSO 接缝 | `SourceAssets/PSOSeamRepair20260923` | 金属环从透明镜片槽恢复至不透明镜体槽 |
| 跨枪 PSO | `SourceAssets/PSO1Russian20260923` | 仅 AKM、A762、PKM 可选 `pso1_4x`；SVD 原厂 PSO 独立保留 |
| 用户指定音轨切片 | `SourceAssets/SVDVideoAudio20260923` | 6 个本机 SoundWave，位于 `VideoAudio20260923` |

资源路径均以 `/Game/Weapons/SVDDragunov20260922/` 为枪械前缀；跨枪 PSO 位于 `/Game/Weapons/PSO1Russian20260923/`。最新表面位于 `RefinedFinish20260923`。保留共享 Manny 手臂及现有瞄具、配件来源。

这是源码／配方发布，不是完整资产备份。公开仓库不包含第三方模型、纹理、音视频、Blend、FBX、uasset、密集骨姿态／网格采样、桥接输出或本地恢复副本。需要有权使用的完整本机 `Content` 和 `SourceAssets` 才能恢复作者输入及最终资产，通用边界见 [AssetSetup](../AssetSetup.md)。`finish_receipt.json`、`connectors_receipt.json`、`import_receipt.json` 等实际导入回执保留本机；本发布不把它们当作公共 checkout 的运行验收。

视频音轨为用户指定的 Bilibili AAC 来源，尚无公开再分发许可。解码为 PCM WAV 不构成无损原始录音；只发布切片脚本和来源／时间点记录，不发布音频。原 SVD 模型保留 LeroyCake / CC BY 4.0 署名；共享手臂、动作、参考材质各沿用自身许可，见 [第三方说明](../../ThirdPartyNotices/SVD_DRAGUNOV.md)。

## 可恢复归档

396 个文件共约 1451.1 MiB 移入 `trash/svd-superseded-20260923/`：90 个被最终手型替代的换弹 FBX、298 个恢复快照、3 个 Blender 自动备份、5 个已被最终回执替代的桥接／失败输出。未删除内容，逐文件记录原路径、目的地、大小、SHA-256、原因和替代物，移动后读回散列一致。公开 [精确清单](../AssetArchives/svd-superseded-20260923.json)，`trash` 本身不提交。

最终手型仍依赖 `SVDFrontHalfGrip`、`SVDReloadHandRepair`、`SVDContactWrap` 等早期 Blend／参数／作者脚本。它们是制作依赖，继续留在本机。PSO 的 `before-topmount` 是现存恢复脚本明确读取的输入，也保留。没有按日期清空旧目录或改动其他任务的试验文件。

## 本次沉淀

- [异形弹匣自然抓握](../../skills/ue5-fps-arms-animation/references/irregular-magazine-grip.md)：局部包握、拇指向上、冻结已认可的掌心与四指，不以拟合误差代替自然手型。
- [SVD 涂层与安装接口](../../skills/ue5-weapon-workflow/references/svd-finish-and-interfaces.md)：替换旧涂层而非叠加、保护材质身份、同步干湿版本、冻结握点和安装面、保留原厂分区显隐、区分透明材质与实际缺面。
- 个人 SKILL 与工程对应内容同步。案例粗糙度／关节角度仅供复现，不推广为跨枪通用常量。

## 推送范围

从 `D:/FPS3D/FPSGAME` 直接精确暂存，普通推送到授权 `origin` 的 `main`。共享源码只选 SVD／PSO 的变更块；目录按武器身份合并本批配件，保留 HEAD 中其他武器与并行属性。SVD 狙击数值／暴击加成调整、其他武器及通用移动／UI／战斗修改留给所属任务，不夹带发布。

瞄具源码同时补齐 `GetLastShotAgeSeconds`／`GetLastShotSeed` 的定义：HEAD 已包含它们的声明和镜内呈现调用，属于本次 PSO 呈现必须保留的接口依赖，不改变开火行为。

本次执行用户要求的仓库整理与发布前检查，包括完整暂存差异、空白、文件大小、敏感信息、许可、脚本语法、相关文档链接和归档读回。没有重新编译或启动游戏；历史构建结果只按原日期保留。发布 SHA 与远端回读结果在交付消息中报告。
