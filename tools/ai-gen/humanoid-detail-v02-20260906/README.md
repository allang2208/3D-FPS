# 人形僵尸 Low Poly V02 · 2026-09-06

按用户最新反馈，最终采用简洁 Low Poly 风格，保留原脸部神态和造型；取消试做的独立眼球、瞳孔和牙齿。优化集中在身体轮廓、肩肘膝支撑、手部表面、衣领袖口与材质。三种既有怪物共同升级，不新增玩法。

| 模型 | V01 三角面 | V02 三角面 | 骨骼 |
| --- | ---: | ---: | ---: |
| 普通现代僵尸 | 1724 | 8572 | 31 |
| 工装矿工 | 4712 | 11532 | 31 |
| 狂奔僵尸 | 1724 | 8428 | 31 |

## 最终处理

- 恢复可合并的四边面后做一层曲面支撑；面部与脚底大部分投回原表面，维持 Low Poly 的原造型。没有额外的面部高密度细分，也没有新增眼球或牙齿几何。
- 肩、肘、膝与衣服腰部做有限幅度修形；手部保持原有简化手型与骨链，只做轻微表面优化，没有重新制作独立五指动画。
- 增加简洁衣领厚度、袖口边缘、纽扣，普通僵尸的领带改为贴身低面数几何。矿工原有安全帽、头灯、腰包、反光条与护膝继续复用。
- 降低皮肤粗糙颗粒感，保留风格化肤色和脸部图形处理。衣服增加轻微织物与污渍变化，体表伤口使用表面材质；每只仍为一个不透明 2K PBR 材质。
- 插值后重新限制最多四骨影响并归一化。动作、时长、移动速度、攻击窗口、伤害与生命均保持 V01。

## 原动作与验证

本轮没有制作新动作。参考与时间合同沿用已实际查看的 [现代僵尸](../modern-zombie-v01-20260906/README.md) 与 [两个变体](../humanoid-variants-v01-20260906/reference-notes.md)，使用同一实际动画检查新网格的攻击、移动与倒地。

`animation-parity.json` 逐条比较三个最终 GLB 与各自 V01：每个模型 16 动画、1530 条通道，时间及变换采样最大差异为 **0**。骨架维持 31 骨。

最终 GLB 重新导入 Blender，分别采样 918 / 968 / 914 个姿态，检查有限坐标、UV、权重和接地。矿工倒地中间姿态仍有约 2.1cm 的附件地面交叠，与 V01 相同；终态最低点约离地 5mm。检查报告在各模型子目录 `asset-validation.json`。

Godot 的普通僵尸行为、动作衔接、弱点命中、变体行为与主场景绑定分别使用现有测试；最终运行日志保留在本目录。主场景默认 D3D12 Forward+ 截图在 `runtime/`。完整人工战斗试玩与大群同屏帧率评估未由这些检查替代。

最终结果：普通行为 22、动作衔接 9、变体行为 32、弱点射线与弹丸 39、普通主场景/副本绑定 8，共 110 项通过。默认渲染器三模型主场景检查和项目 180 帧烟测通过，无脚本错误。编辑器无头导入退出仍有资源/RID 清理提示，未将导入日志描述为完全无错误。

## 文件与预览

- [普通僵尸源文件](modern/modern-zombie-v02.blend) / [GLB](modern/modern-zombie-v02.glb)
- [工装矿工源文件](miner/miner-zombie-v02.blend) / [GLB](miner/miner-zombie-v02.glb)
- [狂奔僵尸源文件](runner/runner-zombie-v02.blend) / [GLB](runner/runner-zombie-v02.glb)
- [普通僵尸前后对照](previews/modern-front-comparison.jpg) / [面部对照](previews/modern-head-close-comparison.jpg)
- [三种最终模型](previews/family-v02.jpg)
- [普通攻击](previews/modern-Attack.gif) / [矿工慢走](previews/miner-Walk.gif) / [狂奔跑步](previews/runner-Walk.gif)

`build_detail.py`、`detail_geometry.py`、`detail_material.py` 与各子目录的源管线快照支持重建。`.gdignore` 将制作源和逐帧参考排除于游戏资源扫描；正式模型位于 `assets/models/modern_zombie/modern_zombie_v02.glb` 和 `assets/models/humanoid_variants/*_v02.glb`。

来源与署名继续沿用 [Denys Almaral / Quaternius 许可](../../../assets/models/modern_zombie/LICENSE.md)。本轮没有引入新的第三方素材。

## 2026-09-06 整理记录

已清理数字命名逐帧截图与 Blender 自动备份；最终 GIF、动作检查表、命名近景、源文件、许可与重建输入保留。再次打包预览前先按重建步骤重新渲染。制作目录已用 `.gdignore` 排除游戏导入。

本次六个制作目录与两个运行资产目录共删除 7435 个可再生文件、备份及无引用的 V01 运行副本，释放 658.40 MiB。V01 制作源和动画对照 GLB 保留。范围见 `cleanup-manifest.json`；所有清理目标已完成删除。

## 隔离发布验证

发布副本从远端 main 基线构建，97 项怪物检查与默认 GPU 四姿态通过。与原工作区 110 项的范围差异、旧战斗诊断和导入退出提示见 [发布记录](../../../docs/modern-zombie-publication-20260906.md)。
