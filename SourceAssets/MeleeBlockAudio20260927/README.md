# 近战格挡受击音效

来源：用户提供 D:/FPS3D/资产/音效/格挡.mp3。仅记录为用户提供素材，未推定额外再分发许可。
原始音频保留为 source.mp3。

裁剪：01 为原片 0.00–0.68 秒；02 为 0.86–1.50 秒。48kHz、16bit PCM、保留立体声，末尾各 30ms 淡出。源音量保留。
接入：RuneSwordComponent 装备时缓存两段 SoundWave，GuardFeedback(false) 在格挡实际受击时等概率选择一段，以原有 0.85 音量及 1.0 音高播放；完美格挡 Parry 分支保持原音效。格挡举起/放下不播放本音效。
资产路径：/Game/Audio/MeleeBlock20260927/S_MeleeBlock_01、S_MeleeBlock_02。目录加入 AlwaysCook。

交付：两段 SoundWave 已由后台 commandlet 导入并保存，见 import.log；正式 Editor DLL 构建成功，日志 Saved/BuildEditor/build-20260927-181508.log（Result: Succeeded）。未启动编辑器或游戏试听测试。
