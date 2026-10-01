# 暴风雪本机制作源

`blizzard_meshes.blend`、`SM_BlizzardHail.fbx`、`SM_BlizzardSpike.fbx` 由 `Tools/Skills/make_blizzard_meshes.py` 在 Blender 后台生成。主体使用一米标准尺寸，UE中按雪团22–40厘米、冰锥42–72厘米实例缩放；尖端沿模型+Z，运行时朝地面法线反向旋转。

UE作者 `Tools/Skills/build_blizzard_assets.py` 将模型实际导入 `/Game/Skills/Blizzard`，制作/编译/保存专属材质与三个 Niagara。冰锥材质只读复用已导入 `/Game/Skills/IceWall/FabIceV3/M_IceWall`；霜痕使用同目录 Color sampler 正确的冰面纹理。烟雾依赖既有冰锥图集和 Niagara 作者工具，并非独立发行包。

原技能图标来自本机原项目 `E:/无尽轮回/长期备份/2026-7-13-1/game-dev/assets/skills/blizzard_icon.png`，复制到冷钢数据目录；起手与命中音使用项目中已迁移冰系音效。第三方素材沿原来源/许可保留在本机，不能将 Fab 资产本体随公开源码再分发。

实际资产保存回执为 `Saved/BlizzardMigration/asset-authoring.json`。制作与原生构建记录见 `Docs/Skills/blizzard-migration-20260930.md`；未运行测试或渲染，用户自测。
