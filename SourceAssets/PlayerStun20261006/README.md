# 玩家眩晕与受击镜头（2026-10-06）

本地库有 Paragon Khaimera / Sparrow 的眩晕动作，以及已留存许可的 Mesh2Motion `Dizzy`。本次采用后者的 CC0 全身动作，不复用怪物目标骨架或第一人称手部动画。

来源和许可记录：`SourceAssets/HumanoidStun20260926/source_manifest.json`、同目录的 `LICENSE-CC0.MD`。原始来源为 Mesh2Motion `human-addon-animations.glb` 的 Dizzy，记录版本 `2d3d1ff03247d9e7e830d1ae375653da4e2146e2`。

制作链：`Tools/PlayerBody/prepare_stun20261006.py` → 本目录 `author_stun.py` → `Tools/PlayerBody/save_stun20261006.py`。原始动作重定向到 Jason，骨长和缩放保持原生参考；用旋转切空间的周期拟合保留失衡节奏并闭合循环，适当收敛躯干、头颈幅度。保存回执在 `assets-saved.json`。

第三人称引用为 `Reaction.Stun.Loop`，对应 `/Game/Characters/JasonPlayer20261003/Stun20261006/Animations/J_M2M_Dizzy_Loop`。采用阻尼响应进入和退出；连续补眩晕不重置正在恢复的动作相位。持械时保留双手的局部握持关系，空手时加入供体手臂动作。腿部继续走原移动、下蹲和地面适配；正式动作可用时不再叠加旧的固定蹲落和规则摆头。

第一人称由 `FPSPlayerReactionCamera` 在最终视图叠加表现：

- 眩晕：临界阻尼缓入缓出，低频多节奏及缓慢相位变化；眩晕刷新时保持相位连续。
- 受击：从既有服务器认可的 HitSerial / HitDirection / HitStrength 获取事件，短促起震、方向性回弹和指数衰减；四个有界事件槽，合成幅度有限。
- 沿用 `CameraMotionScale` 和 `fps.Camera.Shake`；不写控制旋转，不改变原伤害、眩晕时长和瞄准组件。第三人称视角和死亡镜头不叠加这套第一人称震动。
- 不新增长驻 Tick；复用现有身体动画更新和 CalcCamera。资产沿既有身体初始化加载路径读取。

已后台制作、保存资产与接入源码；编译结果见本轮交付。遵照用户规则，未运行游戏、测试、截图或渲染验收，效果由用户实机测试。
