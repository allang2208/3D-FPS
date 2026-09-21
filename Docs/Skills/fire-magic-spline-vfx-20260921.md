# Free Spline VFX 火系替换 · 2026-09-21

用户要求查询 GitHub 上改善陨星僵硬表现的方案，并让灼锋焰甲、陨星试用 Free Spline VFX 火焰。本轮保留已换入的 RuralAustralia 写实岩体，仅重做火焰表现与坠落曲线。

## GitHub 参考与实施方案

- [Unity 官方 VisualEffectGraph-Samples 的 Meteorite](https://github.com/Unity-Technologies/VisualEffectGraph-Samples/tree/master/Assets/Samples/Meteorite/VFX/MainMeteorite) 将陨石、烟火拖尾、地面冲击及附加层分别组织。参考这种分层方式，在现有 UE 陨星上分别处理包覆火、世界空间尾焰、烟气、落地爆燃和余火；原技能没有预警圈，本轮不新增。
- [Plume](https://github.com/travisdmathis/plume) 展示生命周期控制、随附着点生成拖尾及 [curl 扰动](https://github.com/travisdmathis/plume/blob/main/packages/plume/src/modules/update/curl-noise-force.ts) 的组织方式。本轮在 Niagara 中独立编写三角函数势场的解析 curl，配合阻力、上浮及粒子独立相位；没有移植 Three.js 库，也不将它称为完整噪声实现。
- 上述项目分别面向 Unity、Three.js，不能作为 UE Niagara 资产直接导入。仅作为组织与运动思路参考，没有引入其模型、纹理、库或脚本作为运行依赖。

## 火焰来源与适配

实际使用本地 Dr.Game Free Spline VFX：`/Game/_SplineVFX/NS/NS_Spline_Fire` 的 Fire_B、FireBackUp、Smoke 层对应的素材。

- `T_Vfx_Stamp_FireFlame_88`：主要火舌。
- `T_Vfx_Stamp_FireFury_88`：外层翻卷火焰。
- `MI_Vfx_ParticleSubUV_fog03_88_fade` / `T_Vfx_stamp_fog3_88`：冷却烟气。

原系统依赖样条和自身循环，部分层含额外灯光、贴花渲染器。这里复用其真实火焰序列与烟气材质，在新 Niagara 系统中适配武器端点、飞行路径和范围参数；不是把整套样条系统直接挂到角色。

火焰使用项目已有的软根部 AlphaComposite 材质的独立副本，替换为两套原始火焰图集，按粒子独立播放 8×8 序列，处理根部、边缘和生命周期淡入淡出。Free Spline VFX 原包、火球现行材质及系统保持不变。烟气同样复制其材质和实例后设置，不修改原包。

### 用户反馈黑色火焰后的修复

初次接入遗漏了当前火把材质使用的 `EyeAdaptationInverse`：读取实际运行母材质可见，`M_SplineFireSoft` 为 Unlit / AlphaComposite，发光直接从最终预乘节点输出，没有曝光补偿；两个图集、8×8 SubUV 和粒子颜色绑定正常。场景曝光会压低火焰 RGB，但 AlphaComposite 仍按不透明度衰减背景，产生黑色火舌。

已在 `M_SplineFireSoft` 最终预乘发光后补入曝光补偿，保留 DepthFade、软边、根部及寿命淡出的原透明度链；同包烟气副本 `M_SplineSmoke` 也补偿曝光，保持其灰褐色设置。没有修改场景曝光或全局灯光。修改后的两个母材质、三个实例已重新编译保存，制作脚本 `compensate_exposure()` 同步保留修复，重建不会丢失。

排查快照与修复前副本位于 `SourceAssets/FireMagicSplineBlackFix20260921`，`material-fix-result.json` 记录三个实例的发光输出及透明度连接检查。这次仅做材质层定向排查、编译和保存，没有启动 PIE 或实机效果测试；此次为资产修复，无需 C++ 编译或关闭编辑器。

## 本轮制作与接入

全部新火焰资产位于 `/Game/Skills/FireMagic20260921/SplineV4`：

| 系统 | 表现 |
| --- | --- |
| `NS_ArmorSplineFire` | 刀刃附着火舌与挥动后留在世界空间的翻卷余焰，继续使用真实武器端点和速度 |
| `NS_ArmorSplineAura` | 脚边火环，火舌与翻卷层错开相位 |
| `NS_MeteorSplineMantle` | 岩体椭球表面分布火舌，沿飞行反方向剥离 |
| `NS_MeteorSplineWake` | 沿上一帧到当前帧路径生成火焰；独立翻卷、扰动、阻力及冷却烟气 |
| `NS_MeteorSplineImpact` | 即时爆燃、延迟 0.055 秒的上卷火舌、延迟 0.12 秒的烟气，各自扩散并淡出 |
| `NS_MeteorSplineAfterfire` | 地面余火扩散，主火与翻卷层独立变化 |

`FPSFireMagicComponent.cpp` 的运行与预载路径、`FPSMeteorStrike.cpp` 的实际生成路径同步切换。坠落进度从 `0.16t+0.84t²` 改为 `0.28t+0.72t²`，增加初始下落速度，保持 0.65 秒命中；火光加入小幅非同步波动。技能数值、伤害结算、施法手势、六边图标、写实岩体与落地碎片继续沿用。

作者入口：`Tools/Skills/build_fire_magic_spline.py`。通过 MCP 桥依次执行 `run('materials')`、`weapon`、`aura`、`mantle`、`trail`、`ground`、`impact`。依赖现有 V2 系统的参数和生命周期容器，以及项目火球的软边材质制作链；新系统中的火焰渲染素材来自 Free Spline VFX，不再引用青铜火把的火舌材质。恢复时先恢复原有火系依赖及合法本地 Free Spline VFX 包。

作者输入、分阶段保存回执、来源记录保留在 `SourceAssets/FireMagicSpline20260921`。第三方原包、衍生 uasset 与下载的 GitHub 阅读副本仅留本地，不作为本轮公开分发内容。

## 执行边界

已完成独立资产制作、保存及 C++ 引用修改。必要代码编译记录单独保存在作者目录。本轮不启动游戏、PIE、截图或效果验收；运动参数和实际观感由用户测试后反馈。

首次必要编译：23:28 触发 `LiveCoding.CompileSync`，UBT 完成源码编译并返回 `Succeeded`，但 LiveCodingConsole 随后退出，未留下补丁创建/应用成功结果，编辑器调用仍在等待。未强制结束 UE，已请用户正常关闭后完成基础 Editor DLL 构建。不能将 UBT 这一步成功称作热更新已生效；原始日志与状态在作者目录 `live-coding-ubt-log.txt`、`live-coding-console-log.txt`、`build-status.txt`。

最终构建：用户回复“已保存并关闭 UE”后，执行 `Build.bat FPSGAMEEditor Win64 Development -WaitMutex -NoHotReloadFromIDE`，返回 `Target is up to date` / `Result: Succeeded`，退出码 0，记录 `SourceAssets/FireMagicSpline20260921/editor-build-01.log`。基础 Editor 目标已完成常规构建，不再依赖前述未完成的热补丁。本轮没有重新启动编辑器或运行游戏测试。
