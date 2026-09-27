# 弓拉弓／放箭改用参考视频原声（2026-09-26）

用户再次否定上一版声音并指定参考视频原声。本轮重做拉弓与放箭两段；同时保留腰射朝向修正。

## 已发现的差异

上一版把 0.67 秒的拉弓片段离线拉长到 1.4 秒，转成单声道并做了频谱降噪、逐段峰值放大。放箭只取 0.166 秒；播放端又随拉距改变放箭音高。上述改动会改变原混音的速度、音色、力度和尾音，不能作为保留视频原声的版本。

本轮只读保存档案，两槽都已引用版本 19 的 AudioVideo20260926 资产。读取时没有运行的游戏世界，未启动游戏或试听。

## 新制作

来源：[用户视频 BV1jGdDBkEkc](https://www.bilibili.com/video/BV1jGdDBkEkc/)。

- 拉弓：37.450–38.150 秒，0.7 秒原速双声道。
- 放箭：36.772–37.205 秒，0.433 秒，保留原速与完整该段尾音。
- 仅做切口短淡变，不降噪、不转单声道、不拉伸、不逐段放大，不生成替代声；两段原始相对音量保持一致。
- 这是视频原混音摘录，可能包含原视频环境声，并非独立游戏音效母带。

新增 `bow_audio_original_speed` 开关。启用时两段原声以音高／速率 1 和共同音量倍率 0.6 播放，取消拉弓时长变调及放箭拉距变调。拉弓声原速播完即结束，不循环填满后续拉弓时段；提前松手、取消和换武器仍停止该声部。

原生源码：`BowWeaponComponent.h/.cpp`。作者目录：`SourceAssets/BowVideoAudioDirect20260926/`。备份目录：`Saved/BowVideoAudioDirect20260926/Before/`。

## 交付状态

两个 WAV 与原速播放源码已落盘，两个 SoundWave 已通过已有编辑器和 MCP 批次互斥完成导入保存。回执为 `SourceAssets/BowVideoAudioDirect20260926/import-receipt.json`，两项均为 `saved: true`。目录已切换为 `AudioVideoDirect20260926`，原速开关为 1，表现版本升至 20，新音频目录已加入打包配置；取箭与搭弦两段继续保留原引用。

首轮原生构建曾被其他模块 `SmeltingCasting.cpp` 的局部变量遮蔽错误中断；该文件后续已修正。本轮原速播放与腰射朝向源码已随 ADS 调整完成后台构建，`FPSGAMEEditor Win64 Development` 返回 `Result: Succeeded`，记录为 `Saved/BowAudioStillNorth20260926/build-bow-ads-clearance-20260926.log`。当前表现版本为 21（ADS 摆位更新），保留本轮原速开关及两段资产引用。

后台流水线记录：`Saved/BowVideoAudioDirect20260926/pipeline-console.log`。先前因编辑器编译占用而未发现 Python 节点的导入请求没有发出；当前记录已明确成功保存并接入。本轮未主动关闭编辑器、运行游戏、试听或测试。

原音频、衍生 WAV 和 SoundWave 为用户指定的本机视频摘录，未提供资产再分发许可，不继承旧库 CC0 许可。本轮未上传或提交音频。
