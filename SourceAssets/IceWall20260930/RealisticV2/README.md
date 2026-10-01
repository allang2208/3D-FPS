# RealisticV2 冰墙表面作者源

`IceWallRealisticV2.blend` 和四份 FBX 为本地原创冰块。`T_IceSurfaceMasks.png` 的 RGB 分别为霜层、细裂纹、内部气泡，`T_IceSurfaceNormal.png` 为经过低通的浅融蚀高度法线；两张纹理均为本地程序化原创，不沿用初版粗裂纹贴图。

制作入口为 `Tools/Skills/author_ice_wall_realistic.py`、`prepare_ice_wall_realistic_maps.py`、`build_ice_wall_realistic.py`。运行资产保存到 `/Game/Skills/IceWall/RealisticV2`；完整说明及未测试边界见 `Docs/Skills/ice-wall-realistic-v2-20260930.md`。
