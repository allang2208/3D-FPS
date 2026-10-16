# 鸭舌收束器 V2：全新模型

后续用户要求封闭两侧，活动网格与图标已由相邻 `Super90DuckbillClosedSides20261016` 管线继续修订。后续重导请使用该目录；本目录保留双唇基础模型，不要直接覆盖当前封闭侧壁版本。

用户否定前版外观后，重新从基础网格制作本版。`author_model.py` 不导入其他配件网格，也不调用旧版壳体生成器；`prepare_pipeline.py` 仅复用既有导出、材质导入和图标制作工具。

## 外观

- 前端是上下分离、向前扩宽的双层鸭舌，前方与侧面保留实际开口。
- 两片唇板具有连续圆角截面、独立边缘高光带、逐段收腰过渡及几何浅槽。
- 后部重新制作肩壳、棱面安装环、刻槽圆环与上下沉入式紧固件；凹槽与紧固件驱动槽为几何细节。
- 五个材质区域分别表现深灰主体、安装座、暗凹面、加工唇缘及紧固件。复用已接受的 WS1 母材质和平整法线，保留表面平整度。
- 原厂枪口接座位置沿用宿主实际接口；低矮下缘继续适配加长弹仓。新模型出口位置同步更新发射挂点。

## 模型文件

`ShotgunDuckbillV2_Editable.blend` 保存七个可编辑部件。`Exports/` 提供 FBX、GLB 和三级 LOD 组，LOD0/1/2 分别为 9364 / 4752 / 1948 三角面。远级保留双唇轮廓，减少小槽和紧固件。

`References/shotgun_duckbill_actual_model.png` 是实际 Blender 模型的图标制作参考，不是 UE 游戏截图。正式金属框图标 `muzzle_shotgun_duckbill.png` 使用内置 imagegen 编辑生成，完整输入和提示词在 `generation_prompts.json`。

## 游戏接入

- 配件：`shotgun_duckbill`，SUPER90 枪口槽，特殊改造。
- 多弹丸横向扇形展开，腰射/ADS 均生效；独头弹仍为单发。
- 用户确认的附加属性：腰射散布倍率 `0.75`，没有普通收束器的 `0.65` 弹丸散布倍率。
- 弹丸数量、总伤害、射程、弹速、后坐力、开镜耗时保持原有规则。腰射误差仍可使整束弹丸偏移。
- 本地射击、客户端预测、服务端使用同一个横向扇形函数；远端沿用已算好的弹道方向。玩法判定来自装备配方，不依赖网格加载成功。
- 当前资产根目录：`/Game/Weapons/CommonShotgun/DuckbillV2_20261016`；旧 V1 外观不再由游戏引用。
- 模型、材质及两个图标 Texture2D 的实际保存记录见 `install_receipt.json`，构建记录见 `build_*_receipt.json` 或 `livecoding_result_*.json`。

未启动试玩或运行验收；装配、表面、ADS、存档与联机效果由用户测试。

2026-10-16 已完成导入与保存，`install_receipt.json` 的 `complete` 为 true。Editor 与 Game 两个 Win64 Development 常规构建均成功、退出码 0，未重开 UE。第一轮构建遭遇炼金工作台并行修改中间态；当前头文件同步后重新构建成功，本任务没有改动该模块。

## 2026-10-16 整理记录

本目录已确认退役的备份、候选或一次性操作已移至本机 `trash/weapon-attachments-retired-20261016/SourceAssets/Super90DuckbillV2_20261016`。原文的 Before/旧候选路径属于历史记录；当前恢复依赖已保留。准确清单、替代物及本轮发布边界见 [整理发布说明](../../Docs/Publication/WeaponAttachments20261016/README.md)。
