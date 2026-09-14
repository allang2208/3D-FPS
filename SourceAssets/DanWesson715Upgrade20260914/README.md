# Dan-Wesson 715 近景与动作升级

2026-09-14 后续换弹修正：逐发及速装器换弹的当前作者源为 `../DanWesson715ReloadFlick20260914/`，已在原运行路径重新导入。此目录继续作为模型／材质、非换弹动作及参考动画来源；重建当前换弹不要用本目录旧脚本覆盖甩腕和手型修正。

方案与实施说明：[dan-wesson715-upgrade-plan-20260914.md](../../Docs/Weapons/dan-wesson715-upgrade-plan-20260914.md)。

## 作者源

- `DanWesson715_Upgrade_Editable.blend`：最终可编辑模型、材质、原始参考和升级动作。
- `DanWesson715_Hero_Editable.blend`：表面制作阶段源；`DW715_SOURCE_REFERENCE` / `DW715_HIGH` / `DW715_LOW` / `DW715_CAGE`。
- `SK_DW715_Manny.fbx`、`Animations/A_DW715_*.fbx`：最终游戏导出。
- `Textures`：7 组 BaseColor / ORM / NormalGL，共 21 张；UE 法线绿色通道翻转一次。
- `author_inputs.json`、`surfaces.json`、`animation.json`：制作输入、几何输出和动作时序。
- `import.json`：导入脚本保存的实际路径；`build-native-retry.log` 为最终必要构建结果（Succeeded，目标已最新）；`import.log` 记录导入脚本完成及保留的工程配置错误、绑定姿势警告。

## 重建顺序

1. `fetch_references.py` 保存固定 GitHub 提交的 FBX、README、Unlicense 和散列记录。
2. 原参考为 FBX 6.0，先用 `convert_fbx.cpp`（本机 UE 自带 FBX SDK）转为 Blender 可读取的 FBX 7.4，再运行 `read_donor.py`。
3. `prepare.py` 从前版可编辑源读取分件、骨骼和用户反馈的开火姿态。
4. `build_surfaces.py` 制作局部高低模、UV 和 PBR 烘焙；沿用 M1911 的作者函数，保留其源输入文件。
5. `author_actions.py` 制作轴线修复、接触目标、GitHub 手部运动适配及最终 FBX。
6. `import_assets.py` 导入 `/Game/Weapons/DanWesson715/Upgrade20260914` 并添加当前天气材质映射。

参考动作来源：ZenXChaos/ThirdPersonShooter-AnimationSets，提交 `f19adc2ece4cab0f89c9236223abb97d4d2badea`，`Reference/license.md`。本次使用手臂路径弧线及受限的手指运动变化；715 的开巢、退壳、速装器和接触目标为独立编排，并非下载了现成的 Manny 第一人称左轮换弹。

枪体与原贴图仍来自用户持有的 MyNameIsVoo Fab 包；Manny 手模和 P9 衍生基线保持原许可。第三方原包和派生 Blend/FBX/Content 默认仅留本机。声音继续使用前版已记录的 CC0 枪声和原创机械音，仅调整接触时点。

本次无游戏测试、截图、预览渲染、回归或试听。纹理烘焙用于资产制作，不是验收渲染。
