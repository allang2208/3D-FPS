# 战锤砸地音效

用户指定 `D:/FPS3D/资产/音效/砸地.mp3`，用于双手锤重击和冲刺攻击砸地。两种动作在原有接触时刻生成同一个 `AWarhammerShockwave`，因此只替换该冲击波的一次性落地声音，不改普通三连击或其他武器的通用命中音。

声音资产：`/Game/Weapons/SteelWarhammer20261014/GroundImpactAudioV1/S_Warhammer_GroundImpact`。保留原始 48 kHz 双声道、音高和完整尾音；删除 19.4375 ms 开头近静音，保留 2 ms 起音余量，输出 0.7245625 秒 PCM。无 EQ、变速或增益调整，运行时音量和音高倍率均为 1。沿用原命中音的声音类别及衰减设置。

冲击波类预载并持有声音，避免在冲击波 Tick 中同步加载。原有 `bSoundPlayed` 保证每次落地只播放一次，客户端沿用复制冲击波的播放入口，专用服务器不播放。`PlaySoundAtLocation` 的尾音不依附冲击波组件，因此冲击波消退不会截断它。

制作源、原始文件副本、导入脚本、导入回执和构建回执位于 `SourceAssets/SteelWarhammer20261014/GroundImpactAudioV1/`。音源由用户提供，原权利保留，未推定可公开再分发。

本轮不试听、不运行游戏验收；原有游戏预览按此前授权正常结束，未保存资产为空后正常退出编辑器，用于正式 DLL 构建。构建后不自动启动编辑器。

交付状态：声音已导入并保存；正式 `FPSGAMEEditor` 构建成功，基础 Editor DLL 已更新。未进行试听或实机测试。
