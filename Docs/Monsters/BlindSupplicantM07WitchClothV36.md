# M07 V36：复用当前巫婆衣物的背膜物理

日期：2026-10-03。工程：`D:/FPS3D/FPSGAME`。

## 当前交付状态

用户反馈 V34／V35 调整后缺少背膜物理摆动。本轮保留 V35 修复后的显示蒙皮，制作连续隐藏布料代理，复用当前 F6 巫婆 `WitchRebuilt` 的布料捕获及 Chaos 配置。

制作源、两个 FBX、原生接入代码和导入保存脚本已完成。**Editor／Game 必要构建均已完成；新代理、原显示网格的布料／LOD，以及原 AI／F6 蓝图已后台实际保存。** `ue_witch_cloth_delivery_v36.json` 顶层 `saved: true`，22:57:58 的导入日志同时记录三个资产包落盘及脚本完成标记。Game 构建输出 `Binaries/Win64/FPSGAME.exe`，总构建时间 275.81 秒。

导入 commandlet 完成后，退出阶段 `python311.dll`／`PythonScriptPlugin` 出现访问异常，进程返回 3；此异常发生在保存及完成回执之后，不能将该进程记作正常退出。未再次导入覆盖资产，也未启动编辑器、游戏、截图、渲染或性能测试；最终效果由用户测试。

构建解除阻塞时，仅将 `HangingBellM09.h` 的反射参数 `Mesh` 改名为 `InMesh`，避免遮蔽继承成员。该文件同一模块内的其余编译错误由并行修改更新，不覆盖其实现。

## 采用的参考与适配

- 参考是当前 `/Game/Monsters/WitchRebuilt/SK_WitchRebuilt` 内的 `WitchRebuilt_LowerDrape07`，不是退役的 WitchMeshy V06／V07。
- 继承 `UWitchRebuiltClothingAsset` 的有界显示捕获：异常的重心坐标与法向偏移改用邻近三角形，无法稳定捕获的局部退回蒙皮。
- 直接复制已保存巫婆布料的 Chaos 刚度、动画驱动、阻尼、惯性及共享求解配置。针对盲祷者体型，将碰撞厚度设为 1.2 cm、稀疏自碰撞球半径设为 1.1 cm、裁剪倍率设为 2.5；不启用额外的逐点／逐面自碰撞。
- 身体材质中也包含膜片折边，须与膜片材质绑定到同一模拟；依据作者顶点 Alpha 保护真实身体。跨分区重合点共享蒙皮混合权重，捕获退回区域沿表面渐变 12 cm。

## 制作源与性能范围

在 V35 源上保留可见几何、UV、材质、83 骨参考以及修好的权重。新增的左右连续代理各为 39×15 顶点，共 **1,170 顶点、2,128 三角形**；上缘及内侧固定，活动范围渐变，最大自由位移 28 cm。显示折叠层通过布料捕获跟随该连续面。

实际作者回执：234 个固定点、两个显示材质分区共用一个布料资产；巫婆模板求解迭代 4、最大 6、子步 1、动画驱动刚度 0.008。制作日志记录 54,960 个显示顶点参与布料混合。生成的 LOD0／1／2 分别为 145,460／81,354／77,435 个显示顶点；这些是资产构建数据，不是游戏或视觉验收。

不复用旧 V18／V31 的碎片代理拓扑，仅沿用身体和四肢的 14 个碰撞胶囊定义。低分辨率代理尺寸不等于实际帧率收益；未采样性能。

运行时使用既有距离判断和淡入淡出：12 m 内恢复模拟，16 m 外退出；过渡 0.35 秒，退出后暂停求解并释放 LOD0 锁定。死亡／击倒时 0.18 秒退出活体布料，修好的蒙皮跟随骨架。新增的捕获、接缝合并与距离传播只在资产制作阶段运行。

导入脚本关闭 V34 的 `use_coherent_gill_motion`，使 Chaos 接管二次运动；保留既有有限手臂避让。移动、横扫、悬浮施法、死亡和收势接地不换动画，不修改 V35 法术数值或 1.5 倍移动速度。

## 文件与接入

- 制作：`Tools/BlindSupplicantM07/author_witch_cloth_v36.py`
- 原生：`Source/FPSGAME/Monsters/M07MembraneClothingAsset.h/.cpp`，`BlindSupplicantAuthoring.h/.cpp`，`BlindSupplicantMonster.cpp`
- 保存：`Tools/BlindSupplicantM07/import_witch_cloth_v36.py`
- 制作源目录：`SourceAssets/BlindSupplicantM07Meshy20261001/WitchClothV36/`
- 原显示网格：`/Game/Monsters/BlindSupplicantM07/SK_M07_BodyMotionV18`
- 新隐藏代理：`/Game/Monsters/BlindSupplicantM07/Working/SK_M07_ClothProxyV36`
- 原 AI／F6：`/Game/Monsters/BlindSupplicantM07/BP_BlindSupplicantM07`

制作目录内保存 `M07_WitchClothV36.blend`、显示／代理 FBX、作者参数和 `cloth_manifest_v36.json`。导入时备份原网格与蓝图到 `Before/`，重新生成三档显示 LOD，并保存原正式网格／蓝图。只有全部保存完成，`ue_witch_cloth_delivery_v36.json` 才写入 `saved: true`。

制作日志为 `Saved/Logs/M07-V36-Author.log`；Editor 完成日志为 `Saved/Logs/M07-V36-EditorBuild-Final.log`。实际保存及退出异常记录在 `Saved/Logs/M07Import-20261003-225054.log`；Game 构建记录在 `Saved/Logs/M07-V36-GameBuild-Final.log`。用户尚未认可 V36 效果，不作为已验收模板。
