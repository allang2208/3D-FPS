# 百目炉渣 ApeRecoveryV7：大右臂与猩猩式收击

2026-10-01。用户反馈 ClawV6 的最大右臂仍然扭曲，要求寻找相似怪物项目，并考虑大猩猩或其他动作的手部收击。本轮读取原蒙皮、动作制作脚本、造型参考和商城资料，针对肩臂权重与普通攻击/重击回收进行资产修订。导出、实际导入和保存状态以 `ApeRecoveryV7/installation_complete.json` 为准；没有启动游戏、PIE 或验收渲染。

后台等待共享资产释放后，第二次接入已完成：commandlet 退出码为 0，两份运行网格、普通挥爪、抬手重击和公共骨架均已保存，`production_status.json` 的活动版本为 `ApeRecoveryV7`，安装待办已清除。当前 F6 和原生类仍引用原路径，直接使用此次保存的资产。本轮不需要新增原生编译；未执行游戏或视觉验收。

## 找到的参考与实际使用边界

1. [Epic Paragon: Rampage](https://www.fab.com/listings/0807cf74-08fd-4a33-8c8d-f33c9439fb1f)：免费 UE 角色包，商店说明包含角色、动画和动画蓝图。它的粗壮长臂体型适合作为后续完整动作供体候选。本机 FabLibrary 只有对应产品 ID 的空目录，当前 Content 没有可采样的 Rampage 骨架/动画，不能当成已下载或已接入。
2. [Ape Melee Combat Animation Pack](https://www.fab.com/listings/acb25cf5-c321-4fa6-8e9c-3c73df82c67f)：供应商说明覆盖猩猩、兽形与怪物敌人的近战、冲击、反应和死亡动作，提供 FBX。没有购买或下载；其演示视频在网页工具中无法取回，未声称看过逐帧演示或取得源动画。
3. [Reallusion Gorilla 动捕制作说明](https://magazine.reallusion.com/2025/11/10/the-making-of-3d-gorilla-animations/)：供应商介绍猩猩与人体的肩胸宽度、臂长和腿长差异，以及用臂长延伸工具捕获重心和节奏。用于确定体型适配思路；没有取得或使用其商业动捕文件。

本轮交付是按粗壮长臂力学重新创作的猩猩式动作，没有下载、采样或重定向上述商店资产，不能称为“已用 Rampage 动画”。不再采样 ClawC 的独立肩臂方向。

当前编辑器在首次资产桥等待期间退出，因此当前地图的现场怪物列表未取回；没有为只读搜寻另起 UE 编辑器。本次本机资产搜寻范围为当前项目 Content/SourceAssets 与本机 Fab/模型缓存，不把目录占位当成模型或动画文件。

## 本轮定位

`RuntimeV3/author_runtime.py` 的原始蒙皮用 `smooth(.33,.60,p[:,2])` 将较高部位附着到躯干；ClawV6 又从这份蒙皮继承大右臂基底。这个条件对粗长前肢不适合：手臂区域的一部分会留在胸/背上，而掌、前臂已经运动，线性蒙皮会在中间拉伸和扭曲。

对源网格右臂走廊 `x > .08、y < -.38、.32 < z < .60` 读取权重，1,532 个顶点中有 683 个的躯干影响超过臂骨影响，躯干权重均值约 44.9%。这是目标区域的源数据定位，不是游戏视觉验收或性能测量。

另一个问题是 ClawV6 将上、下臂方向分别转成独立最短旋转，再从相邻骨推导辅助扭转。体型和绑定弯曲平面不同，源动作的回收会使前臂快速转向；换动作名称或单纯调大手掌运动不能解决这类滚转与权重问题。

## 蒙皮修订

- 保留原绑定姿态、43 根作者骨、39 根变形骨、几何、UV、法线和材料。
- 修改 12,682 个右臂/连接区顶点；以肩—肘—腕—掌的弧长分区，躯干附着只在实际肩部连接段过渡。
- 上臂、前臂、掌的主体跟随对应主骨，肘和腕附近保留短过渡带并平滑。减少刚性段上辅助扭转骨的混合，五个爪指保留轻度独立影响，每顶点最多四个影响。
- 目标区域以外复制原 ClawV6 权重。Blender 使用线性蒙皮，符合 UE 的当前蒙皮方式。

## 动作修订

普通挥爪和抬手重击使用一个随肩臂运动的弯曲平面，前臂只由该平面中的肘部铰链驱动；不再对下臂单独求方向旋转，没有独立轴向拧转。肩臂关键姿态之间使用四元数插值，上臂/前臂长度按原绑定保持，腕部屈伸限制在小范围。

普通攻击：抬臂 → 向前挥击 → 从身体右外侧收回 → 放低前臂 → 回到原撑地点。重击：从外侧抬起 → 短暂停顿 → 落掌重击 → 从外侧回收 → 放回撑地点。躯干轻度移重，其他三肢沿原支撑垫配合。

动作合同保持：

| 动作 | 长度 | 伤害窗口 |
| --- | --- | --- |
| AttackSweep_R | 1.4 s | 0.54–0.73 s |
| AttackSlam_R | 1.8 s | 0.84–1.00 s |

两条动作的首末帧回到原绑定撑地姿态；其他动作关键帧没有重制，新的蒙皮同时应用到其网格。奔跑接近、站稳后才启动攻击时钟、340 cm/s 追击、300 cm 接敌、约 130 cm 近战到位、1.25 秒冷却、0.12 秒恢复与死亡 0.42 秒布娃娃交接保持。

## 制作与接入

制作目录为 `SourceAssets/HundredEyedSlagMeshy20260930/ApeRecoveryV7`；包含 `author_ape_recovery.py`、可编辑 `.blend`、`skin_weights.npz`、网格 FBX、两条动画 FBX、动作合同和保存记录。`Before` 备份本轮实际替换的旧资产。

保存目标是两份现有网格、两条现有攻击和公共骨架：

- `/Game/Monsters/HundredEyedSlag/PolishV2/SK_HundredEyedSlag_V2`
- `/Game/Monsters/HundredEyedSlag/V1/SK_HundredEyedSlag_V1`
- `/Game/Monsters/HundredEyedSlag/V1/Animations/A_HundredEyedSlag_AttackSweep_R`
- `/Game/Monsters/HundredEyedSlag/V1/Animations/A_HundredEyedSlag_AttackSlam_R`
- `/Game/Monsters/HundredEyedSlag/V1/SK_HundredEyedSlag_V1_Skeleton`

保留 F6 与原生类引用、原皮肤材质、2K 纹理和高模烘焙、十万三角形 LOD0，按原设置从修订蒙皮生成三档 LOD，复用原拟合物理资产。本轮没有修改 C++，沿用 ClawV6 的已完成原生构建；没有调用 Meshy 或购买其他资产。

`Rebuild.ps1 -Stage Authoring` 制作与导出；`-Stage Install` 安装已有导出，默认两者。安装优先通过已有主编辑器的批次桥；主编辑器关闭时通过共享批次互斥启动无界面 commandlet。第一次 commandlet 保存目标网格被 Error 32 文件锁阻止，没有完成资产替换；随后等待持有共享资产的 FPSGAME-mp 运行实例释放，不关闭或操作这些游戏进程。实际导入完成以保存记录为准。

未作游戏视觉、攻击命中、布娃娃或帧率验收，最终大臂形态与收手效果由用户在 F6 试玩确认。
