# 枪械往复与抛壳校准：整理和发布

日期：2026-10-09。范围为本对话最后完成的步枪轴向往复优化及逐枪抛壳位置检查。当前仓库为 `D:/FPS3D/FPSGAME`，目标 `https://github.com/allang2208/3D-FPS.git` 的 `main`。

## 已整理

17 个失败探测、空请求输出、过期 Live Coding 传输文件和修改前源码备份已移入本机 `trash/weapon-gunplay-retired-20261009/`。移动前限定绝对路径，移动后逐个读回 SHA-256；总计 611,176 字节。原路径、目标、原因、保留替代物和散列见 [归档清单](../AssetArchives/weapon-gunplay-20261009.json)。这些恢复副本包含当时并行代码，只能按块参考，不得整文件覆盖当前工作。

保留所有最终输入和当前制作工具：实际资产引用、当前网格导出、参考及压缩姿态、离线几何、窗口选点配方、对照图与成功构建回执。未根据目录日期或 candidate 名称清理其他任务。

## 公开内容

- [轴向往复实施](rifle-axial-recoil-20261008.md)：运行表 `RifleAxialRecoil.h`、角色表现消费点及 [采样/生成配方](../../Tools/Weapons/RifleAxialRecoil20261008/README.md)。
- [抛壳逐枪实施](casing-port-calibration-20261009.md)：运行表 `CasingPortCalibration.h`、特效组件的本轮接入及 [抛壳制作配方](../../Tools/Weapons/CasingPorts20261009/README.md)。
- [武器 SKILL 对应章节](../../skills/ue5-weapon-workflow/references/gunplay-vfx.md#逐枪抛壳校准2026-10-09)：参考骨架/当前 mesh/开火姿态的区别、物理出口与套筒锚点、双持未镜像枪体、轴向曲线逐时刻去重。个人技能与工程副本已同步。
- 稀疏窗口坐标 `calibration.json`、后坐力配方 `recipe.json` 和公开归档清单。

共享文件按本轮语义片段暂存；第三人称枪口映射、特效预热、热成像、附魔与其他并行修改继续保留在工作区。公开抛壳代码直接使用当前公共基线已有的枪体世界变换；本地版本还沿用已有的第三人称映射包装，未为本次发布带入该独立功能。

## 恢复与状态边界

先按 [AssetSetup](../AssetSetup.md) 恢复完整已授权 Content，再按各制作目录 README 的输入顺序重建。当前网格 FBX、NPZ 几何、密集骨骼/动画 JSON、截图、UE 包、引擎、插件、材质、字体、日志和构建二进制不进入本次提交；使用资产的商业许可不作为原资产可再分发的证明。Git 源码不是完整可运行内容备份。

2026-10-09 `FPSGAMEEditor` 和 `FPSGAME` 均已在完整本机工程中构建成功，构建记录留本机。此次发布按规则复核精确差异、路径、大小、敏感信息、许可与配方链接；没有重新运行 UE、游戏、动画渲染或玩法回归，也没有将公共切片单独构建的结果写成已完成。实际连射、ADS、双持及总后坐力观感仍由用户测试。
