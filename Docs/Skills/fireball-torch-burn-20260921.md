# 火球燃烧表现：参考当前青铜火把

用户要求对照场景道具青铜火把的燃烧效果，优化或替换火球。沿用原技能、动作、悬浮位置、弹道、伤害、蓝耗、冷却、成长和命中爆炸，修改火球主体与飞行尾焰资产。

## 实际来源和取舍

读取 `BronzeTorch.cpp` 和当前 `NS_TorchFlame`、两层材质、渲染器与发射器堆栈；查看已有火把源预览。当前编辑器打开的是 `L_Dungeon_Prototype`，该编辑世界没有 `BronzeTorch` 实例，所以本轮使用类中实际引用的已保存火把系统作为参照，未更换地图或启动游戏拍摄。

火把系统为 `/Game/Props/RomanColumn20260915/NS_TorchFlame`；两层是 `NE_Flame_01` / `NE_Flame_02`，使用 `MI_TorchSoft_Flame01/02`。其父材质是 Vefects `M_VFX_Erosion`，以流动噪声、火焰/柔团遮罩与粒子消散参数形成燃烧，并非火焰动画图集。来源和参数读回在 `SourceAssets/FireballTorchBurn20260921/source-settings.json`、`material-contract.json`。

2026-09-18 曾经将火把两层直接叠在旧流体火球上，用户否定后回滚。本次改为替换原流体主体，采用紧凑亮焰与外围火舌两层；没有复用被否定的叠加成品，也没有修改青铜火把本身。

## 主体缺失修复（同日，当前版本）

用户实机反馈「只看得到燃烧效果，看不到火球主体」。排查确认正式系统只有 `TorchBurnVolume` 和 `TorchBurnTongues`；前者使用 `T_VFX_Dust_01` 遮罩、最大粒子透明度 0.38，并随寿命增加 dissolve。原主体已移除，新的“体积层”仍然只是会消散的火苗／烟尘片，不能持续维持火球轮廓。读取记录为 `SourceAssets/FireballTorchBurn20260921/body-repair-diagnosis.json`。

- 用 `TorchBurnCohesiveCore` 替换失效的 `TorchBurnVolume`；保留外层 `TorchBurnTongues` 和本轮之前的尾焰设置。
- 内核为中心位置固定、30 × 30 cm 的单个镜头朝向粒子，SpriteSize 继续随凝聚缩放。`Unaligned + FaceCamera` 让它不受外焰局部 -X 对齐影响，避免沿飞行方向观看时截面退化。
- 内核生成一次；SpawnBurst 数量受 `Engine.Emitter.TotalSpawnedParticles` 限制，不随发射器循环叠加。移除内核的 ParticleState 寿命淘汰，持续存在至投射物命中 `DeactivateImmediate` 或销毁；外焰仍按自身寿命消散。
- 新材质 `TorchBurn20260921/M_FireballCohesiveCore` 用火把现有灰度噪声做两路流动采样。球面厚度影响暖黄／橙红明暗，中心保持 0.82–0.94 光学覆盖，外围宽柔边叠小幅不规则扰动；不使用 dissolve 切穿内核，也不靠整体暴亮补轮廓。
- AlphaComposite 在最终透明度和 4 cm DepthFade 后预乘；保留曝光补偿、NiagaraSprites、AfterDOF、深度检测，并关闭透明速度写入。噪声贴图实际为 Linear Grayscale，采样类型已按源纹理修正。
- 正式路径仍为 `NS_FireballSlowBurnCore`。原版本与修复前版本分别保存在 `Before/` 和 `BeforeBodyRepair/`，SHA-256 写入 `install_core.json`。

内核材质、候选系统与正式系统已在运行的编辑器中通过项目 MCP 桥编译保存；输出为 `body-material-grayscale-mcp.txt`、`body-candidate-core-mcp.txt`、`body-install-core-mcp.txt`。未运行 PIE 或游戏观感测试，由用户重新施放测试。无 C++ 修改，不需原生构建。

## 初版表现（主体层已被上述修复替换）

- `TorchBurnVolume`：柔团火焰遮罩，10 个/秒，寿命 0.62–0.84 秒；25–29 × 27–31 cm，填充紧凑燃烧体积。
- `TorchBurnTongues`：与火把一致的火舌遮罩，15 个/秒，寿命 0.48–0.73 秒；13–19 × 27–35 cm，在小范围内错开位置和相位。
- 橙红外焰、暖亮内焰；出生淡入、尾段消散，动态 dissolve 从 0.06 增长到 0.86。去掉旧流体图集主体及其独立短外焰、烟片和环状热扰动，避免多套火叠成一团。
- 材质复制自火把，独立父材质与实例存入 `/Game/Skills/Fireball/TorchBurn20260921`。保留噪声侵蚀，改 Unlit、保留深度检测和 5 cm 深度淡化，加入曝光补偿；实例发光为 5.5 / 7.0。该数字含曝光补偿，与无补偿的火把 12 / 24 不作亮度比例对比。
- 凝聚时 SpriteSize 显式乘 `Engine.Owner.Scale.x`，与既有 C++ 凝聚缩放同步；不再只有粒子位置缩放而火苗一出生就是全尺寸。
- 发射后 0.08 秒从上燃转为局部 -X 尾焰，局部 +X 继续由已有投射物代码按真实速度定向。
- 新渲染器明确绑定 `Particles.SpriteAlignment`。旧流体渲染器虽然选择 CustomAlignment，实际绑定仍是已经移除的 `Particles.ShapeLocation.ShapeVector`。
- 世界空间尾焰改用相同火焰材质，按速度/18 cm 发射，上限 160 个/秒，0.06–0.095 秒寿命，粒子沿真实飞行方向反向对齐和消散。
- Vefects 发射器保留 `Life Cycle Mode=System`，没有套用旧主体 Self 模式；保留 NiagaraSprites 材质用途，关闭透明速度写入，避免与 DepthFade 冲突。

## 接入和恢复

运行路径保持 `/Game/Skills/Fireball/NS_FireballSlowBurnCore` 和 `NS_FireballVelocityTrail`。新增独立候选系统编译后，再按同一作者函数重建这两个正式系统；不修改 C++，不需要原生重编译。

作者脚本：`Tools/Skills/build_fireball_torch_burn.py`。完整重建入口 `build_fireball_assets.py` 也已在旧基础链之后追加该版本，避免日后重建退回流体主体。`materials` 阶段包含当前内核材质，亦可单独调用 `run('body_material')`；其余入口为 `run('candidate_core')`、`run('candidate_trail')`、`run('install_core')`、`run('install_trail')`。

正式系统改动前备份在 `SourceAssets/FireballTorchBurn20260921/Before`，对应安装回执保存原始 SHA-256。原火把、Vefects 母版与现有命中爆炸资产不写入。本机既有第三方素材沿用现有项目来源，不新增下载，也不公开发布二进制。

## 制作状态

材质、主体候选和尾焰候选均已编译保存；两个正式运行系统也已通过项目 MCP 桥完成更新、编译和保存。安装回执为 `install_core.json`、`install_trail.json`，对应桥输出为 `install-core-mcp.txt`、`install-trail-mcp.txt`。无需 C++ 构建，重新进入试玩后重新施放即可使用更新的资产。

本轮未启动 PIE、未跑战斗回归、未渲染新版预览。资产编译不代表观感验收，实际表现交由用户测试。
