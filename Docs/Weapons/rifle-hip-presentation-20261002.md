# 步枪统一基准与逐枪腰射展示偏移（2026-10-02）

用户要求按本轮排查建议调整腰射构图，恢复部分枪械被画面下缘裁掉的机匣、枪机及导轨细节。

## 本轮配置

共同 M4 基准、枪轴与上方向解算继续使用 `RifleHipFraming`。在共同右手腕基准上增加逐武器的相机空间展示偏移，单位为厘米，相机 X 正方向为前方。

| 武器 | 相对统一结果前移 |
| --- | ---: |
| M4 | 0 cm |
| HK416 | 0 cm |
| QBZ191 | 5 cm |
| M16A2 | 5 cm |
| AKM | 9 cm |
| A762 | 9 cm |
| ASH-12 | 8 cm |
| SVD | 10 cm |

数值依据为本轮已保存基础待机的只读位置比较，以及 A762 源几何视锥计算：六把枪的初版统一结果相对原构图后退约 5–10 cm。A762 前移 9 cm 的源投影能恢复接近原构图的机匣细节范围。这是本轮制作值；没有将源投影当作游戏画面验收。原始排查记录位于 `Saved/RifleHipAssessment20261002/assessment.md`、`framing_comparison.json`、`a762_part_projection.json`。

## 接入与动作合同

只修改 `Source/FPSGAME/Weapons/RifleHipFraming.cpp`，新增按武器定义选择的 `PresentationOffset()`。偏移在换枪的 `Initialize()` 中加入 `TargetHand` 一次，`SelectIdle()` 按当前基础待机及握把 profile 重新求解最终位置。每次重新求解从目标与姿态直接计算，不累加旧展示位置。

整枪、双臂及已有挂点作为同一组件刚体前移。原模型比例、手部相对接触、统一枪轴与上方向、基础/变体动画和原动作空间沿用现有实现；没有修改类/结构体布局或资产。

所有现有 `RifleHipFraming.Location()` 调用直接取得包含该枪展示偏移的最终腰射位置：装备从此位置开始，换弹/检视/快速近战沿原动作权重和既定收势窗口交回该位置。ADS 目标继续由独立瞄点、上方向和眼距标定，腰射与 ADS 按既有权重过渡，展示偏移不叠入 ADS。

此规则覆盖[初版统一腰射构图](rifle-hip-standard-20260930.md)中“所有枪右手腕深度完全相同”的展示约束。开发基准与接口仍共用，实际展示深度允许按枪型不同。后续构图调参集中修改这张偏移表，不在动画源或各状态分支重复加偏移。

## 文件与交付

修改前工作区快照位于 `SourceAssets/RifleHipPresentation20261002/Before`，只作追溯，不应整文件回滚覆盖并行工作。

源码和说明已落盘，编译状态以本轮 `SourceAssets/RifleHipPresentation20261002/build_receipt.json` 为准。编辑时已有编辑器运行；提交构建时其进程已退出，故使用后台常规 Editor 模块构建。没有主动启动、关闭或重启编辑器。

后台 `FPSGAMEEditor Win64 Development -Module=FPSGAME` 构建成功，UBT 总执行时间 25.65 秒，包含本次 `RifleHipFraming.cpp` 编译与基础 `Binaries/Win64/UnrealEditor-FPSGAME.dll` 链接保存。日志为 `Saved/BuildEditor/rifle-hip-presentation-20261002.log`。本轮没有执行 Live Coding，预备的 `compile_live.json` 仅保留为已有编辑器运行时的备用请求。

未启动游戏或 PIE，未执行运行测试、截图、渲染或验收。最终构图、手臂表现与开镜衔接由用户测试。
