# RSH 弹巢错位与换弹机构排查

## 根因与修复

背包、装备栏、枪匠独立预览和掉落物制作使用 `InitializeWeaponVisuals(true)`。这个轻量入口在加载 RSH 私有机构姿态层之前返回，后续 `SampleRSH12Presentation` 取得空 profile，直接把 715 原动作应用到 RSH 的逆绑定网格。结果是枪体已经按 RSH 安装框架调整，弹巢、摆臂、退壳机构和弹药却沿用供体位置。

实际保存的单持、双持右手和双持左手网格均保留了正确拆分：`6_l` 弹巢、`4_l` 摆臂和独立前退壳杆、`13_l` 后退壳盘。当前 UE profile 的机构轨道与现用作者源一致。对 UE 导出的网格和压缩动作进行离线求值时，故意去掉私有层即可重现约 **3.5777°** 弹巢倾斜；恢复该层后的轴线偏差约 **0.0197°**，属于当前压缩动作采样结果。

修复位于 `Source/FPSGAME/FPSGAMECharacter.cpp` 的展示初始化分支：清理上一把展示枪的 profile，并在 RSH 分支加载本枪基础机构层；展示 ADS 使用已有共同握姿 idle。保留轻量初始化，不加载战斗、音频或特效依赖。`ColdSteelWeaponIcons.cpp` 的 RSH 缓存键增加 `mechanism=1`，使旧的动态图标和包围盒失效。

## 换弹模型与动作配合

读取当前 UE 保存的 3 套网格、3 套基础 profile 和 4 套前握把 profile，并核对现用单持、双持源动作和时间映射。没有用旧单动候选或历史导入脚本覆盖现用资产。

- 弹巢与摆臂使用实际 RSH 铰链；前退壳杆和后退壳盘仍由 `WPN_Extractor` 联动。
- 单持基础及四套前握把、双持左右手共 7 套现用 profile，逐发装填与五发装填器共 280 个入膛接触采样中，弹壳底缘与对应弹孔的最大计算误差小于 0.00013 mm，轴线误差在本计算精度下为零。这是现用作者姿态与保存 profile 的离线坐标结果，不是游戏内视觉验收。
- 当前换弹播放、弹药入膛提交、双持弹壳脱离和音效仍使用同一源时钟；快速装填器按 3.60 → 3.85 秒映射。单持私有接触层和双持既有开仓降低轨道均保留。

未发现需要重新拆分网格或重做换弹动作的证据，因此没有为展示错误修改已对齐的弹孔、手部动作、共享骨架或弹药逻辑。

## 制作与落盘记录

- 完整 Editor 目标构建成功：`Saved/BuildEditor/build-20261006-132235.log`；包含 `FPSGAMECharacter.cpp` 与 `ColdSteelWeaponIcons.cpp` 的编译和基础 DLL 链接。
- 使用修复后的生产入口重新生成 480 × 320 图标，并保存 `/Game/ColdSteelData/Icons/ue_rsh12`。生产日志及回执位于 `SourceAssets/RSH12Mechanics20261006`；可直接查看 `ue_rsh12_fixed.png`。
- 旧图标与 Texture 在 `SourceAssets/RSH12Mechanics20261006/BeforeIcon`；UE 只读导出在 `Before`；诊断数值在 `diagnosis_saved.json` 和 `reload_diagnosis.json`。

本次仅在后台读取、编译和生产图标，没有启动交互式编辑器或游戏。换弹手感、连续动作和不同装备组合仍由用户进行游戏测试。
