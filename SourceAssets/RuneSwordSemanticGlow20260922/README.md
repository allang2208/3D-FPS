# 按语义图标区分剑身Ⅱ符文颜色

用户反馈符文均为白色，要求按新版图标的颜色和含义调整剑上荧光。本轮修改已加载的符文材质，保存 2 个父材质及 1 个原生金色实例；没有修改 C++、改造属性、存档、纹样遮罩或图标。

| 选项 | 核心与光晕 | 动态表现 |
| --- | --- | --- |
| 共鸣符文 | 青绿色 | 环纹宽缓呼吸 |
| 侵蚀符文 | 紫罗兰色 | 裂纹错相明暗变化 |
| 导魔符文 | 电蓝色 | 从剑根向剑尖流动 |
| 金色符文强化 | 暖金色 | 轻微呼吸与沿刃扫光 |

原来的前三种模式共用银白核心及冰蓝荧光，`BaseBrightness=1.35`、`GlowStrength=2.8`。现在按 `RuneMode` 选择独立的核心/光晕参数，降低为 `0.85`、`1.25`，发光 RGB 同比例限制峰值到 `1.65`，避免通过单通道裁切丢失色相。核心始终有非零亮度。光晕半径由 2.5 改为 3 个遮罩像素，仍使用原有局部曝光补偿，不修改全局后期或场景灯光。

读取当前 Custom 代码还发现旧金色注入重复，`pulse` 和 `haloColor` 被放在声明之前使用。本轮以完整、可编辑的 `semantic_runes.hlsl` 替换该节点的代码，保留原投射空间、纹样采样与裁切。无需重新执行早期 `RuneGoldMaterialCommandlet` 的源码拼接流程。

符文长剑的金色强化仍走原生 UV0 材质，保留剑身及护手的独立遮罩和统一长度相位。金色底色与光晕换为本轮暖金参数，常亮强度 0.85、呼吸幅度 0.09、扫光幅度 0.40，光晕权重 0.08；RGB 峰值同比例限制到 1.35。

## 范围与文件

- 共享覆盖材质：`/Game/Weapons/MeleeRunes20260915/SurfaceV2/M_SilverRuneSurfaceV2`。现有两把剑的同名改造共用它，因此共鸣、侵蚀、导魔的配色同步一致；其他剑使用的金色投射分支也为暖金色。
- 原生金色材质与实例：`/Game/Weapons/AzureRunesword20260913/NativeRuneGold20260922/M_AzureRunesword_NativeGold` 和 `MI_AzureRunesword_NativeGold`。
- `palette.json`：线性色彩和亮度参数；`semantic_runes.hlsl`、`native_gold_glow.hlsl`：可编辑着色器源。
- `material_sources.json`、`Before/`：修改前节点、参数与 3 个资产备份。
- `install_semantic_glow.py`：通过现有互斥 MCP 桥接入，保留材质图中的原节点和原 PBR 连接。
- `install_receipt.json`、`install-resume-result.txt`：3 个资产保存完成记录。

首次调用已完成覆盖材质制作和编译，但保存被当前 PIE 拒绝。随后只结束 PIE，编辑器保持打开，从保存失败处继续，完成覆盖材质、原生金色材质和实例保存。未启动游戏、执行截图、运行测试或视觉验收；由用户重新进入游戏查看。
