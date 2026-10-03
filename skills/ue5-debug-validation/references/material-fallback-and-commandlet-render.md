# 材质回落默认材质诊断 + commandlet 渲染验证台（2026-10-02/03，矿脉岩块案）

适用症状：材质在游戏或 commandlet 里渲染成**均匀灰/默认材质外观**，或离线渲染验证反复全灰。
案例正本：`/Game/WorldGeneration/TemperateHills/OreRocks/`（M_HillsOreRock 家族）；
复用工具：`Source/FPSGAME/Production/OreVeinPreviewCommandlet.cpp`（渲染验证台）、
`Tools/Production/build_ore_vein_rocks.py`（材质重建）、`Tools/Production/verify_ore_vein_visual.py`（资产读回验证）。

## 1. "均匀灰"是双层病，先分层再动手

- **第一层 UV**：外购/旧网格家族的 UV0 可能从未被维护——先看同族原版母材质是否根本不用
  TexCoord（VertexBlend 类常用 VertexColor+材质函数）。若原版就不用 UV，你的新材质按 UV0
  采样只能拿到同一常数像素=均匀灰。修法不是补 UV，是**局部空间双平面投影**：
  `WorldPos−ObjectPositionWS`（ISM 逐实例正确）取局部坐标，顶面 XY / 正面 XZ 两套投影按
  朝向权重混合，每贴图 2 采样。python 名：`MaterialExpressionObjectPositionWS`（非
  ObjectPosition）；TextureSample 坐标输入名=`UVs`；LinearInterpolate 输出无分量通道名，
  取分量要加 ComponentMask。
- **第二层编译**：母材质 SM6 编译失败会**静默回落默认材质**，日志只有一行
  `Failed to compile Material for platform` —— **错误原文就贴在这条告警的下一行**
  （本案绕了 AssetLog、-unattended、二分重建一大圈，最后 grep 告警上下文两行就拿到：
  `(Node PixelNormalWS) Invalid node PixelNormalWS used for Normal input`）。
  Normal 输入的依赖树必须是切线空间树，把 `PixelNormalWS` 拿去算法线混合权重=拒译。
  修法：权重改从已有局部坐标推导（`saturate(1.6·|Z|/(|Y|+|Z|))`），两套投影共享。

## 2. 诊断歧路上的三个坑（全部实测）

- `MaterialEditingLibrary.recompile_material` **返回值不可信**：连单贴图最简材质也报 False，
  不能用它做二分判据；真判据是渲染 commandlet 日志里的编译告警行。
- `-unattended` 会**禁用 AssetLog 落盘**（Saved/AssetLogs/ 为空）；要资产级日志就去掉它，
  但最终仍以告警行上下文最快。
- Nanite 网格需要材质 `bUsedWithNanite=True`（缺失=额外一条 "needed to set usage flag
  Nanite" 回落）。低面数网格（本例 3.7k 面 ISM 批渲染）直接关 Nanite 更省事，与项目导入
  管线先例一致——渲染/解析两端不必为此改代码。

## 3. commandlet 渲染验证台（OreVeinPreviewCommandlet 配方）

`-run=OreVeinPreview -AllowCommandletRendering -RenderOffscreen -NoTextureStreaming -unattended -nosplash`
（**漏 -AllowCommandletRendering = RT 资源根本不创建**）。结构要点：

- RT/组件在普通 C++ 成员里会被 GC：`AddToRoot`；读回用 `FRHIGPUTextureReadback`，`Lock`
  必须在 `ENQUEUE_RENDER_COMMAND`（渲染线程）内，轮询=反复 enqueue+Flush。
- 无主组件进 FPreviewScene 不上屏 → `SpawnActor<AStaticMeshActor>`+AddToRoot。
- 正交相机在 commandlet 下会平面裁掉一切，用透视相机。
- **单岩石能成像、多组件排队缺席**时别缠：逐个拍（每块单独居中出一图）直接给答案。
- 对照实验锚点：跑一个 proven 的旧 commandlet（如武器图鉴目录）证明环境无恙，问题在自建
  场景；再跑"原版网格+新材质"决定性实验分离网格/材质嫌疑（测完移除覆写重编）。
- 判读用日志像素统计（nonzero/max/avg）+ 直接读 PNG，双矿种各一张确认区分度。

## 4. 状态记录口径

- 2026-10-03 离线验证：四矿种（金/铁/铜/银）渲染图 `Saved/OreVeinRocks/` 一眼可辨、编译
  零失败、FPSGAMEEditor 构建含本 commandlet Succeeded。
- **游戏内实机验收至今未做**——离线渲染 PASS 不等于游戏内 PASS，交接时如实注明。
