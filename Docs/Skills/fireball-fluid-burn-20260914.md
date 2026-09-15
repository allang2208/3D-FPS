# 火球：流体烘焙燃烧主体（2026-09-14）

用户要求游戏中的悬浮／飞行火球更接近一团真实燃烧火焰，并授权按建议调整。此次制作原创流体序列，接入既有 Niagara 主体及世界空间拖尾；快捷栏火红图标属于前一阶段，本轮不改图标。

后续镜头残影与外围热浪更新见 [火球镜头残影与悬浮热浪](fireball-motion-heat-20260914.md)，其中 `FireballHoverHeatHalo` 已接替本文最初制作的旧微弱热扰动层。

## 制作路线

用 Blender Mantaflow 做离线持续燃烧，96³ 基础气体网格、2 倍细节上采样，三个不规则、不同步供燃的源体；源体只参与模拟，不作为可见球壳。保留浮力、燃烧消耗和局部涡旋。模拟 144 帧、24 fps，前 48 帧作为建立燃烧的预热，其后 96 帧用于贴图生产。

`pack_fluid_atlases.py` 从模拟的火焰场沿两个正交方向进行体积光学积分，生成两张 2048×2048 RGBA 图集，每张 8×8、64 帧。使用 32 帧余弦交叠，在预乘线性颜色空间制作循环：最后一帧与下一轮第一帧来自原模拟相邻帧。运行时帧插值并错开各粒子的初始相位。RGB 是美术控制的热色发光，Alpha 是独立光学覆盖；颜色映射来自火焰浓度，不把该标量误称为实际温度测量。

这是实际流体模拟数据的离线烘焙，运行时使用平面粒子组合播放，不在每颗火球上实时运行 3D 流体。两个方向提供形态变化，不代表随相机切换的完整体积渲染。原始序列、模拟缓存及可编辑 Blend 留在本机供后续调整。

## Niagara 表现

- 主体仍使用 `/Game/Skills/Fireball/NS_FireballSlowBurnCore`，移除原 `FireballCore`／`FireballSlowRoil`／旧外焰发射器，换成两层原创燃烧主体、短外焰、稀薄烟与轻微热扰动。
- 新主体使用独立透明通道，发光在最终深度淡化之后预乘。保留世界深度，不叠加稳定的发光球壳或硬圆边；主色保留橙黄、局部亮黄及低热区红橙层次。
- 两个主体层生成率为 2.1／1.7 个每秒，寿命 0.85–1.2 秒，22–26 帧每秒独立播放；根部有小幅不同偏移。短外焰每秒 6 个、寿命 0.38–0.66 秒，依靠长短差异和各自的生命周期消散。
- 悬浮时贴图内的燃烧向上翻卷；发射后沿现有 60 ms 交接，将粒子根部与贴图朝向一起转到局部 -X，接续真实飞行速度的反方向。
- `/Game/Skills/Fireball/NS_FireballVelocityTrail` 换用新燃烧图集，继续从 C++ 提供的实际移动线段生成，出生时固定世界空间后向速度。寿命 0.08–0.135 秒、间距 14 cm、上限 240 个每秒，用尺寸差异和衰减形成短而破碎的尾焰。
- 稀薄烟和热扰动来自本机 Epic Niagara Examples 的专用实例；短火舌复用本机 Dr.Game Free Spline VFX 纹理及现有项目父材质。原资源包不修改。
- 原有点光源、脱手悬浮、收手／发射手势、碰撞、伤害、冷却、魔法消耗、修炼和存档不变。本轮无 C++ 修改，不需要原生构建。

## 文件与恢复

- 作者源：`SourceAssets/FireballFluidBurn20260914/author_fluid.py`、`Fireball_Fluid_Editable.blend`、`Cache/`、`Fields/`、`simulation.json`。
- 贴图烘焙：同目录 `pack_fluid_atlases.py`、`Textures/T_FireballFluid_A.png`、`Textures/T_FireballFluid_B.png`、`atlas.json`。
- 引擎作者入口：`Tools/Skills/build_fireball_fluid_burn.py`。新纹理和材质位于 `/Game/Skills/Fireball/FluidBurn20260914`。现有运行主体／拖尾路径原位保存，因此无需修改技能组件默认引用。
- 完整重建入口 `build_fireball_assets.py` 在原 slow_burn → outer_flame 后调用 fluid_burn；保留旧生成链及其输入。重建当前效果需要先恢复本轮两张原创图集；也可按模拟 → 贴图烘焙 → UE 导入顺序重新生产。
- 本轮首次修改前的两个系统文件保留在作者目录 `BeforeFluidBurn/`，作为回退输入；没有清理历史素材、缓存或归档。
- 同目录 `integration.json` 由 UE 制作脚本在完成资产保存后写出，制作进度分别记录在 `bake.log`、`atlas-bake.log` 与 `ue-authoring.log`。它们记录必要制作，不代表实机验收。
- 原创模拟／图集与第三方模板的来源分开记录；此次仅本机制作接入，无 Git 提交或推送。

## 首次制作的用户测试边界

本轮生产执行已完成：Mantaflow 数据／细节缓存与场导出结束，两张图集写出；UE 导入脚本以退出码 0 完成，记录 `FIREBALL_FLUID_BURN_INSTALLED`。主体和拖尾的必要 Niagara 编译均返回 `valid=1`，七项新纹理／材质与两个运行系统已保存。这些是制作结果，不是游戏测试结论。

本轮按用户规则不运行自动测试、静态检查、游戏、截图或验收。原生代码与玩法不修改；必要的模拟、贴图烘焙、资产导入和 Niagara／材质编译属于制作环节。实际近景体积感、曝光、火舌观感和性能由用户进入游戏判断。已开启的游戏可能持有旧资源，需要重新启动游戏读取更新。

## 后续修复：只见黑烟、不见火焰

用户随后明确要求“只见黑烟，不见火焰，排查调整”，因此本阶段进行了针对该故障的数据读取和独立 UE 渲染；没有运行主地图或玩法回归。

原因一：新主体材质遗漏了旧 Epic 父材质中的曝光补偿。高曝光场景会压低原始发光，而 Alpha 仍然遮挡背景，导致火焰看起来像黑烟。两张原始 RGBA 图集及火焰模拟场都有有效数据，问题不在原贴图缺失。主体 A/B 和短外焰现已加入 `EyeAdaptationInverse`；Alpha 与深度淡化保持独立，仍在最终覆盖率之后预乘。拖尾复用主体 B 材质，随同修复。

原因二：从 `NE_Core` 继承的 Sprite Renderer 仍指定旧爆炸图集 `T_ExplosionRoil_EOO_Loop` 作为多边形裁剪纹理，造成新火焰底部被旧轮廓切掉。主体、短外焰、薄烟、热扰动与拖尾共六个 Renderer 的 `CutoutTexture` 已清空，`bUseMaterialCutoutTexture=false`，覆盖范围交给各自材质透明度。生成器也写入上述两项修复，重建不会恢复旧错误。

定位渲染使用未保存的空白地图、实际 Niagara 系统、SceneCapture 和完整编辑器渲染循环。在普通曝光与手动曝光 Bias=-10 条件下复现和比对：修复前后一组高曝光画面的最高 RGB 从约 1/255 恢复至约 206/255，橙黄色火焰重新可见；普通曝光亮度基本保持。该条件用于隔离曝光问题，不代表主地图当前实际 EV。记录位于作者目录 `VisibilityProbe_before/`、`VisibilityProbe_after/` 和 `visibility-layers-editor.log`。

分层关闭烟／热扰动后仍存在裁剪，进一步定位到错误 CutoutTexture。清空后的两个系统已编译保存，六项属性回读均为 `CutoutTexture=None`，见 `cutout-fix.json`。最后一次渲染复查在启动阶段被项目 `AutoFootstep` 模块加载失败打断，见 `visibility-after-editor.log`；未修改该插件及项目配置。现有 after 截图反映曝光修复、裁剪清空之前的状态，不作为裁剪修复后的画面。

修复入口为作者目录 `fix_flame_exposure.py`、`fix_flame_cutout.py`；对应备份分别在 `BeforeExposureFix/`、`BeforeCutoutFix/`。未修改 C++ 或技能玩法参数。最终主地图中的悬浮／飞行观感仍由用户重新加载资源后测试。
