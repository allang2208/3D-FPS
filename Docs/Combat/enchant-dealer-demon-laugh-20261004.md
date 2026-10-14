# 庄家高倍结算：恶魔笑声（2026-10-04）

用户要求联网寻找合适的恶魔笑声，并与高倍率特效同步播放。采用 Freesound 作者 scorpion67890 的 [Demonic Laugh](https://freesound.org/people/scorpion67890/sounds/169317/)，作者声明用自己的笑声降调制作，页面列出 1.428 秒、CC0 许可；[CC0 说明](https://creativecommons.org/publicdomain/zero/1.0/)允许修改和商用。

下载公开 HQ MP3 预览，不使用需要登录的原始 WAV 接口。素材、网页许可快照和制作源保存在 `SourceAssets/Dealer20261004/AudioV3`；`Attribution.md` 和 `provenance.json` 记录来源、散列和加工。候选取舍依据作者描述与时长，本轮不主动试听；最终音色与音量由用户判断。

## 音源制作与保存

`author_audio.py` 生成 `Masters/S_Dealer_DemonLaugh.wav`：48 kHz、单声道 PCM16、约 1.43 秒。裁去安静预卷，40 Hz 高通／9 kHz 低通、−3 dBFS 峰值余量、3 ms 淡入和 60 ms 淡出；不增加长回声拖尾。升采样不代表原素材质量恢复。

正式 SoundWave 路径 `/Game/Weapons/Dealer20261004/Audio/S_Dealer_DemonLaugh`，非循环、PCM、ForceInline。已有 `/Game/Weapons/Dealer20261004` cook 根涵盖音源，无需另设全局音频配置。独立 `AudioV3/run_install.ps1` 使用已有编辑器互斥桥或后台 commandlet；完整卡牌 `run_author.ps1` / `install_ue.py` 同步包含音源，后续恢复不会漏掉它。

## 触发与同步

`UDealerEnchantmentComponent` 沿用可靠拥有者牌组 RPC，仅 Full House／Four of a Kind／Straight Flush 结算设置一次性声音标记。其他命中、暴击、抽牌及低倍结算不播放笑声。战斗倍率、第五次有效命中结算和暴击优先选牌规则保持原实现。

音源与卡牌／火焰素材一起异步预加载，命中时不进行同步磁盘加载。首次实际定位并显示高倍 Burst 的 Tick 同时启动声音，然后清除标记，后续帧不重复播放。默认从文件起点播放；资源准备迟到时，按结果时间与音高换算采样起点，保持同一结算时间轴，已结束的片段不迟到补播。

| 结算 | 运行音量乘数 | 音高乘数 |
| --- | --- | --- |
| 葫芦 ×4 | 0.65 | 1.00 |
| 四条 ×5 | 0.75 | 0.96 |
| 同花顺 ×7 | 0.85 | 0.90 |

声音为拥有者本地 2D 音效，跟随镜头效果，无世界距离衰减；关闭 UI 声音标记，沿用游戏暂停行为。每角色最多一个笑声音部，新一轮结算停止上一轮；下一发抽牌保留上一结果及声音的剩余寿命。卸下对应附魔武器、死亡、视角离开玩家、结果结束和组件销毁时停止并释放。不新增定时器、战斗随机调用或复制音频状态。

## 交付状态

源素材及 PCM 作者输出已落盘，SoundWave 已通过后台 commandlet 实际导入并保存，`SourceAssets/Dealer20261004/AudioV3/install-receipt.json` 为 `complete=true`。Game 和 Editor 必要构建均成功，回执 `Saved/DealerLaugh20261004/delivery.json`；首次构建遇到的怪物模块编译错误随后随该模块更新解除，保留 `gameBuild-attempt1-output.log`，本任务没有修改怪物模块。未打开编辑器或游戏，未试听、测试或验收。
