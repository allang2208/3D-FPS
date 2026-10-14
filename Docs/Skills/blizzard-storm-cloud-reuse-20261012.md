# 暴风雪直接复用雷暴乌云

用户截图显示初版暴风雪乌云细小、分散并呈规则网格，明确要求直接复用雷暴领域的乌云。已替换暴风雪现用的 `/Game/Skills/StormClouds/RollingV1/NS_BlizzardStormCloud`，保持现有加载路径。

## 当前表现结构

- 直接复制 `/Game/Skills/StormClouds/RollingV1/NS_StormDomainCloud` 中的 `DenseDarkBase`、`RollingCloudBody`、`SlateCloudCrown`、`ElectricCloudRim`、`SoftCloudFringe` 五层。云的重叠分布、尺寸、配色、动态密度、材质、48 个核心粒子及约 8 个边缘粒子均来自现用雷暴。
- 不复制 `CloudDischarges` 与 `FallingElectricSparks`；`ElectricCloudRim` 本身是灰色云层。
- 移除原 `IndoorCloud` 的 5×5 可见云块排列。25 个房间单元只负责查询真实云团位置的地面、净空和墙边宽度：开放单元保留完整云宽，低顶压薄并置于当地天花板下，墙边单元收窄。90～180 cm 净空渐隐规则保留。
- 暴风雪区域生命周期、技能范围、伤害、雪雾、落冰、预览与手边蓄力云继续沿用现有实现；雷暴源资产不修改。

## 作者与落盘

定向入口 `Tools/Skills/reuse_storm_domain_blizzard_cloud.py`；完整恢复作者 `Tools/Skills/build_rolling_storm_clouds.py` 的 `blizzard()` 已同步新结构。只保存暴风雪区域云，未修改 C++，不需要原生重编译。

编辑器中通过 `Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript` 串行执行。第一次复制后 Niagara 已编译，但引擎保存拒绝跨包引用雷暴系统内部的私有 emitter；现已按 `FVersionedNiagaraEmitterData::RemoveParent` 的语义清空复制层的 `VersionedParent` 和 `VersionedParentAtLastMerge`，保留复制的完整图表及渲染参数。该处理同步作者，后续恢复不会再产生同一保存错误。

用户停止试玩后，恢复入口只继续处理已制作资产的引用与编译保存，未重复重建云层。最终 `resume-save-02.json` 返回 `success=True`、`BLIZZARD_STORM_CLOUD_REUSED`、`stage=assets_saved`。保存回执 `SourceAssets/BlizzardStormCloudReuse20261012/asset-authoring.json`，调用记录 `Saved/BlizzardStormCloudReuse20261012`。用户截图保存在同一 SourceAssets 目录的 `Reference/user-grid-cloud.png`。

未启动游戏、截图、渲染或测试；资产编译保存成功不代表观感验收，交由用户重新施法确认。
