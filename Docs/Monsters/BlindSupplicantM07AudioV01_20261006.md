# 盲祷者 M-07 音效 AudioV01（2026-10-06）

为盲祷者补齐本体音效；此前仅有墙拟态身份音与法术命中音（沿用玩家技能资产）。复用优先：肉身层取 M-10 已下载 freesound CC0 预览源，念咒/袍声/法术辉光/鳃膜全部 numpy 程序合成，未做公开渠道再搜索。

## 资产

7 个 48 kHz 单声道 WAV 在 `SourceAssets/BlindSupplicantM07Meshy20261001/AudioV01/Audio/`，导入 `/Game/Monsters/BlindSupplicantM07/Audio/AudioV1`：Idle 3.4 s 循环（腹鸣+低语诵经+鳃膜颤动）、Chase 2.3 s 循环（袍料+踱步）、Melee 0.9 s（击中峰值 0.40 s，对位经 1.30 倍率折算的 ≈0.36–0.38 s 接触）、MagicGather 2.2 s（蓄力诵经）、MagicRelease 1.0 s（0.30 s 释放爆发）、Hit 0.65 s、Death 2.2 s（0.9 s 坠落）。制作参数与逐源 CC0 记录见 `AudioV01/README.md`。

## 接入

- `M07|Audio` 7 属性 + `IdleVoice`/`ChaseVoice`（head/根，衰减覆盖 1600）。
- 新增 `BlindSupplicantM07Audio.cpp`：Tick 轮询 `ENurseState` 边沿；法术与近战分流靠新增复制字段 `AudioAttackKind`/`AudioMagicReleased`——`PrepareAttack` 与释放翻转点写入，专用服客户端同样正确分流，kind 未到先挂起 0.6 s。蓄力音挂施法掌位，释放即停。专用服务器跳过，EndPlay 全停。
- 命中音、墙拟态音入口不变；KnockedDown/GettingUp 走 Hit 已播音沿，Recovery 无声。

## 状态

脚本与源码就绪；构建/导入结果见 `AudioV01/delivery.json` 与 `asset_receipt.json`。未运行游戏、编辑器或验收测试——重点试听：Idle 诵经与墙拟态音的层叠关系、法术蓄力时长不一时的收边、Melee 0.40 s 对位实机接触。
