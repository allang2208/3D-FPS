# M249 插匣后回握复查（2026-11-09）

检查完成，但**没有全部通过**。正式保存状态见 `install_receipt.json`，检查结论见 `review_receipt.json`。当前保存版对应 `saved/` 的原生 UE 输出和 `Preview/M249_return_checked.mp4`；其它输出目录是过程中间版本，不能当成最终验收结果。

## 已保存的修正

- 修正了回握时上臂辅助骨跨过旋转分支而突然翻转的问题。原生 60 Hz 求值中，旧版单帧最大旋转约 176.6°；当前约 36.3°，处于连续的转腕过程，未再出现旧版的近 180° 单帧翻转。
- 肘部方向随肩腕轴连续转运，手腕按前臂的摆动与旋转分别插值；手指在最后靠近握把前预先收拢。
- 保留缩短后的回握路线，补了弹匣外侧退手和护木下方接近路径。30/45 发原有总时长、弹药提交、右手拉栓和镜头反馈不变。
- 两条侧弹匣换弹和五类握把 profile 已压缩并保存。当前七个包的哈希与保存回执一致。没有改写其它动作或原待机握姿。

## 本次检查范围和证据

通过既有 `M249ReloadReview` 后台 commandlet 加载实际保存的动作、姿态差量、关节矫正、配件和动作镜头层。覆盖 30/45 发 × 普通/空仓 × 五类握把，共 20 个组合，另加四段连续第一人称回放。

- `continuity.json`：60 Hz 骨骼旋转、位移和回握后的锁握误差。当前最大单帧腕位移约 4.98 cm；回握尾段相对当前 idle 的误差低于 0.001 cm。
- `depths_saved.json`：选定回握关键帧的原生蒙皮表面检查。先用多方向射线分类，再用绝对绕数确认内外，避免把 UE 三角面绕序方向当成穿透结论；深度取最深候选点。不是每个渲染帧的连续碰撞证明。
- `saved/receipt.json`：24 个后台求值/回放案例完成；没有启动编辑器 GUI 或 PIE，没有进行音效、装备衣袖或实际关卡验收。

## 尚未解决的项

1. **45 发弹匣空仓回握**：源时间约 2.963 s，无名指仍与弹匣相交，最大约 0.98 cm。退手路径改善不等于这个接触已消除。
2. **原厂前握把空仓落手**：源时间约 3.081 s，指尖仍与握把相交，最大约 1.33 cm。曾尝试强制从下方对接，但造成更大的腕位移峰值，已撤掉该强制对接。
3. **通用前握把原待机抓握**：垂直、侧倾、棱镜、斜角四类目标握姿本身存在约 0.50–1.26 cm 的指节嵌入，斜角最大。回握结束精确交给当前 idle，也会继承这一问题。本轮没有把未经完整适配的刚性偏移写入这组基础握姿。

因此当前结论是：旋转连续性和结束衔接已修正，接触质量仍有明确未通过项，不能宣称所有穿模和握姿均已修复。

## Archive update — 2026-11-10

Superseded trial captures/previews were moved to `trash/M24920261109/SourceAssets/M249Orpind20261107/ReturnReview24/`. See `Docs/Publication/M24920261109/archive-summary.json` and the local trash manifest for exact paths and verified hashes. Active authoring dependencies and saved evidence remain in this directory; historical preview scripts are not a current installation route.
