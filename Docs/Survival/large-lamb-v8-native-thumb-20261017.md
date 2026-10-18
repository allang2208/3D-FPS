# 大羊排 V8 手部与原生关节抓握修正

本轮用户确认问题贯穿整个握持过程，尤其是拇指。目标为双手进食 `roasted_large_lamb`。

## 当前手模身份

`FPSPotionUseComponent::TryBegin` 在双手食物分支选择 `FallbackHands`，由 `DefaultGame.ini` 的 Traversal `ArmsMesh` 加载：

`/Game/Characters/ModularOutfit20260924/BarePalmV7/Traversal/SK_Traversal_BareArmsV7`

V8 是在原资产上进行的表面升级，名称仍保留 V7。实际包的 SHA-256 为 `4ad9b781e0fba16a77ca085c27bae2a8f17d238240391847f77cf8baa0686a7b`，与 `BareHandAudit20261016/Installed/0fc712f32c7e.json` 的 V8 保存回执完全一致。本轮没有替换手模、骨架或蒙皮；确认当前磁盘资产确实为 V8，不把资产名当作内容版本。

## 姿态原因与修正

上一轮 `preserve_native_roll` 用最短弧将每节拇指朝向掌坐标下的目标方向，减少了轴向扭转，但不能保证中节、末节只绕各自原生弯曲轴转动。当前数据中，握持时两手末节仍带约 12–15 度的离轴旋转；包含收拢/松开的 13 个采样阶段最高为 21.71 度。这是骨骼旋转向量相对模型原生 Y 轴的指标，不是人体医学关节角。

为 `FPotionDigitPose` 增加可选 `local_rotations`，数组为三节骨骼各自相对于原生局部参考姿态的 `[x,y,z,w]` 四元数。在已有父骨和原生局部变换后施加旋转，以闭合权重从单位四元数连续插值；没有该字段的动作沿用原逻辑。只给大羊排左右拇指写入该字段。

- 左拇指根：原生 Y 8°、Z 4°；中节 Y 24°；末节 Y 22.5°。
- 右拇指根：原生 Y −19°、Z 3.5°；中节 Y 45°；末节 Y 35°。
- 根部负责对掌，中节与末节只绕各自原生 Y 轴弯曲，不再靠侧折追逐掌坐标目标。
- 数据同步 `potion_use_motion.json`、`FoodGrip20261003/large_lamb_natural_grasp.json` 和 `LargeLamb20261014/grip_profile.json`，正常重制入口会保留本轮姿态。

保留左右掌向、握点、其他四指、羊排模型及轨迹、骨段平移与长度、6 秒动作和 4.65 秒接触时钟。没有变动其他消耗品数据。

## 本轮证据与边界

任务源位于 `SourceAssets/LambGripV8_20261017`。

- `diagnosis_before.json`：实际包与 V8 回执散列、原拇指局部旋转。
- `pose_model.py`：当前运行姿态的离线求值，已包含上一轮原生 roll 分支及本轮局部旋转分支；没有再用旧的忽略 roll 的离线结果代替当前姿态。
- `author_thumb.py`、`thumb_fit.json`：使用当前 V8 混合蒙皮及真实羊排三角表面制作左右独立姿态。
- `saved_pose_review.json`：13 阶段复查；修正后中节/末节离轴量约 0.000012°，骨段长度变化约 0.000002 cm，均为浮点精度量级。
- 握持阶段拇指局部最大嵌入约左 0.21 mm、右 0.31 mm；仍有局部接触嵌入，不能声称零穿模。指腹接触和实际游戏观感不同，最终由用户确认。
- `final_present*.png` / `final_bite*.png` 及同名 Blend：保存数据生成的离线对照，使用简化显示材质，不是 UE 截图或材质验收。
- `Before` 保留本次准确文件修改前副本；没有回退其他并行更改。

本轮 C++ 值成员布局变化已完成常规 Editor 与 Game 构建，两目标均为 `Succeeded`。回执在 `SourceAssets/LambGripV8_20261017/20261017-002704/result.json`，实际 DLL、EXE 与源文件散列在 `delivery.json`。没有启动编辑器界面、游戏或 PIE，没有进行游戏内视觉验收。
