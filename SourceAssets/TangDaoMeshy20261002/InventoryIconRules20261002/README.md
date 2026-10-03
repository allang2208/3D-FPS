# 唐刀背包图标规则同步

按冷钢设计规则第 7 节和现有 `ColdSteelMeleeIcon.cpp` 制作。读取游戏中已保存的唐刀原厂模块与材质，复用近战动态图标的正交侧视、刀尖朝上、384×768 透明竖幅及 91% 主轴取景。保留金属、黑红缠柄和龙纹的原生颜色。

`export_icon.ps1` 在后台定向运行 `ColdSteelWeaponIconCatalog -Definition=ue_tang_dao`，只制作 PNG，不运行游戏，不初始化玩家档案，不保存模型或材质。整批遵守现有 UE MCP 互斥。

`import_icon.py` 实际重新导入、保存原有两个库存 Texture2D，并同步正式 PNG、旧作者源和 SurfaceV2 图源。活动物品键继续是 `Icons/ue_tang_dao_surface_v2.png`；纹理使用 UI 组、sRGB、图标压缩、无 mipmap 和不流送。已安装改造仍由原有配方动态图显示。

旧 PNG 和纹理包保留在 `Before/`。实际出图、资产保存分别记录在 `export_receipt.json` 和 `import_receipt.json`。旧库存作者入口已改为调用本批 UE 出图，避免以后覆盖成旧 Blender 构图。未运行游戏或自动验收，由用户测试。
