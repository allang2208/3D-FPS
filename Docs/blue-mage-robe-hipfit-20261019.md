# 法师长袍腰胯外鼓修复

用户截图显示持步枪的第三人称角色腰带下方两侧外鼓，腰部与裙摆过渡突然。本轮范围为蓝色法师长袍的腰胯、裙摆上段和对应衣内碰撞；同时完成此前已授权的三件套图标保存。

## 定位依据

当前 `ue_blue_mage_robe` 使用 Body/Jason 的 Owner 与世界身体四个布料网格，第一人称手臂另有共用的武器适配组。截图对应 Jason 身体外观；原生身体和作者源均在项目中留存。

1. 旧的 Jason 大腿采用 12.8 cm 等半径胶囊，端点中心直接落到髋关节。髋关节横向约 9.77 cm，碰撞可到身体中心外约 22.57 cm，原生髋部半宽约 16.63 cm。它把前后向所需厚度同时扩到了横向，并在髋上方留下过大的球冠。
2. 原裙摆从腰截面开始按 `t^0.82` 外扩，腰附近的扩张速度偏大，同时把腰部前后截面沿整个裙摆延续，造成臀后余量过多。
3. 静止参考姿态下，对裙摆低模代理与大腿碰撞做离线截面检查：Body 上段有 212 个代理顶点处于旧碰撞包络内，最深约 3.02 cm；Jason 为 320 个，最深约 4.08 cm。这能解释模拟开始后布料被向外推出的现象。该检查不是运行时布料截图或完整动作验收。

## 修复

- 腰带以下约 24 cm 身体尺度范围，以原生身体横截面的凸包建立腰胯轮廓，并保留约 0.8–1.3 cm 的衣物余量；再向原来的下摆轮廓渐进展开。腰线原点和下摆边界固定，前后截面分别跟随身体，避免只把整个裙子等比例缩小。
- 可见裙摆、隐藏布料代理以及裙底回折使用同一个变形场；拓扑、UV 和骨骼权重保留。
- 每侧大腿改为两条前后偏移的渐缩胶囊。中心段从髋到膝的 12% 延续至 95%，避免大球冠侵入腰部。Jason 上/下半径为 7.1/5.1 cm，Body 为 7.7/5.4 cm；原生骨骼局部缩放继续换算。
- 腰部固定区从约 6 cm 延伸到 10 cm，向下继续渐进释放。布料碰撞厚度从 0.65 cm 调为 0.35 cm，均乘身体尺度。
- 小腿、足部碰撞和此前恢复的小腿/鞋靴网格继续使用现行版本；23 个第一人称衣袖分支及武器动作不需要重新制作。

## 对照结果

Jason 参考姿态的髋部裙摆半宽从约 19.63 cm 调整到 18.04 cm，臀后位置由约 Y=18.19 cm 收至 Y=13.47 cm；大腿中上部半宽由约 22.08 cm 收至 19.08 cm。该数值是作者模型截面，不能当作所有运行时姿态下的固定尺寸。

对 Body、Body_Owner、Jason、Jason_Owner 的同一离线碰撞检查，新上段初始交叠数均为 0。四份模型的腰线位移、下摆位移、非裙摆顶点位移均为 0；拓扑、UV 和骨骼权重对照一致。完整结果在 `SourceAssets/BlueMageRobe20261018/HipFit20261019/geometry-comparison.json`。

## 制作与接入

- 作者入口：`Tools/BlueMageRobe/hip_fit.py`；完整 `author_body.py` 已接入同一腰胯处理，避免重新生成时回退。
- 碰撞作者代码：`Source/FPSGAME/Characters/FPSMageRobeAuthoring.cpp`。
- 构建与保存批次：`Tools/BlueMageRobe/run_hipfit.ps1`，使用现有 UE 互斥等待；必要的 Editor/Game 构建完成后，保存四个新修订身体、对应布料物理、更新展示/掉落，并保存长袍、帽子、手套的图标专用网格及 UI 纹理。
- 新身体资源目录：`/Game/Characters/ModularOutfit20260924/BlueMageRobe20261018/HipFit20261019/Body/`。
- `publish_hipfit.py` 只替换长袍 Body/Jason 世界与 Owner 四条引用；保留 `underlayer_meshes`、裤鞋和全部武器衣袖配置。
- 此次四份身体 FBX 与可编辑 Blender 源已更新，长袍的标准 PNG 与相机对齐展示数据同步使用新轮廓。

源文件和原图在 `HipFit20261019/Before/` 保留。原始粗截面记录 `initial-section-analysis.json` 中的 `leg_sections` 未排除手臂，未用于腿部碰撞标定；最终标定使用按大腿骨分支权重筛选的截面及上述完整裙摆代理距离检查。

实际 UE 保存状态见 `HipFit20261019/saved_assets.json`，目录接入见 `HipFit20261019/published.json`，三件套图标保存见 `SourceAssets/BlueMageSetIcons20261019/saved_icons.json`。构建或脚本完成与实际游戏效果分别记录；本轮不自动启动游戏进行视觉或动作验收。

2026-10-19 的 `hipfit-build-01` 已完成 FPSGAMEEditor 与 FPSGAME 两个目标的构建。首轮保存停在旧碰撞体记录读取处，尚未写入新身体；UE Python 未暴露 `PhysicsAsset.SkeletalBodySetups`。保存脚本改为记录实际网格与布料的物理资产绑定路径，碰撞尺寸与离线对照仍以作者代码及 `geometry-comparison.json` 为据，不把绑定路径回执当作碰撞形状读回。

最终落盘：`hipfit-import-03` 后台 commandlet 返回 0，四个身体版本均保存三档 LOD、连续裙摆布料及物理资产绑定；三个标准图标展示网格与 UI 纹理一并保存。随后 `publish_hipfit.py` 已切换四条身体引用，`published.json` 记录 `completed=true`、`calf_underlayers_unchanged=true`、`first_person_sleeves_unchanged=true`。所有武器继续通过共享身体配置使用此修订；未进行游戏内动作或布料验收。
