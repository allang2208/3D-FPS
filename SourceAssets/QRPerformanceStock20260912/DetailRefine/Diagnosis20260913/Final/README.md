# QR 后托限定范围修复记录

用户明确要求：排查改造面板穿模、上方材质不统一，并继续修复。仅检查这两项及拍摄其预览，未运行玩法、换弹或存档回归。

## 定位和修改

1. 上盖原材质是 `StockPolymer_Refined`，整块硬壳误用了非金属。作者源与 FBX 已改为金属槽，分别映射到对应枪身图集。
2. 布尔挖槽后仍保留旧法线，6 个平面面片的角点偏离超过 5 度，最大约 52.46 度。现在完成所有几何修改后重建法线，限定诊断中超过 5 度的面片数为 0。
3. 原上盖与 M4 尾板、AKM 尾舌的表面相交；AKM 转接盖板还与保留机匣边缘相交。已分别修改局部接口和内腔，保持枪根挂点及肩垫位置。
4. AKM 金属图集切块使用交替镜像连续采样，移除明显的纹理跳变接缝。

`housing_findings.json` 对冻结的实际枪身变形参考进行表面相交比较：M4、AKM 的上盖、前框、接环及 AKM 转接盖板均无相交记录。该结果限于记录中的静态装配参考，不代表动作或全部玩法通过。

## 游戏资源及画面

最终 UE 导入日志 `../import_final.log` 记录两款 `SM_QRPerformanceStock` 保存成功，并读回以下金属材质引用：

- M4：`/Game/Weapons/M4InfimaV3/Body_001.Body_001`
- AKM：`/Game/Weapons/AKMIntegration/SovietFab/M_AKM_Soviet_PBR.M_AKM_Soviet_PBR`

聚合物和橡胶为独立槽。工程已有的 `GameFeatureData` 设置错误仍导致 commandlet 非零退出；两款资源导入保存与该工程错误分开记录。

新进程使用独立预览存档 `QRRefinedPreview_20260913_01`，在改造面板选择 QR 配件后拍摄，未应用保存草稿：

- `M4_Gunsmith.png`：M4 改造面板斜视截图。
- `M4_Gunsmith_Side.png`：M4 改造面板侧视截图。
- `AKM_Gunsmith.png`：AKM 改造面板截图。
- `M4_Mount.png`、`AKM_Mount.png`：作者源按实际挂点组合的接口近景。

截图与源资产保留本机；最终操作测试交由用户。
