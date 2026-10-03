# M-07 V26：按百目原始参考重做整臂横扫

日期：2026-10-03。用户反馈 V25 横扫整条手臂扭曲，要求参照百目的原参考源，让整臂与身体配合动作。

后续用户否定本版：整臂仍扭曲、穿入身体、打击感弱。正式横扫已由 [V27 动作库完整挥击](BlindSupplicantM07LibrarySweepV27.md) 替换。下文保留制作历史，不作为认可模板。

两段动画已通过后台 commandlet 实际导入并保存，现有 `BP_BlindSupplicantM07` 的 `MeleeLeftClip`、`MeleeRightClip`、`AttackClip` 已切换至 V26。未启动编辑器、游戏、渲染或测试，动作质量仍待用户体验。

## 参考与处理

- 实际供体：`/Game/ParagonRampage/Characters/Heroes/Rampage/Animations/Attack_Biped_Melee_A`。使用百目本地保留的 60 Hz 肩、肘、腕、骨盆与胸部数据，以及 `Idle_Biped` 首帧校准；参考百目 `RampageV8/author_rampage.py` 的整臂骨段方法。
- V25 对上下臂分别混合目标旋转，又给前臂叠加最多 80° 的转掌，腕掌再单独追目标。V26 取消这条处理链，以当前 M07 V20 自然待机校准上臂方向和肘平面，整臂共用肩部旋转与单一肘铰链；前臂不再额外轴向扭转。
- 百目有独立的上臂／前臂 twist 和关节支撑骨。M07 当前 83 骨参考没有这些辅助骨，因此不照搬百目的轴向补偿。上臂肘平面相对最小摆动的附加旋转平滑限幅 28°；腕部仅接收供体相对前臂的剩余变化，摆动最多 18°、轴转最多 8°，不强制掌心始终朝某个世界方向。
- 保留供体的蓄力、快速扫过、后随与收势；原本伸到脑后的起手适配为身体前侧起势。反手采用正确的镜像向量／旋转换算，肘平面法线按轴向向量处理。
- 骨盆先转，胸肩随后转动，五节脊柱分担变化；按 M07 长肢比例收小供体身体大转身，骨盆／胸肩偏航分别平滑限幅 15°／32°。另一侧手臂作小幅配重，双腿保持支撑，头部保留部分反向稳定。

## 已保存资产与时序

| 动作 | 资产目录下名称 | 时长 | 命中中心 |
| --- | --- | --- | --- |
| 左横扫 | `A_M07_SweepLeft` | 1.40 秒 | 0.60 秒 |
| 右横扫 | `A_M07_SweepRight` | 1.50 秒 | 0.6667 秒 |

目录：`/Game/Monsters/BlindSupplicantM07/AnimationsReferenceChainSweepV26`。播放倍率 1.0，接触窗口 0.14 秒；保留现有伤害、距离及爪部接触处理。供体时序非线性映射到以上制作时间。

保留 V25 移动、V24 施法与前移蓄积、V20 待机，以及当前显示模型、权重、83 骨参考和布料。V25 两段横扫已被替换，不作为认可模板。组织避让继续在新动作中离线烘焙，沿用已有有限运行时组织修正；V26 不增加运行时 IK、碰撞或逐帧网格处理，不声称实测帧率收益。

## 制作与保存记录

- 制作脚本：`Tools/BlindSupplicantM07/author_reference_chain_sweep_v26.py`
- 导入脚本：`Tools/BlindSupplicantM07/import_reference_chain_sweep_v26.py`
- 可编辑制作源与 FBX：`SourceAssets/BlindSupplicantM07Meshy20261001/ReferenceChainSweepV26/Motion/`
- 制作清单：该目录下 `reference_chain_sweep_manifest_v26.json`
- 实际保存回执：`SourceAssets/BlindSupplicantM07Meshy20261001/ReferenceChainSweepV26/ue_reference_chain_sweep_delivery_v26.json`
- 导入前原蓝图文件保存在 `ReferenceChainSweepV26/Before/`，旧动画资产保留。
- 后台导入日志：`Saved/Logs/M07Import-20261003-133201.log`

本轮属于动画资产替换，没有修改原生代码。同时在已有编辑器退出后补齐 V25 延后的 Editor DLL 构建，结果 `Succeeded`，日志 `Saved/BuildEditor/m07-FPSGAMEEditor-20261003-133654.log`。未执行自测、截图、渲染、PIE 或性能测量；保存与构建成功只代表制作接入完成，不代表视觉验收。
