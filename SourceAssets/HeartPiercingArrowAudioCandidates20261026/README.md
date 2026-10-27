# 穿心箭出箭音效试听候选

2026-10-27 收尾：当前选定并实际保存的是 SelectedH 的 BalancedV4，来源为 StrongV2 的 E/F/G 分层。以下 A–D 为历史选型记录；未采用的试听、Singles、旧 CombinedV3、两份首次获取脚本及失败 HTML 已移入 trash/bow-skills-retired-20261027/ 的同名原路径。当前 E/F/G Singles、CC0 原始录音、许可与 BalancedV4 作者链保留。归档清单见 Docs/Publication/BowSkills20261027/archive-manifest.json。

仅供用户试听选型，尚未选定、导入或接入 UE。未修改当前普通射箭或穿心箭音效，未启动编辑器或游戏。

| 编号 | 试听方向 | 素材与处理 | 授权 |
| --- | --- | --- | --- |
| A | 游戏战弓 | artisticdude 的 Bow.wav，保留原速与音高 | CC0 |
| B | 重弩弹弦 | HolgiB 的 crossbow_dryshot.flac，速度／音高倍率 0.8 | CC BY 3.0 |
| C | 厚重长弓 | Still North Media 的 English Longbow Shoot.wav，截取 0.087–0.560 秒，速度／音高倍率 0.85 | CC0 |
| D | 弓弦破空 | dorkster 的 FLARE shoot.ogg，保留原速与音高 | CC BY-SA 3.0 |

四款仅统一至 −3 dBFS 峰值、加短边缘淡变，未进行主观等响匹配，未叠加低音或其他音效。`Auditions` 中每段连放两次，间隔 0.7 秒；`Singles` 保留独立单发候选。`prepare_oga_auditions.py` 从 Sources 重建。实际听感与选择由用户确定。

## 来源与署名

- A: “Battle Sound Effects / Bow.wav” by artisticdude, submitted by Ogrebane. https://opengameart.org/content/battle-sound-effects — 本次选择 CC0 授权：https://creativecommons.org/publicdomain/zero/1.0/
- B: “Crossbow sounds / crossbow_dryshot.flac” by HolgiB. https://opengameart.org/content/crossbow-sounds — https://creativecommons.org/licenses/by/3.0/ 。本试听版降调／减速、重采样、调整增益和边缘淡变。
- C: “Medieval sound effects - Weapon Textures / English Longbow Shoot.wav” by Ben Jaszczak and Brian Nelson / Still North Media. https://opengameart.org/content/medieval-sound-effects-weapon-textures — CC0；复用本机已有原始素材，原来源记录及许可保存在 Sources。此版裁切及降调。
- D: “Bow & Arrow Shot / shoot.ogg” by dorkster, based on qubodup sound sources. https://opengameart.org/content/bow-arrow-shot — https://creativecommons.org/licenses/by-sa/3.0/ 。本试听衍生音频沿用 CC BY-SA 3.0，修改包括重采样、增益与边缘淡变；无音高或音色改动。

首次检索的 Freesound 四款公开预览下载返回 HTTP 403，未作为本次 A–D 交付音频；对应 HTML 及首次获取脚本 prepare_auditions.py 仅保留研究记录，勿误当成已取得的音源。
