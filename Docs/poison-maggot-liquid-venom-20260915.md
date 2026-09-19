# 毒蛆黏液投射物

用户选定“浑浊绿色黏液团、细液滴尾迹、少量毒雾、撞击飞溅和短暂湿痕”。这是原投射物的表现替换，伤害主体仍为可躲避的毒滴。

## 制作与接入

- 投射物采用湿润半透明外层与较小的不透明浑浊内核。暗黄绿色、低粗糙度反光、流动法线与局部颜色变化替代旧的均匀球面；无自发光。外层顶点轻微起伏，体积近似守恒的伸缩与缓慢翻转由视觉时钟驱动。
- 每 0.065 s 沿实际飞行段留下细液滴，每三次附带一次淡雾。碎滴以较低速度拖在主体后方，轻微下坠并缩小消失；雾短暂扩散淡出，保留主要弹道的可读性。低帧率最多补四次外观发射，不影响主投射物的扫掠命中。
- 主投射物命中后发出九颗带下坠的碎滴和两缕轻雾，碎滴触及命中面即退场。世界表面增加不规则湿痕，4.5 s 后用 2.5 s 渐隐；命中玩家胶囊时只做飞溅，避免将贴花贴在不可见胶囊上。
- `UPoisonMaggotVenomFX` 使用每世界共享的 192 个碎滴、48 个雾片和 40 个湿痕槽位。碎滴和雾使用两组 InstancedStaticMesh；材质共享，循环复用，不为每粒创建 Actor 或动态材质。效果预算未作性能测试。
- 视觉使用独立随机流，不消费散布和中毒概率使用的随机数。沿用原始碰撞选择、一次伤害、中毒叠层、怪物死亡清理主投射物，以及当前原始基数 1.5 倍射程。预览世界不创建效果管理器。

## 资源与可编辑源

运行时代码：`Source/FPSGAME/Monsters/PoisonMaggotProjectile.*`、`PoisonMaggotVenomFX.*`。

制作脚本：`Tools/PoisonMaggot/build_venom_liquid.py`。

资源目录：`/Game/Monsters/PoisonMaggot/VenomLiquid20260915`。包含 `M_VenomLiquid`、`M_VenomCore`、`M_VenomDroplet`、`M_VenomMist`、`M_VenomWetFilm`。运行时代码直接引用新资源；旧 `VenomMaterial` 资源仍保留，但该投射物不再用它覆盖新材质。

程序化 HLSL 与制作记录：`SourceAssets/PoisonMaggotVenom20260915`。材质图案为本轮原创，几何使用引擎 BasicShapes Sphere/Plane，无外部素材下载。没有修改怪物骨骼动作。

## 构建与交付

材质通过 UE Python 制作命令导入和编译，不运行游戏、不生成预览。Substrate 湿痕必须经 `SubstrateConvertToDecal` 输出，否则其域会被推导成表面材质，无法使用贴花生命周期。

材质制作完成日志：`Saved/PoisonMaggot/venom-liquid-authoring-20260915-r2.log`，包含五个保存标记及 `VENOM_LIQUID_AUTHORING_COMPLETE`，命令退出码 0。重建图节点过程中有临时断线编译警告，所有图完成连接后经过制作脚本的最终编译并保存。

正式编辑器模块构建完成：`Saved/BuildEditor/build-20260915-090337.log`，结果 `Succeeded`。

本轮不执行游戏、画面或性能测试，效果交由用户实际体验。
