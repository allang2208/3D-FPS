# 201 视频原声开火音

用户指定从 [BV11xwQz5EHS](https://www.bilibili.com/video/BV11xwQz5EHS/) 的 25 秒后提取射击并接入 201。制作源位于 `SourceAssets/LMG20120260927/FireAudio01`。

从四轮连射的末发分别提取约 285 ms，保留起音和短尾音。处理低频杂音、轻度收整高频、裁切淡化并匹配四段能量，统一保留 −1 dBFS 样本峰值余量。保持原生 44.1 kHz 双声道和音高。精确视频时点、母版、处理参数和 SHA-256 均在 `provenance.json`。

UE 资产为 `/Game/Weapons/LMG201/FireAudio01/S_LMG201_Fire_01` 至 `04`。201 的普通单发和连射声库均指向独立音源，使用既有相邻不重复选择与最多六声部的短尾音重叠。既有消音声、机械音、声音类别、播放倍率和射击节拍保持原合同。

原生改动为 `FPSGAMECharacter.cpp`、`Weapons/LMG201WeaponAssets.h`。这两个文件写入后，项目 `Saved/BuildEditor/build-20260927-233829.log` 所记录的常规构建编译了 `FPSGAMECharacter.cpp`，链接基础 Editor DLL 并成功完成；非仅 Live Coding 补丁。

导入保存情况见 `import_receipt.json`，最终交付状态见 `DELIVERY.json`。本轮未主动启动 UE 编辑器、试听或运行游戏，最终听感交由用户测试。

后台导入已完成，`import_commandlet.log` 返回 `LMG201_FIRE_AUDIO_IMPORTED_SAVED 4`，进程正常结束。

音源是用户指定视频的上传混音，原音轨及衍生文件保留本机；未建立公开再分发许可，不公开提交音频或 uasset。
