# RSH 基础腰射扩散与方形瞄具调整

用户要求基础腰射扩散改为当前 4 倍，保留两款现有瞄具模型并改名；EOTH 使用固定 1.5 倍放大，保留开镜耗时降低 5%。范围仅为 RSH-12。

| 配置 | 本轮修改 |
| --- | --- |
| `ue_rsh12.base.spread_mult` | 原来省略此键，默认 1；现在显式设置为 4 |
| `holographic` | 名称改为「方形瞄准镜」，继续 1 倍，开镜耗时不变 |
| `eoth_holographic` | 名称改为「战术方形瞄准镜」，固定 1.5 倍，`ads_percent=-0.05` |

实际数据为 `Content/ColdSteelData/gunsmith.json` 的 RSH 条目；仅定向写入该武器块，保留其他武器的原始字节。`SourceAssets/RSH12SquareOpticsBalance20261004/publish_catalog.py` 固定目标散布为 4，重复运行不继续翻倍；原始快照保存在同目录 `Before/`，制作结果记录为 `catalog_receipt.json`。原始 RSH 与紧凑瞄具的目录重建入口同时沿用本次修改。

`GunsmithSystem` 的基础散布继续进入单持 `HipSpreadMultiplier`、双持每手 `Stats.Spread`、准星及枪匠显示，不另加单枪末端乘数。瞄准倍率在 `ScopeOpticalPresentation.cpp::GetOpticMagnification` 为 RSH 的 `eoth_holographic` 返回 1.5，已有 ADS 视角计算按半角正切比应用倍率；其他武器同 ID 的瞄具保持原行为。保留实体方形镜框与镜片，不切换为全屏高倍镜遮罩。

改造 ID、网格、挂点、材质和图标继续使用现有版本，存档无需更换配件 ID。开镜耗时继续由目录 `ads_percent` 和原有公式汇总。上一轮基础后坐力、稳定性与专属消音器保持原值。

后台编译入口为作者目录 `build_editor.ps1`，实际结果记录为 `build_receipt.json` 与 `Build-console.log`。`FPSGAMEEditor` 基础模块构建成功，DLL 于 2026-10-04 09:55:11 UTC 落盘。本次未启动 UE、PIE 或游戏，未执行自测，由用户测试实际手感。

后续用户将两款方形瞄具指定为 RSH 专属，并要求普通款也采用开镜耗时 -5%；新 ID、旧存档兼容与本轮构建记录见 [RSH 两款方形瞄具专属化](rsh12-exclusive-square-optics-20261004.md)。本页保留上一阶段口径。
