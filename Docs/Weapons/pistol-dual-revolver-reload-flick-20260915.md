# 双持左轮换弹起手甩腕

2026-09-15。用户要求双持左轮换弹先有手腕甩开弹巢的动作，再向屏幕下方移动，并区分左右手方向。

## 动作调整

原 NaturalAimV3 保留了弹巢机械轨道，但枪体的表现运动使用整段换弹的归一化时间。装填一发和六发的换弹总时长不同，导致枪体甩动与固定的 0.25–0.48 s 开仓轨道错开；长换弹中尤其容易看成弹巢自行打开，再把枪推下去。

RevolverReloadFlickV6 将起手改为固定机械源时钟：0–0.16 s 反向预摆，0.16–0.32 s 快速甩腕，0.32–0.58 s 回弹和收稳。弹巢沿用 0.25–0.48 s 开仓，因此开仓发生在甩动过程中。

| 手 | 预摆 | 主甩 | 机械开仓 |
| --- | --- | --- | --- |
| 右手 | 向内小幅预摆 | 向屏幕右外侧甩腕 | 保留原左轮开合轴 |
| 左手 | 向内小幅预摆 | 向屏幕左外侧甩腕 | 保留原左轮开合轴，不镜像枪体 |

主甩侧倾 38°，配合 9° 水平转向和 2.6 cm 外移；不是只改变枪根、把手腕留在原处。沿用 NaturalAimV3 的枪柄接触和整臂求解，肩肘略微跟随甩动，握枪手与枪体始终共同移动。

非空仓逐发装填于 0.50–0.94 s 下移；空仓和速装器先保留可见退壳段，于机械源时钟 1.12–1.50 s 下移。速装器延续 3.60 → 3.85 s 的源时钟映射。到画面下方后接回原装填与收尾姿态。

## 接入范围

- 左右手各 21 个逐发装填分支和 1 个速装器分支，共 44 个动画。
- 动画路径：`/Game/Weapons/PistolDualWield20260914/DW715/{r,l}/RevolverReloadFlickV6/Animations`。
- `PistolDualWieldComponent.cpp` 将左轮的 `single_*` / `speed_*` 分支接到新目录。M1911、双持握姿、射击、奔跑以及单持左轮继续使用已有资产。
- 弹巢、弹壳、子弹、速装器的源机械轨道和所有装填/音效事件时点保留。动作长度及弹药提交仍按原分支工作。

## 可编辑源与制作结果

作者目录：`SourceAssets/PistolDualWield20260914/RevolverReloadFlickV6`。参数为 `reload_profile.json`；每只手保存独立的 `DW715_{r,l}_Dual_Editable.blend` 及 120 Hz FBX，清单为 `DW715-authoring.json`。

制作命令使用 `author_dual.py -- DW715 --revolver-reload-flick`；导入使用 `import_dual.py` 加 `-DualRevolverReloadFlickUpdate`。生产日志为 `author.log`、`import.log`、`build.log`，导入清单为 `reload-import.json`。

左右手各 22 个片段已完成导出，Blender 返回 0，记录 `DUAL_AUTHOR_COMPLETE DW715`；44 个片段已导入，UE 进程返回 0，记录 `DUAL_IMPORT_COMPLETE`。必要原生构建已完成，返回 0，UBT 为 `Result: Succeeded`。未执行实机测试、渲染预览或回归，最终动作效果交由用户测试。
