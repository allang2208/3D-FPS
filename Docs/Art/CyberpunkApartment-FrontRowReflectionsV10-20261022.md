# 公寓前排广告屏与动态水面倒影 V10

目标地图 `/Game/GameMaps/L_CyberpunkApartment`。制作源 `SourceAssets/CyberpunkApartmentRebuild20261022/RefinementV10`，资产目录 `/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV10`。

## 广告牌布置

六块屏幕从后排地标移到既有 City_1 / City_2 沿岸第一排高楼的临湾立面。沿用原屏幕 Actor、广告图集与播放内容，重新制作支架的布置，不留下后排重复屏幕。广告牌正面朝向公寓所在岸；位置与支撑深度按各楼的实际分段立面确定。

| 屏幕 | 沿岸楼宇作者 X 坐标 | 游戏世界屏幕宽 × 高 |
| --- | ---: | ---: |
| NEXUS 主屏 | -943.4 m | 55 × 77.5 m |
| ESTUARY 主屏 | -363.1 m | 37.5 × 55 m |
| TIDELINE 主屏 | -63.1 m | 43.75 × 65 m |
| PORT 主屏 | 386.3 m | 37.5 × 45 m |
| NEXUS 横屏 | -943.4 m | 47.5 × 8.75 m |
| ESTUARY 横屏 | -363.1 m | 50 × 7.5 m |

`design.py` 是屏幕位置、尺寸、广告相位与反射位置的共同来源。金属支架继续复用 V7 PBR 材质；显示网格复用 V8，不重复制作图集。

## 水面表现

从现有 V7 水材质派生 `MI_AP10_BayWater`，保留原 Clearwater 波谱、V6 像素尺度过滤、距离位移过滤、原城市补充反射、动态天空、吸收与散射设置。仅对公寓的 `BAY_Water` 替换材质，不改全局水体或光照配置。

- 广告反射按水面点、玩家视点和已过滤的波浪法线计算反射方向，再投射到六块真实广告面的同一世界坐标。广告换帧、滚动、颜色与原屏共用 `shader_sources.py` 的动画代码。
- 六道探照光束的反射使用 V9 同一位置、长度、颜色、俯仰／横扫周期与相位，随水波和扫动变化。
- 这些是针对既定远景发光物的解析反射补充，叠加在原水体上；没有增加全场景反射捕获，也不承担任意新增物件的完整遮挡求交。

## 稳定性与预算

- 倒影直接写入现有水材质，不另叠接近共面的透明水片，避免新增深度冲突。
- 使用连续 mip 级别、屏幕像素覆盖范围与粗糙反射宽度共同过滤；图集采样限制在所属格内，减少远距串格和锐利亮点跳变。
- 倒影边缘与探照光束轮廓平滑衰减，设反射亮度上限；没有帧随机噪声或间隔跳帧刷新。
- 新增 0 个 SceneCapture、0 个视频解码器、0 个 Tick Actor、0 张纹理和 0 个额外水面绘制层。复用两张广告图集；每像素广告采样上限 10 次，并在倒影覆盖区域外跳过采样；探照光束不采样纹理。
- 保留硬件光追、Lumen、原水面反射与天气基线。实现预算不等于实测帧率收益。

参数入口为 `MI_AP10_BayWater`：`AdReflectionGain=0.8`、`BeamReflectionGain=0.7`、`ReflectionNormalWeight=0.65`、`ReflectionBlur=0.009`、`ReflectionMaxRadiance=1.8`。提高 Blur 会让倒影更柔和；屏幕位置或动画参数改动应通过同一作者源重新生成水材质，维持对应关系。

## 交付

`publish-01` 已完成后台导入和地图保存；`compile-02` 完成三份新增主材质的 PCD3D_SM6 着色器编译及保存，通过引擎 `FinishCompilation` 等待完成。制作记录为 `assets_saved.json`、`installed.json`、`material-compilation.json` 与 `completed.json`。V9 安装链已接续 V10，重装前版会恢复本轮布置。

支架 FBX 初始导入记录了近零切线／副法线提示，保存前设置全精度 UV、Mikk 切线重建与 Nanite 完整回退。未进行游戏、画面验收、截图或性能采集，最终观感与实际帧率由用户体验确认。
