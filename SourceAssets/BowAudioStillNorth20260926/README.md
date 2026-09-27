# 暗纹猎弓分阶段音效

来源是 Still North Media 的 CC0 中世纪武器录音，作者 Ben Jaszczak 和 Brian Nelson。
GitHub 是索引，完整录音从 OpenGameArt 镜像获取。来源链接、原始与衍生文件散列见
`sources.json`、`audio-manifest.json`；许可见 `LICENSE-CC0.txt`。

- 获取：`py -3.11 SourceAssets/BowAudioStillNorth20260926/acquire_sources.py`
- 制作：`py -3.11 SourceAssets/BowAudioStillNorth20260926/author_audio.py`
- 后台导入与原生构建：`powershell -NoProfile -File SourceAssets/BowAudioStillNorth20260926/run_background.ps1`

| 资产 | 原始录音／制作 | 游戏触发 |
| --- | --- | --- |
| S_Bow_TakeArrow | Arrow Fletching 16.82–17.34 s，保音高压为 0.26 s | R 搭箭到 28%；空弦左键在 0.2 s 入场起点播放，并适配至 0.16 s |
| S_Bow_Nock | English Longbow Nock Arrow 3.64–3.83 s，0.16 s | R 搭箭到 82%；空弦左键入场结束 |
| S_Bow_Draw | English Longbow Draw 1.65–4.19 s，保音高压为 1.4 s | 进入 Drawing 后一次播放，按弓术后的拉满时长调整播放速率 |
| S_Bow_Release | English Longbow Shoot 0.087–0.56 s，保留原速 | 成功生成并结算箭支时；取消不触发 |

取箭是使用箭羽摩擦录音制作的动作拟音，不宣称独立箭袋录音。短入场阶段还会提高取箭音的
播放速率；技能缩放拉弓音同样会改变音高。原速基线的离线时长适配保持音高。
未追加飞行、命中、弓弦保持循环或其他武器音效。

四个 WAV 均为 48 kHz、单声道、16-bit PCM，去低频、边缘淡入淡出并留峰值余量。
导入为独立非循环 SoundWave，ForceInline，音量／音高 1；运行时倍率依次为
0.4／0.5／0.42／0.6，放箭保留既有拉距音高变化。
取箭／搭箭由可停止的 HandlingAudio 管理，拉弓由 DrawAudio 管理；取消、收起、换武器、
放箭、销毁时结束对应声部，满拉后不会重复播放拉弓音。

`bow_presentation_revision=15` 通过既有库存迁移更新旧弓。新增资源键
`bow_take_arrow_sound` 纳入异步加载及表现签名；不修改弹药扣除、伤害或 0.2 s 到位合同。
包装配置显式包含本音效目录，因为引用来自 JSON。

交付状态见 `Docs/Weapons/dark-bow-audio-stillnorth-20260926.md`。
默认不试听、不启动游戏、不执行测试；素材选择基于录音名称与波形编辑，听感由用户测试。
