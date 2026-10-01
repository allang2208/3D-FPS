# 暴风雪三层乌云与砸落音效

2026-10-01 按用户要求参考原项目乌云构造，复用现有云朵素材，并在冰块砸落时播放音效。默认后台制作与必要构建，不启动游戏、PIE、预览、渲染或音频试听。

## 原版依据与此次接入

只读原项目 `E:/无尽轮回/长期备份/2026-7-13-1/game-dev`。`src/effects/blizzard-zone.js` 的 `_cloudCfg`、`_buildCloud` 将深灰／灰／浅灰三层叠出云体，分别 18／14／9 团，范围由椭圆半轴推导；边缘每 280 ms 散出两团。`data/skills.json:skills.blizzard.sounds` 指定 `icewall.mp3` 起手、`ice.mp3` 命中；原版声音在伤害拍命中后播放，装饰冰块的 `_impact` 自身没有音效。

本次保留三层构造与现有声音身份，再按用户要求扩展到实际砸地时触发声音。伤害／寒冷／经验节拍、法杖限制、施法动作、快捷栏、存档及坠冰速度仍沿现有版本。

## 云朵素材与构造

新资产归属 `/Game/Skills/Blizzard/StormV2`。作者 `Tools/Skills/build_blizzard_storm_cloud.py` 从已导入诺曼底包的 `M_Master_StormCloud`／`MI_StormCloud_00A` 派生独立父材质和实例，保留 `T_Particle_Cloud_00A_Masks`、原生流动噪声与受光表现。源母材质只有粒子 Alpha，没有粒子 RGB 接入基础色；副本补入逐层 RGB，并给透明边缘增加柔化圆形边界。

- 18 团深灰底层、14 团中灰主体、9 团较浅顶部为一次出生、持续整个区域的稳定云体。径向分布、大小和高度按技能范围与云顶高度推导，位置轻微翻卷，不整体随世界风离开区域。
- 周边烟云以约 7.14 团／秒出生，寿命 1.5–2.6 秒，接受小幅共享风偏移与细节预算。核心在低细节时保留约 27 团，完整配置 41 团；周边约最多 19 团。
- 原生云材质的近景淡出与深度淡出缩到局部施法尺度，发光为 0；一个云系统的四个发射器仍只占一个 Niagara 组件。每区域继续是云／雪／寒雾 3 个组件、48 个坠冰／碎冰实例，每玩家最多 4 场。
- 云核心在开始约 0.25 秒淡入，结束后约 0.6 秒淡出；结束停止周边新出生。运行云组件传入 `StormDuration` 与 `CloudEmission`，扩大云的固定边界以容纳羽化边缘。

此云为技能区域局部受光云团，使用诺曼底已有云素材；本次没有修改天空天气资产。

## 砸落音效

`S_BlizzardIceLanding` 由已迁移 `S_IceImpact` 派生，音源对应原版 `assets/sounds/skills/ice.mp3`；配套专属 `ATT_BlizzardIceLanding` 与 `CON_BlizzardIceLanding`。原版起手音和有效伤害拍命中音继续保留。

`FPSBlizzardZone` 在非碎片雪球／冰锥首次碰到表面时，于实际接触点播放一次落地声；空场落地也有声音，碎片二次落地不重复播放。每区域最短间隔 0.14 秒，雪球音量 0.36、音高 0.86–0.98，冰锥音量 0.58、音高 0.97–1.07。距离衰减半径 120 cm、外侧衰减距离 2000 cm；专属声音全局最多 6 个并发，满额拒绝新声音，避免裁断已播放声音。

组件将新云与落地声加入既有 BeginPlay 异步预载，释放时不执行同步加载；`/Game/Skills/Blizzard` 已列 AlwaysCook，覆盖 StormV2。

## 落盘与构建

源码和作者脚本已保存。初始编辑器桥批次因接入超时未发送；后续编辑器关闭，没有可用节点。确认没有运行中的编辑器／commandlet 占用后，使用后台 `UnrealEditor-Cmd -run=pythonscript -NullRHI` 完成制作并保存，退出码 0。

回执 `Saved/BlizzardCloud20261001/asset-authoring.json` 列出已保存的专属父材质、实例、Niagara 云、声音衰减、并发与 SoundWave 共 6 个资产。命令行日志 `author-commandlet.log`／`author-console.log` 同目录。

原生构建曾遇到并行修改反射头文件后生成代码过期的问题，按最新工作区重新生成 UHT 后继续构建，保留并行修改。`build-game-editor-final.log` 已记录 Editor DLL 完成链接及 `FPSGAMEEditor.target` 写入；之后 Game 编译因对话中断停止。

继续后的 `build-game-resume.log` 记录暴风雪两份 C++ 已编译，但整体 Game 目标失败：构建期间角色的 SVD 握持属性和符文剑头文件发生更新，生成代码过期；符文剑 `FinalizeBoneTransform` 还通过 `const UAnimSingleNodeInstance*` 调用了非 const 的 `GetCurrentAsset()`。为完成必要构建，只将该处局部指针声明从 `const auto*` 改为 `auto*`，随后重新生成 UHT 并构建 Game。

`build-game-current.log` 中生成代码错误已消除，剩余错误来自同期更新的双持手枪 `PistolPoseFamily`：条件表达式混用了字符串与 `EName`。将三个分支显式统一为 `FName`，保持返回的姿态家族名称不变。

Game 最终构建 `build-game-complete.log`：569 项动作，`FPSGAME.exe` 链接和 `FPSGAME.target` 写入完成，`Result: Succeeded`，退出码 0，耗时 399.14 秒。

最新 Editor 构建 `build-editor-complete.log`：140 项动作，`UnrealEditor-FPSGAME.dll`／AutoFootstep Editor DLL 链接和 `FPSGAMEEditor.target` 写入完成，`Result: Succeeded`，退出码 0，耗时 163.16 秒。源码、6 个专属资产及 Game／Editor 程序均已落盘；没有主动打开编辑器或运行游戏。

未进行实机测试或观感／音频验收，由用户测试。
