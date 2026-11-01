# 疾雷举杖引雷 V3

用户随后提供游戏截图否定了此版右肘姿态。动作已由 [V4](../JiLeiMotionV4/README.md) 替代；本目录蓝白闪电继续使用。以下仅为 V3 历史制作记录，不代表动作获认可。

2026-10-29，按用户反馈将 V2 的平举改为明确的右上举锤，环绕电弧改为蓝白色并增强。

## 动作制作

- 左手手指在作者时间约 0.11 秒内松开，约 0.30 秒自然下落。右手从约 0.14 秒开始抬升，约 1.34 秒到达引雷姿势；运行时仍按原重击蓄力进度映射。
- 满蓄力右手握点比 V2 抬高 13.5 厘米，锤柄朝右上方倾斜。肩、肘、腕共同参与求解，保留右手原握点和手指包握，使用连续肘平面与前臂辅助骨分摊旋转。
- 姿态制作时将锤头可见范围纳入目标。尚未进行游戏内画面确认。
- 释放保留短促缓冲，再连续放下，左手后段重新扶柄。两条片段仍为 2 秒蓄力、约 0.72 秒释放，240 Hz 作者采样。
- 制作源：`author_motion.py`、`JiLeiMotionV3_Editable.blend`、`Export/`。`motion.json` 是作者求解参数，不是运行时测试报告。

## 环绕闪电

- 专用材质 `/Game/Weapons/ThunderGodHammer20261028/JiLeiSeatV1/M_JiLei_BlueWhiteLightning`：蓝色电弧外缘与蓝白高亮区域。
- 4 条粗主弧绕双侧锤头，2 条横向电弧穿插，2 条延伸至锤颈；扩大环绕范围，提高粗细和闪动强度，亮度随蓄力提高。
- 使用已有 8 弧拓扑、30 Hz 形状更新及组件池。动态组件只在疾雷蓄力时显示，其他锤座使用原材质。
- C++ 接入位于 `Source/FPSGAME/Production/ProductionStormDriveLightning.cpp`；保留同文件已并入的武器切换期间网格有效性处理。

## 交付记录

`import_receipt.json` 记录动画保存；`lightning-receipt.json` 记录专用材质保存；`Backups/` 保留覆盖前的动画包。`build.log` 为后台 `FPSGAMEEditor Win64 Development` 构建结果，Succeeded / Target is up to date。现有编辑器退出后使用无界面 commandlet 导入，没有重启可视编辑器。

未运行游戏、PIE、截图或动作验收。伤害、消耗、范围、眩晕、感电以及贯雷投掷召回不在本次修改范围内，实际表现由用户测试。
