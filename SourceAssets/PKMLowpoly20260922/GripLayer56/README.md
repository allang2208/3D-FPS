# GripLayer56：握把运行时层

说明文档：`Docs/Weapons/grip-layer56-20260930.md`。运行时代码：`Source/FPSGAME/Weapons/GripPoseLayer.*`。

| 文件 | 作用 |
| --- | --- |
| `collect.py` | 只读采集 ArmHinge55 的 140 条在用动作（组件空间 `WPN_root`、左臂 8 骨、左手指），输出到 `Inputs/`。可续采。 |
| `run_collect.ps1` | 采集调度：没有 FPSGAME 编辑器时用后台 commandlet（`run_headless.ps1`）；编辑器开着且不在 PIE 时分批走桥，每批约 15 秒；其他情况等待。FPSGAME-mp 不计。 |
| `evaluate.py` | 握把层参考算法，C++ 按它逐步移植。和作者做的握把 clip 逐帧对比。 |
| `grip_contact.py` | 统计基础手偏离握持位的范围，用来定权重阈值。 |
| `summarize.py` | 输出汇总表（按动作取五类握把中的最大值）。 |
| `study_rate.json` / `evaluate_rate.log` | 当前算法的结果：阈值 3.5–5.5 cm、32–48°，每秒最多变化 4。 |
| `evaluate_v1.py` / `study_v1.json` | 第一轮（只移手）的记录，已否决。 |

重跑：

```
python -X utf8 evaluate.py --pos 3.5,5.5 --ang 32,48 --rate 4 --out study_rate.json
python -X utf8 summarize.py study_rate.json
```

改动 `GripPoseLayer.cpp` 里的常量时，`evaluate.py` 要同步修改，反之亦然。
