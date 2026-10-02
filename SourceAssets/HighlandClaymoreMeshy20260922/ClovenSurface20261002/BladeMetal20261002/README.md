# 裂角护手沿用剑身金属（2026-10-02）

用户认为上一轮翼面较清楚，但要求护手采用剑身的金属材质。本轮从当前 `/Game/Weapons/HighlandClaymore20260922/Materials/M_HighlandClaymoreSurface` 复制现用材质图，只将其四路纹理输入替换为适配翼面 UV 的同源贴图；没有另定金属底色、粗糙度或法线强度。

直接把剑身整剑图集绑定到护手的新 UV，会采到符文、皮革、宝石和纹饰区域，因此需先从实际剑身钢面三角形取得纯金属样片，再按样片物理尺度转移到底色、法线、金属度及粗糙度。小块样片边界做周期衔接，避免重复接缝；翼面原纹饰边和根部过渡沿用原图集，法线转入连续 UV0 的切线基。

- 原料：高地剑 `Meshy/candidate01/downloads/texture_0*.png`，与剑身 UE 四张贴图同源。
- 几何与 UV：沿用前一轮 `Highland_ClovenGuard_ArcSurface20261002_Editable.blend`，本轮不重导网格。
- 可编辑源：`Highland_ClovenGuard_BladeMetal20261002_Editable.blend`。
- 贴图：`Textures/T_ClovenBladeMetal_{BaseColor,Normal,Metallic,Roughness}.png`，均为 2048。
- UE 材质：`/Game/Weapons/HighlandClaymore20260922/ClovenSurface20261002/BladeMetal/M_HighlandBladeMetal_Cloven20261002`，是剑身材质图的独立 UV 适配副本。
- 安装只改当前裂角护手的 `M_ClovenWingSurface20261002` 槽材质绑定；中央宝石、原生材质与暗槽、赤红嵌纹槽保留。
- `author_blade_metal.py`、`author_textures.py` 与 `texture_recipe.json` 记录取样和生产；`install_blade_metal.py`、`install_receipt.json` 与 `Before/` 记录资产保存及替换前备份。

导入入口：上一层 `install_background.ps1 -Script <本目录/install_blade_metal.py 的绝对路径>`。后台制作不启动编辑器；已有编辑器时由原互斥桥执行材质导入与保存。只有安装回执 `complete: true` 才表示已保存到当前活动网格，脚本或贴图制作完成不表示接入完成。

本轮已完成后台导入、材质编译与保存。安装时没有运行中的本项目编辑器，执行的是 commandlet；`install-20261002-005858-594.log` 输出 `CLOVEN_BLADE_METAL_INSTALL_COMPLETE`，退出码 0。四张贴图、剑身材质适配副本和当前护手网格均已保存，回执 `complete: true`。

未启动游戏、截图、测试或验收渲染。用户反馈仅确认上轮表面相对优化，不代表本轮金属材质已获视觉验收。
