# 钢制头盔第一人称黑色蒙边

按用户指定的方向，将锁子甲配套钢制头盔的第一人称内衬图改为纯黑蒙边、柔化开口边缘和轻微惯性晃动。外部头盔模型继续使用 CrownRefine20261020。

## 视觉与动作

- 使用 UI 半透明材质绘制全屏黑框，透明开口为圆角横向窗口。
- 按用户追加要求将上下总视野拓宽 50%：清晰开口高度由屏幕的 31.8% 增至 47.7%，相对原中心上下对称扩展；宽度仍为 90%，中心高度仍为 50.675%。不修改摄像机 FOV。
- 从开口向外，以屏幕高度 2.5% 的宽度平滑过渡到不透明黑色；中央视野不叠加亮度或染色。
- 开口圆角和羽化按屏幕纵向像素比例计算，材质接收实际视口宽高比。
- 继续读取最终镜头的走跑、后坐力、受击和相机震动反馈，并加入少量转头惯性。使用 7 Hz 临界阻尼回位。
- 位移上限为屏幕宽度的 1.2%、高度的 2%，旋转上限为 0.9 度。只移动蒙边，不施加额外镜头晃动。
- `fps.Helmet.Motion` 控制晃动强度，范围 0–1。新黑框为纯黑；旧纹理的 `fps.Helmet.InteriorBrightness` 不影响新黑框。

## 接入

原有本地玩家、第一人称、存活和视角目标条件继续控制显示，层级保持 15。头部装备异步加载入口同时支持 UI 材质与原有纹理资源。材质使用每个控件独立的动态实例，无纹理采样；开口在全屏材质中移动，画面边缘持续覆盖。

资产：
`/Game/Characters/ModularOutfit20260924/SteelArmet20261019/BlackFrame20261020/M_SteelArmet_SoftBlackFrame`

制作脚本：

- `Tools/SteelArmet/black_frame.hlsl`
- `Tools/SteelArmet/save_black_frame.py`
- `Tools/SteelArmet/publish_black_frame.py`

构建完成后，发布脚本只修改 `player_body.json` 中 `head_equipment.ue_steel_armet.first_person_overlay`。不会覆盖法袍袖子、手腕、裤靴或头盔外部模型配置。

## 交付状态

源码、材质和配置均已落盘，Editor/Game 两个目标构建成功。

- 材质保存：`SourceAssets/SteelArmet20261019/black-frame-save-01.log`，保存回执为 `BlackFrame20261020/saved_assets.json`。
- 构建：`SourceAssets/SteelArmet20261019/black-frame-build-01-FPSGAMEEditor.log`、`black-frame-build-01-FPSGAME.log`。
- 配置发布：`SourceAssets/SteelArmet20261019/BlackFrame20261020/published.json`。

上下视野扩大 50% 的追加调整已保存到同一材质，现有配置直接使用。保存日志为 `SourceAssets/SteelArmet20261019/black-frame-height150-save-01.log`，`saved_assets.json` 中高度为 0.477；本次只改材质参数，无需重新构建 C++。

未打开编辑器、运行游戏或进行视觉验收，由用户试玩。
