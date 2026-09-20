# 矿镐攻击第四版：沿视线举柄与左臂伸展

用户指出第三版仍有明显直角折肘，举起时镐柄应接近与视线平行。本版在第三版可编辑源上继续制作，改变蓄势的工具旋转和肩肘关系。

## 姿态制作

- 握柄中点的举顶高度由 +0.32 m 改为 +0.43 m；柄轴相对竖直的后转角由 −25° 改为 −82°，即长柄与视线所在直线约差 8°。镐头向后，柄尾向前，双手在前上方支撑。
- 初次举起角度为 −68°，随后继续后转到 −82° 蓄势。抬举和下砸贝塞尔控制姿态同步修改，避免只改变顶点造成过渡脱节。
- 肩部上提量从 0.19 m 收到 0.155 m。左手伸到较远的前上方，减少通过耸肩维持折肘的补偿。
- 左手环绕柄轴的蓄势握向改为 −85°；左肘举顶引导改为 `[0.60, -0.25, -0.80]`，使肘部位于伸展前臂下方。制作中的骨架拟合，左肘内角约由抬举的 146° 过渡到顶点的 150°，保留弯曲而不锁死。右手保留独立的握向和肘部引导，并随共同工具姿态重算手臂。
- 左腕的参考轴夹角在上述最终引导下约为抬举 13°、顶点 23°。这些数字仅用于骨架姿态制作，不是医学关节角或视觉验收结论。
- 保留第三版上臂轴向旋转分担和前臂辅助骨处理，以及手指原有局部抓握姿态。

## 时间合同与文件

继续采用总时长 1.16 s、0.32 s 完成初次举起、0.47 s 释放、0.60 s 接触的分段节奏；抬举使用缓动，下砸使用加速曲线。命中后完整姿态保持 0.20 s，再抽回。命中、挥空终点分别保留第三版的 Z = −0.40 m、−0.445 m。

- 可编辑源：`SourceAssets/PickaxeSightline20260919/Pickaxe_Sightline_Editable.blend`。
- 制作入口和参数：同目录 `author_attack.py`、`motion.json`。
- 姿态拟合草案：同目录 `fit_overhead.py`、`overhead_pose_fit.json`、`overhead_plane_fit.json`。前者记录原肘引导下的握向选择，后者包含最终采用的肘引导；属于制作过程资料。
- 导出：同目录 `Export/A_RusticPickaxe_Swing.fbx`、`Export/A_RusticPickaxe_HitRecover.fbx`，300 Hz。
- 正式导入入口：`Tools/Production/import_pickaxe_overhead.py`，完整矿镐重导入也使用同一入口。
- 正式资产：`/Game/Items/ProductionTools/RusticPickaxe20260919/A_RusticPickaxe_Swing` 和 `A_RusticPickaxe_HitRecover`。

本版未修改 C++。制作、导出及正式动画替换均已完成。用户停止 PIE 后，已在当前 FPSGAME 编辑器内导入并保存 Swing、HitRecover 两段动画，无需关闭或重启编辑器。成功回执为本版 `import_receipt.json` 和 `editor_import_response.json`。未追加实机测试、预览或渲染，最终肘部轮廓和动作手感交由用户测试。
