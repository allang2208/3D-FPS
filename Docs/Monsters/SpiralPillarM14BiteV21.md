# 螺柱 M14：探出口器、突伸与闭合撕咬 V21

2026-10-06。按用户指定的「先适当伸出口器约 0.5 秒，再用 0.2–0.3 秒快速伸至最大并闭合」重排撕咬，音效与伤害共用接触时刻。

## 动作与音效

| 阶段 | 时间 | 动作 | 音效 |
|---|---|---|---|
| 探出蓄势 | 0.00–0.50 s | 下方口器平缓伸至旧动作最大位移的 22%，嘴逐渐张开 | 轻湿组织拉伸、低声呼气 |
| 加速突伸 | 0.50–0.75 s | 后段加速，到 0.75 s 达到原有最大伸长，末端制动 | 短促上升气流 |
| 闭合咬紧 | 0.75–0.80 s | 保持最大伸长，八瓣口颌在 3 个 60 Hz 帧内向内合拢 | 咬合、低频闷击及轻螺柱碰撞重音对齐 0.80 s |
| 短促回弹 | 0.817–0.98 s | 先小幅后撤，再微回弹；咬紧后稍放松 | 湿组织挤压尾声 |
| 收嘴回稳 | 0.98–1.50 s | 平滑收回，躯干与悬挂组织错时衰减 | 渐弱湿摩擦 |

初始读取的实际蓝图使用 `A_M14_Bite_v08`（0.95 s）、`S_M14_Bite`，接触时刻 0.43 s；旧 AudioV01 配方的咬合峰值仍安排在 0.86 s。本次改为统一 0.80 s。时序唯一输入为 `Tools/SpiralPillarM14/bite_v21.json`。

制作从当前 V15 母版及其中 V08 动作继续。保留口器原有约 50.15 cm 的最大骨骼前伸位移；不以放大整身或根位移制造冲击。口颌在原张口位移方向反向收紧，随后释放，躯干和两侧囊体有轻量延迟回弹。非线性运动以 60 Hz 烘焙，帧间使用线性插值防止快速闭合时曲线过冲。

伤害仍由已有 `TickAttack` 在接触时刻采样实际 `mouth_socket`，保持单次结算。蓝图只更新 `bite_clip`、`bite_sound`、`bite_contact_seconds`；260 cm 起手距离、125 cm MouthReach、3.2 s 冷却、伤害、V15 显示网格及其他攻击保留。音效继续沿现有状态起点播放，没有增加运行时 Tick 或定时器。

## 制作与接入文件

- 动画制作：`Tools/SpiralPillarM14/author_bite_v21.py`。
- 音效制作：`Tools/SpiralPillarM14/author_bite_audio_v21.py`。
- 导入保存：`Tools/SpiralPillarM14/import_bite_v21.py`，后台入口 `Import-BiteV21.ps1`。
- 制作源：`SourceAssets/SpiralPillarM14Meshy20261004/ProductionV21/Authoring/M14_StagedBite_v21.blend`。
- 交换文件：同目录 `Exports/A_M14_Bite_v21.fbx`、`Audio/S_M14_Bite_v21.wav`。
- 目标动画：`/Game/Monsters/SpiralPillarM14/Animations/A_M14_Bite_v21`。
- 目标音效：`/Game/Monsters/SpiralPillarM14/Audio/BiteV21/S_M14_Bite_v21`。
- 原蓝图：`/Game/Monsters/SpiralPillarM14/BP_SpiralPillarM14`。

声音复用已落地 AudioV01 的 CC0 Freesound 本地 MP3 素材（467701、635042、466830），气流与螺柱碰撞层本地合成。来源路径和许可记录在 `ProductionV21/Records/audio_authoring.json`；没有新增下载或将压缩源描述成无损原录音。

动画与 WAV 已制作导出，UE 动画、音效、骨架及原蓝图已实际保存，`ProductionV21/Records/ue_revision.json` 为 `complete: true`。接入等待期间已有编辑器重新运行，入口按规则使用该进程的批次桥完成导入，未另开编辑器或 commandlet。导入前备份原蓝图及骨架至 `ProductionV21/Before`。此版本不修改原生代码，无需 C++ 构建。

依用户规则，未启动游戏、未试听、未渲染或进行运行测试，实际表现由用户体验。
