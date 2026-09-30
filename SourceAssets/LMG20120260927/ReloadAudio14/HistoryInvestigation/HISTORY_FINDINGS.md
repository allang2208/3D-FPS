# PKM 换弹尾音修复：保存、Git 与当前内容排查

2026-09-28。用户要求查工作记录，确认尾音处理是否没保存或被 Git 还原。本轮只读调查；新增诊断导出和本报告，没有修改音效、运行源码、Git 索引或提交。

## 结论

9 月 25 日的开盖、合盖尾音修复已保存到本机 UE 资产。当前磁盘和当前 UE 会话内读取的两声仍为修复版，未发现被旧版覆盖的证据。Git 发布确实遗漏了这次独立尾音修复的脚本和记录；已发布的基础导入入口仍指向未修尾音的原始 WAV。这个恢复流程缺口确实能在重跑旧导入脚本时造成覆盖，但不是本次两份现用资产已经回退的证据。

用户现在听到的具体残留声音尚未定位到单个播放事件。不能将 Git 漏提交直接当作当前听感问题的已证实原因，也不能将上一轮发现的 201 AKM 通用分支当作弹箱尾音的已证实来源。

## 保存证据

原记录：`SourceAssets/PKMLowpoly20260922/BeltAudio22/BGM_FINDINGS.md` 的 9 月 25 日接入记录，以及 `rebuild/import_receipt.json`。两声分别引用 `S_PKM_CoverOpen_rebuilt_delivered.wav`、`S_PKM_CoverClose_rebuilt_delivered.wav`，`saved: true`。

现用包的最后写入时间均为 2026-09-25 16:05:07：

| 资产 | 大小 | SHA-256 |
| --- | ---: | --- |
| S_PKM_CoverOpen.uasset | 45909 | 3306617588baaf030aacf33c952d02d136a13c43bc24fc30d057de8a51d3c87e |
| S_PKM_CoverClose.uasset | 20686 | 442703beded12c656e4be455bb4c38208508d9179ca1588f80b4c41463315dad |

上述散列也与本轮之前 `Refine12/current.json` 中的实际资产记录一致。

本轮通过现有 MCP 桥读取当前 UE 会话并导出两声，没有启动、停止或操控游戏，没有保存或重导资产。`loaded_audio.json` 记录读取结果；`pcm_comparison.json` 确认两者 PCM 均与修复 WAV 逐样本一致，均不等于原始旧 WAV。读取时角色没有对应的机械声音组件记录，因此该结果不能冒充一次实际换弹的播放捕获。

## Git 证据

- 查询远端得到 main 为 `4660bc5268f3b41502216895aac4a024825c4cde`，与本地 HEAD、origin/main 一致。
- 9 月 23 日 `59fdf642` 已发布 PKM 基础制作内容，包含 BeltAudio22 的 README、audio_manifest、author_audio、import_audio、prepare_reference_audio；该提交仍在 origin/main 历史中。
- 9 月 27 日 `28f221eb` 发布的是 PKM 材质、弓和手枪检视相关内容，没有包含这次尾音修复。
- `_author_rebuild.py`、`_import_rebuild_ue.py`、`BGM_FINDINGS.md` 当前均为 `??`，没有对应文件的 Git 提交历史，远端 main 目录中也没有这些文件。
- `.gitignore` 第 83 行排除 Content 二进制；第 533 行排除该 PKM 作者目录的素材，后续只放行部分文本配方。因此 WAV、uasset、导入回执留在本机是现有仓库规则；修复脚本和说明未提交则是单独的发布遗漏。

## 能造成后续退回的制作入口

已提交的 `BeltAudio22/import_audio.py` 第 15 行继续使用 `HERE/contact['wav']`，manifest 中开合盖仍为根目录的原始 `S_PKM_CoverOpen.wav` / `S_PKM_CoverClose.wav`。第 19 行 `replace_existing=True`，第 33 行保存资产。

修复后的 WAV 只由独立的 `_import_rebuild_ue.py` 接入；基础导入入口没有调用它。若照 Git 里的恢复说明只运行旧 `import_audio.py`，就会用旧音覆盖同名运行资产。当前资产内容证明这一覆盖尚未发生在本次读取的两份文件上。

工作记录也存在未清理的矛盾：BGM_FINDINGS 开头及末尾仍保留“未导入／未改动”的早期文字，中段却已记录成功导入。这会误导后续恢复和版本判断；应以导入回执与现用资产内容为准。

## 原处理范围与残留边界

当时只重建开盖、合盖各自末端的一小段背景污染声，保留撞击本体和整体时长，并非给全部换弹录音分离背景音乐。原报告明确记录拨链、拆装箱、铺链等其余片段仍含原视频背景声；当前拉栓四段 ChargeAudio35 的说明也保留了原视频环境底声的边界。

离线 PCM 对比显示修复前后总时长未缩短；最后 100 ms 的整体电平分别降低约 4.58 dB（开盖）和 1.45 dB（合盖）。这只是能量变化，不等于背景音乐的独立电平，也不能证明主观上已经无尾音。

后续应将修复配方并入正式恢复入口、清理矛盾文档并补齐文本发布记录；声音处理则先定位实际残留的具体片段。本次调查没有擅自覆盖已认可声音，也没有重新提交或推送。
