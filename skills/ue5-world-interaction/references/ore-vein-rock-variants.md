# 矿脉岩块变体：矿种唯一真源、空间加权与重建路径（2026-09-30/10-02/03）

温带丘陵含矿岩块的完整约定。资产 `/Game/WorldGeneration/TemperateHills/OreRocks/`
（M_HillsOreRock 母材质 + MI_HillsOre_{Iron,Copper,Silver,Gold} + SM_LS_Rock_00A_{矿种} 四变体网格）。

## 1. 矿种唯一真源（渲染/掉落共用）

`ATemperateHillsWorld::RockOreDefinition(uint32 Key, const FVector2D& At) const`
——渲染端（变体网格替换）与采集结算端（TemperateHillsProduction 掉落）**必须调同一份判定**，
且传同一候选格心，否则"看见的矿"和"挖出的矿"会漂移。函数可改内部公式，但签名/共用关系别破。

- 空间加权（2026-09-30 用户要求矿围绕岩石地貌+河床）：保底 0.08 + 坡度 (1−N.Z)×0.45 +
  地表碎石斑（复用地表材质的 Dry 公式 Noise 1411/1417/1459，石相地面才像有矿）×0.40 +
  河床带（Wet>.3 或 Distance<HalfWidth +0.55，泛洪区 Bank 衰减 +0.25）。
  `Roll=Key%1000 < Weight×1000`，矿种=`(Key/1000)%100`（25 铁/12 铜/4 银/2 金）。
- 变体网格：`OreRockVariantMesh(Key, At)` 在 GetPlacements **坡面+河岸两分支**都要替换
  `P.Mesh`（路径硬编码两处，注释互指）；TemperateHillsStreaming Stage==2 追加 4 变体预载。
  纯石保留 4 网格轮换；含矿统一 00A 单形态（辨识度优先，用户拍板）。

## 2. 可采性 = 实例半径与 500cm 闸门（挖出过的教训）

采矿闸门拒实例半径 >500cm。原坡面 scale [0.7,2.1] 配 SphereRadius 884 时**全世界无可采岩块**，
"请寻找独立岩块"提示空转。定值：坡面 [0.30,2.00]（≈15.6% 可采小岩块+岩壁双峰）、
河岸岩 [0.30,0.75]（≈59% 可采，河床是可采矿的主要来源）；DA RiverRocks 必须填 4 网格，
空数组=河床零岩块。调分布先推这两处的可采比例，别只看材质。

## 3. 材质要点（细节见 debug-validation 的回落诊断参考）

- 岩底+矿脉带+晶点遮罩，遮罩区混 OreColor/OreMetallic/OreRoughness；
  VeinScale/SpeckScale 烧成 Constant（免疫本项目 VectorParameter 运行时读零病史）。
- 网格 UV0 不可信 → 局部空间双平面投影；法线混合权重从局部坐标推（PixelNormalWS 进
  Normal 依赖树=编译拒译回落灰材质）。
- 四个变体网格 Nanite 关闭（3.7k 面 ISM 批渲染无收益）。

## 4. 重建与验证（Content 资产不进 git，脚本即真源）

- 重建：`UnrealEditor-Cmd FPSGAME.uproject -run=pythonscript -script=Tools/Production/build_ore_vein_rocks.py`
  （重跑会整体重建母材质/MI/变体网格并落盘）。
- 读回验证：`Tools/Production/verify_ore_vein_visual.py`（表达式数/参数/槽位/颜色）。
- 渲染验证：`-run=OreVeinPreview`（配方与深坑见 [材质回落与 commandlet 渲染验证台](../ue5-debug-validation/references/material-fallback-and-commandlet-render.md)），
  产物 `Saved/OreVeinRocks/{plain,gold,iron,copper,silver}.png`。
- 已知遗留（2026-09-30 排查）：leadOre/sulfurOre（tribute 类）无获取途径，19+ 弹药配方
  引用它们=弹药链断；items.json 存在驼峰/下划线两套矿石命名分裂（ironOre 遗存 vs iron_ore
  实际掉落），合并视图查数值时注意。
- **实机验收欠**：离线四矿渲染 2026-10-03 确认可辨；游戏内色彩/可采手感未验。
