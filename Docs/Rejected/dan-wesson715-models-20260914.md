# 715 两轮模型修改回退与归档

用户先后否定 Precision 全面几何重建和 Polish 局部精修：前者表现变差并丢失细节，后者在已认可的 Chrome 材质上修改模型后效果下降。两者都已回退，不能作为已接受方案再次默认接入。

当前主体为 `/Game/Weapons/DanWesson715/Chrome20260914/SK_DW715_Manny`。它沿用 Detail 的原形体、完整结构法线与 UV，使用用户反馈明显改善的官方 Chromium 材质。最新配件和雨滴入口见 [当前资源恢复说明](../Weapons/dan-wesson715-publication-20260914.md)。

2026-09-14 将以下六处移至本机 `trash/dan-wesson715-rejected-models-20260914/`，保留原相对目录：

- `SourceAssets/DanWesson715Precision20260914/`
- `SourceAssets/DanWesson715Polish20260914/`
- `Content/Weapons/DanWesson715/Precision20260914/`
- `Content/Weapons/DanWesson715/Polish20260914/`
- `Docs/Weapons/dan-wesson715-precision-20260914.md`
- `Docs/Weapons/dan-wesson715-polish-20260914.md`

共 379 个文件，2,454,674,299 字节。归档清单包含原路径、目标路径、大小、SHA-256、原因和保留替代物，移动前后散列一致；两个被弃用 Content 目录没有来自目录之外的资产引用。证据：[归档清单](../../SourceAssets/DanWesson715Publication20260914/archive-manifest.json)、[归档摘要](../../SourceAssets/DanWesson715Publication20260914/archive-summary.json)、[资产引用记录](../../SourceAssets/DanWesson715Publication20260914/archive-references.json)。`trash` 和其中第三方派生资产不公开提交。

保留 Upgrade、SingleLoad、ReloadFlick、ReloadSplit、ReloadMotion、ReloadNatural、LeftRecovery、MetalFinish、Attachments、Mirror、Detail、Chrome、RecordedAudio、AccessoryPolymer 等目录：它们仍是现用模型、材质或动作的上游制作依赖，不能仅凭日期或候选命名清理。

可复用教训：几何面数、倒角段数和贴图尺寸增加并不等于细节改善。用户确认形体正确时，优先区分原结构法线、UV/切线、表面噪声及反射响应；不要减弱整张结构法线、统一平均全枪法线或以更亮反光替代结构分离。保留已认可版本，用户否定的新版本退出加载入口并完整归档。

本次只执行用户要求的仓库整理与发布检查，没有启动游戏、渲染或开展玩法测试。
