# M24 两款改造枪托快速近战：手部接触修订

范围：玄脊碳纤维枪托、骨架狙击枪托；独立默认、平衡、幻影、防滑后握把及 5／10 发弹匣。原厂一体枪托的 base／mag10 Profile 不修改。

当前两款枪托共用 `skeleton_*` 八份 Profile。原动作中段按旧骨架枪托后部包握；更换碳纤维外形后掌根与新表面发生明显相交。此前 R3 的过渡也有个别指尖在闭合时穿入后握把。

本次保留原来的松手、换握、枪托前送及回握结构，将发力握点重新配准到两款枪托共有的前颈区域。按当前 V9 蒙皮、关节矫正及实际导出几何拟合掌根和五指；右臂以原生骨长跟随，枪体及左臂轨道保留。回握末段平滑交回当前家族的真实 idle 握点，局部修正相交手指的闭合时机。源动作仍为 0.9 秒，命中仍为 0.25 秒。

## 制作与接入

1. `run.ps1 -Script read_inputs.py`：在现有 UE 互斥下读取当前 idle／近战差量和基础序列，导出实际两款枪托的 Native／Advanced 装配与四款后握把。
2. 后台 Blender 5.1：依次执行 `fit_contact.py`、`author.py`、`refine_return.py`，随后执行 `refine_return.py -- --dense-default` 和 `refine_return.py -- --dense-default --thumb-spread` 对默认握把进行密集指尖及拇指外展修订。产出 `quick_melee_patch.json.gz`。
3. `save_editable.py`：保存原生 V9 骨架、蒙皮、JC 修形关键帧和当前装配到 `M24_TwoStock_QuickMelee_Editable.blend`。默认显示骨架枪托；切换 `M24_Advanced_carbon` 并隐藏 `M24_Advanced_stock` 可查看碳纤维版本。
4. `run.ps1 -Script publish.py`：只合并八份 Profile 的 quick_melee 条目，保留现场其他角色。未保存资产及变化的 idle／近战输入会阻止覆盖；实际写入前备份到 `BeforePublish/`，保存结果记录在 `publish_receipt.json`。

## 本次请求的检查

`review.py` 对当前 V9 皮肤及动态关节修形进行离线采样。接触判断按实际独立部件执行，使用包围盒、三方向射线奇偶、射线命中面朝向和最近三角面侧别共同判断；避免把多个开口壳合并后的射线误判当作穿模。

采样：120 Hz，手部顶点每 5 个取 1 个。该结果不能证明所有三角面和连续时刻都没有相交。原动作初末帧已有的 idle 贴合误差与本次中段修订分别记录；不以移动整个枪体、改手指长度或隐藏手部来消除读数。

`preview.py --saved --motion` 从正式保存的 Profile 导出源模型慢放。它是后台 Blender 的姿态／接触预览，不是 UE 游戏录像；不代表运行时相机、衣袖或联机验收。本次不启动 UE 编辑器或游戏，不改 C++，无需原生构建。

最终局部结果：主要碳纤维枪托掌根相交明显下降；本次 120 Hz、手部顶点每 5 个取 1 个的整体最大值由约 13.6 mm 降到约 2.8 mm。剩余最大值属于原机匣骨架枪托已有的默认 idle 拇指贴合，其起止姿势仍保留；少量其他过渡采样约为 1.1–1.3 mm，不宣称全程零相交。回握拟合会随候选手指变化重新计算 JC 修形权重，避免用冻结修形的结果代替最终皮肤。

当前资产已保存与否以 `publish_receipt.json` 的 complete 和 saved 为准；离线测量结果见 `contact_review.json`。
