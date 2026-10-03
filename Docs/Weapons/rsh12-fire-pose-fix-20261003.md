# RSH-12 开火时枪械与手臂消失修复

用户反馈：开火期间整枪和手臂消失。此次只修正动画制作／导出状态，保留五发容量、单动开火与每枪拨锤、已有孔位和退壳器绑定修复。

## 原因

`RSH12Integration20261003` 的模型作者文件为静态绑定导出而将骨架设为 `REST`。后续 `author_single_action.py` 加载此文件后制作动画，却没有切回 `POSE`。

因此，虽然动作关键帧已写入，可编辑骨架和动画 FBX 的求值仍使用静态参考矩阵。实际 UE 资产的 SOURCE 和 COMPRESSED 数据均显示，所有被读取的开火时刻都保持同一绑定姿态：例如右手回到约 `(47.77, -15.04, -58.11) cm`，枪根回到约 `(5.77, -14.37, -9.84) cm`。原 715 待机右手约为 `(-1.04, 27.05, -16.65) cm`。这种位置切换使视模离开第一人称画面。原始读取记录为 `SourceAssets/RSH12FireFix20261003/installed_before.json` 和 `blender_before.json`。

## 制作与接入

- `SourceAssets/RSH12SingleAction20261003/author_single_action.py`：加载模型制作源后立即切换 `r.data.pose_position='POSE'`；作者清单记录该状态。
- 重新制作四个动画：单持 `A_RSH12_fire`、`A_RSH12_aim_fire`，双持左右 `A_RSH12_r_fire`、`A_RSH12_l_fire`。
- 沿用完整原生 V7 手臂骨架及现有单动动作。三个当前 profile 同步由原配方重新保存。
- 修改前的作者入口、可编辑动画、FBX、profile 和相关 UE 资产保存在 `SourceAssets/RSH12FireFix20261003/BeforeSource`、`BeforeAuthored`、`BeforeAssets`。
- 本轮未修改 C++、模型、材质或武器数据，无需重新编译原生模块。

## 交付状态

四个动画及三个当前 profile 共七个 UE 资产已在后台实际导入并保存。实际保存记录为 `SourceAssets/RSH12FireFix20261003/import_receipt.json`。动作作者源、FBX 和单动配方同步更新，后续重制会沿用 POSE 状态。

未启动编辑器、游戏、PIE、渲染或回归测试。游戏中的可见性、ADS 后坐及拨锤动作由用户测试。
