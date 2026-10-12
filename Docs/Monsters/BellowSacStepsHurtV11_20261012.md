# 鼓囊 M-09 脚步与受击声音 V11

用户要求补充脚步和受击声，延续 V10 湿润组织、低沉囊体共鸣风格，由用户自行测试。

## 制作和接入

| 事件 | 音源 | 触发 |
| --- | --- | --- |
| FootstepA–D | 四段 0.24 / 0.26 / 0.25 / 0.28 秒湿肉足垫和低沉承重声 | 从现有四足动画 GaitPhase 的落脚相位触发；空间位置使用对应足骨投影到 CharacterMovement 的可行走支撑面 |
| HurtA–C | 三段 0.27 / 0.31 / 0.34 秒收紧喉腔、囊体共鸣和短促湿肉冲击 | 沿既有 TakeDamage 扣血结果触发，仅非致命且实际扣血大于零；服务端最多每 0.42 秒发送一次声音事件 |

脚步沿 V01 制作源的腿部相位：后左 0、前左 +0.25、后右 +0.5、前右 +0.75。对应整身落脚相位与足骨：

| GaitPhase | 足骨 |
| --- | --- |
| 0 | 后左 Bone_005 |
| 0.25 | 前右 Bone_024 |
| 0.5 | 后右 Bone_011 |
| 0.75 | 前左 Bone_019 |

慢速/正常移动共享这组相位，声音读取动画真实步态时钟及动作集 phase offset，不新增第二套步长计时。起步建立相位基准；停止、攻击、受控、离地和死亡时关闭触发。超过 0.2 秒的长帧不补播积压脚步，每次更新最多播放一个刚跨越的落脚点。接地使用移动组件已有的 walkable floor，不增加足部射线或改写动画。

声音随机选择变化版本，相邻事件不重复同一段。脚步音量随速度从 0.48 到 0.76，受击由实际伤害占最大生命比例映射为 0.72–1.0，均乘原蓝图总增益（导入时保留现值 1.35）。新音源峰值分别 -5 / -4 dBFS，保留 V10 的空间单声道制作方式。

两路独立、可复用的 FootstepVoice / HurtVoice，专服不分配；本体总计五路组件。脚步最大传播约 16 米、受击约 20 米，并发组分别限制 6 / 4 路，优先剔除远声，35 ms 淡出。受击声音复用既有表现 RPC，丢弃超过 0.18 秒的迟到事件；不抢断警戒、蓄压或吐弹通道。致命命中由现有死亡声接管，死亡/销毁停止脚步与受击通道。

## 来源

复用 `CreatureAudioV10` 中已保留的三个 CC0 原料：537883 吸气怪吼、635042 血肉挤压、695999 腹腔共鸣，并叠加原创滤波气流和固定频率承重声。没有新增外部下载。

输入仍是已记录的 HQ MP3 预览，不能写成无损母带；交付为 48 kHz / 16-bit / 单声道 PCM WAV。原料副本、来源、许可记录和散列位于 `SourceAssets/BellowSacLobberMeshy20261012/StepsHurtV11/`。

## 文件与资产

- `Tools/BellowSacLobber/author_steps_hurt_v11.py`：独立制作七段声音，不重生成 V10。
- `Tools/BellowSacLobber/import_steps_hurt_v11.py`：导入七份 SoundWave、两份并发资源，以增量方式合并到原蓝图的 BellowSounds；保留 V10 八项和总增益。
- `Tools/BellowSacLobber/finalize_steps_hurt_v11.py`：更新基础 Editor DLL 后重新保存蓝图绑定。
- `Tools/BellowSacLobber/import_creature_audio_v10.py` 同步改为合并声音表，日后重导 V10 不会清空本次新增项。
- 资产目录：`/Game/Monsters/BellowSacLobber/V11/Audio`。
- 角色蓝图：`/Game/Monsters/BellowSacLobber/BP_BellowSacLobber`，继续从原 F6 怪物生成入口使用。
- 原生修改限定于 `BellowSacLobber.h/.cpp` 和 `BellowSacAudio.cpp`。

## 接入记录

七份 SoundWave、两份并发资源与原蓝图已通过现有编辑器桥保存；回执为 `StepsHurtV11/asset_receipt.json`。用户允许保存三个未保存弹药图标并正常关闭编辑器；实际编辑器日志记录三个包于 2026-10-12 21:07:25 保存并正常退出。本任务随后提交的关闭桥未连接到已退出的编辑器，未重放该操作。

原生 Editor 构建成功（22.77 s），Game 构建成功（77.98 s）；分别记录于 `Saved/BellowSacLobber20261012/build-steps-hurt-v11-editor.log` 和 `build-steps-hurt-v11-game.log`。更新基础 DLL 后，后台 commandlet 已重新保存蓝图，日志为 `finalize-steps-hurt-v11.log`，记录 `BELLOW_STEPS_HURT_V11_NATIVE_BOUND` 及 `Success - 0 error(s), 5 warning(s)`；回执 `post_native_build_blueprint_saved=true`。

未试听、未启动游戏或执行测试，交由用户通过原 F6 入口体验；本任务没有重新打开交互编辑器。
