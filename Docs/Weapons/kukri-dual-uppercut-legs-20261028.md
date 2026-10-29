# 双持上挑：同步单持腿部衔接

将 2026-10-27 最新单持 `UppercutSingleLegsV1` 的骨盆、双腿、足部及腿部 twist 辅助骨，同步到 Jason、Kaitlin 的双持上挑。沿用后脚蹬地、前脚落稳、后脚跟进及错步回位的节奏。

上半身来源为当前配置实际指向的双持 `UppercutSwordLowerV1`，通过现有编辑器读取。迁移只复制骨盆与下半身子树，在 `spine_01` 补偿骨盆旋转变化，保留双持肩臂、腕部、手指与两把刀的握持关系。原双持首尾姿态保留。单持版本、第一人称和玩法不修改。

两种上挑共用 120 Hz、153 帧及相同接触时钟，无需重定时；Contact、Release 和 NativeSwordGrip 标记沿用。

两套新动画已通过已有 UE 的互斥桥保存，`assets-saved.json` 完整。通过共享配置字段事务，仅切换两处 `Kukri.FullBody.Dual.Uppercut`。

资产目录：`/Game/Characters/JasonPlayer20261003/Kukri20261024/ComboV3/{Jason|Kaitlin}/Animations/UppercutDualLegsV1/`，名称 `A_Kukri_Dual_Uppercut_SupportedLegs`。

可复制作业与回执保存在 `SourceAssets/KukriDualUppercutLegs20261028/`：`prepare.py`、`inputs.json`、`author.py`、`*-actions.json`、`authoring.json`、`save_assets.py`、`save_all.py`、`assets-saved.json`、`publish.py`、`published.json`、`delivery.json`。

本轮没有 C++ 修改，不需新增编译；没有主动启动或关闭编辑器，未运行游戏、测试、截图或渲染，观感由用户测试。未打包、提交或推送。
