# RSH 两款方形瞄具专属化

用户要求两款方形瞄具作为 RSH 专属改造替换原全息选项，普通款开镜耗时降低 5%，不得改动其他枪械。

| RSH 原 ID | 专属 ID | 名称 | 倍率 | 开镜耗时 |
| --- | --- | --- | --- | --- |
| `holographic` | `rsh12_square_sight` | 方形瞄准镜 | 1 倍 | -5% |
| `eoth_holographic` | `rsh12_tactical_square_sight` | 战术方形瞄准镜 | 1.5 倍 | -5% |

仅改 `gunsmith.json` 中 `ue_rsh12` 武器块，两项旧选项原位替换为专属 ID。其他武器及 common_options 的原始文件字节不参与替换。先前 RSH 基础腰射扩散 4 倍继续保留。

`RSH12OpticAssets` 将新 ID 映射到现有 RSH 专用网格、导轨与安装偏移；单持与双持模型均复用现有资产。枪匠卡片增加 RSH 限定的专属标记，图标沿用已有配件图，不生成或修改其他枪械的共享图。

旧存档通过 `GunsmithSystem::Normalize` 兼容：仅 `Definition=ue_rsh12` 且槽位为 `optic` 时转换两个旧 ID。原有装配和属性读取都会获得新 ID，正常应用改造时写回，不直接修改存档文件。其他武器的同名旧 ID 保持原义。运行倍率、资源预加载、瞄具挂载及双持近战配件动作分支同步适配新 ID。

RSH 原始瞄具挂点生成器、紧凑瞄具和总目录重建入口同步沿用专属配置，避免重制退回通用选项。作者及制作结果位于 `SourceAssets/RSH12ExclusiveOptics20261004`，`catalog_receipt.json` 记录实际替换；必要构建结果记录为 `build_receipt.json`。

目录已发布，`FPSGAMEEditor` 基础模块后台构建成功，DLL 于 2026-10-04 10:05:26 UTC 落盘；见 `build_receipt.json` 与 `Build-console.log`。未主动打开编辑器、运行游戏或执行自测，由用户测试。
