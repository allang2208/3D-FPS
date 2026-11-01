# GuanLei user-selected recall audio V4

用户指定两份 MP3，作为最终召回划空和接住声。英文原始素材保存于 `Source/`：

- `GuanLei_Recall_Whoosh.mp3` ← `D:/FPS3D/资产/音效/划空声.mp3`
- `GuanLei_Catch_Blunt.mp3` ← `D:/FPS3D/资产/音效/接住钝器.mp3`

`Audio/S_GuanLei_RecallAirLoop.wav` 和 `Audio/S_GuanLei_RecallCatch.wav` 为 UE 导入素材。48 kHz PCM16，保持原音高、原声道和音色；仅去除首尾近静音、1 ms 边缘处理及必要的防削波增益。用户原文件保留。

UE 资产沿用英文路径 `/Game/Weapons/ThunderGodHammer20261028/RecallAudioV1/`，替换相应两个 SoundWave。划空声设置循环，播放端保持 1.0 音高并按素材实际时长定位，到手时停止；接住声在真实掌心接触时单独播放一次，并保留完整尾音。金属嗡鸣层沿用原配置。

制作：`prepare_audio.py`；导入：`publish_assets.ps1`。源散列及参数见 `audio_manifest.json`，资产保存见 `import_receipt.json`。当前恢复入口为本目录，V1–V3 是历史。源码／当前编辑器热更新／常规 DLL 构建与游戏测试分别记录，不混称完成。没有进行游戏测试。
