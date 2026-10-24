# 公寓海湾远景：GitHub 调研与实现路线

检索日期：2026-10-22。目标是公寓窗外、跨海湾观察对岸的城市，不是可漫游的整座城市。

| 参考 | 可借鉴的部分 | 在当前 UE 5.8 项目的用法 |
|---|---|---|
| [Neon Zenith](https://github.com/billpwchan/neon-zenith) | 建筑造型规则、分层立面、按房间/租户分区的窗灯 | 对岸重要楼群保留实体轮廓；立面使用有深度的窗格和独立灯光遮罩。它是 Three.js 工程，不能作为 UE 插件直接接入。 |
| [GavinKG/ImposterGenerator](https://github.com/GavinKG/ImposterGenerator) | 分组捕获建筑的颜色、法线、深度等属性，制作远距离替身 | 参考捕获与材质分离方式。该仓库面向 UE4，不直接安装进 5.8。 |
| [UE 5.8 Impostor Baker](https://dev.epicgames.com/documentation/en-us/unreal-engine/impostor-baker-plugin-in-unreal-engine) | 多视角捕获、邻近视角混合、远距离 LOD | 若需要进一步降低超远楼群成本，优先采用引擎当前工具；替身保留材质数据，而非整片固定夜景照片。 |

[Procedural-cyberpunk-city](https://github.com/jhonatan98rios/Procedural-cyberpunk-city) 的 README 仍将生成核心列为待实现，未作为现成成熟方案选用。

## 判断

当前主要问题不只是模型面数：建筑形态重复、立面身份不突出，整片烘焙夜色又无法响应白天。继续提高相同方块和亮窗的密度，很难解决整体观感。

建议的美术重做顺序：先确定 3–5 栋有明确剪影的海湾地标及高低层分区，再制作少量有真实窗框、机械层和商业裙房的立面母版；从母版生成远处使用的颜色、法线、粗糙度和独立发光遮罩。中景与超远景按屏幕占比分层。近距离才有意义的细节不铺满整片对岸。

本轮没有导入第三方模型或执行外部仓库脚本；仅参考其公开设计和实现说明。若后续使用 Neon Zenith 的现成美术，需要分别遵循代码、模型和纹理的许可，见其 [Credits](https://github.com/billpwchan/neon-zenith/blob/main/CREDITS.md)。

## 本轮具体接入

V6 将现有源文件中的远城和岬角导出为三组受光照影响的静态几何，移除固定夜空球的显示；窗灯和招牌随现有天空的太阳高度淡入淡出。这样先解决昼夜兼容和天空遮挡，未将其称为建筑美术已经合格。

主城 UDS/UDW 地图实例直接复制到公寓，沿用 FPSWeatherManager 的权威时间与天气。水面保留原生 Clearwater／SingleLayerWater，针对远距离波纹加入像素覆盖过滤、位移距离过滤、较柔和的远处粗糙度；夜景反射去除硬边界盒投影和固定天空，仅保留低强度、预过滤的城市补偿。

本轮资产与地图均已保存：`assets_saved.json` 为 `assets_saved`，`installed.json` 为 `map_saved`；回执位于 `SourceAssets/CyberpunkApartmentRebuild20261022/RefinementV6/`。2026-10-22 17:10 完成公寓地图保存，241 个场景对象相对当前版本放大 1.25 倍，室内作者缩放从 1.2 变为 1.5；玩家体型和出生高度保持原值。天空和天气实例来自主城的临时关卡副本，迁入公寓后已卸载临时来源，没有保留主城子关卡。

没有运行游戏、截图或帧率测量；水面闪动改善程度仍需真实旋转视角确认。
