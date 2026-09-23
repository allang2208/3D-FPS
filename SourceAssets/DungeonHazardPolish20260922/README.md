# 排水坑腐蚀粘液与破墙材质

目标：`/Game/GameMaps/L_Dungeon_AuthoredExpansion`。新增 `DungeonPusChannel` 原生类，实现与胖子僵尸同类型、同默认数值的腐蚀魔法接触伤害；环境池长期存在，桥面及离地人物不受该地面接触判定命中。

- `Scripts/author_materials.py`：原创骨料混凝土的 2K PBR 与 16 位高度图。
- `Scripts/author_slime.py`：沟内细分液面和可编辑 Blender 源；运行时波动交由材质完成。
- `Scripts/import_materials.py`：专用断口材质实例与绿色流体材质。喷泉贴图包含线性存储法线和压缩法线，按实际压缩格式选择采样器与解码，不能统一强行 Normal 采样，也不修改喷泉的共享贴图设置。
- `Scripts/read_inputs.py`：读取本地图的神像与相关房间引用，供作者操作使用。
- `Scripts/complete_scene.py`：在缺口后口袋空间中唯一识别神像，记录绝对目标朝向，再导入三组网格和保存场景；不累积旋转。
- `Scripts/install_scene.py`：安装危险区域及神像方向，保存本地图所属外部 Actor 包。

必要原生构建使用项目普通 Editor 构建；`build-and-prepare.ps1` 持有与 MCP 相同的互斥锁，只在编辑器已关闭时运行构建和离线接入，不关闭占用中的编辑器。当前编辑器可用且已加载新增原生类时，通过 MCP 执行 `prepare_assets.py` 即可。

断面和碎砖作者规则位于 `DungeonRoomShells20260922/Scripts/room_detail_geometry.py`，整场生成配方中的 `trench.hazard` 也已接入新环境池。原怪物粘液、喷泉、已认可的墙裙剥落保持独立依赖。

完成状态以 `Receipts/materials.json`、`Receipts/meshes.json` 和 `Receipts/install.json` 为准。导入和保存不是实机效果验收；未执行自动测试、PIE 或渲染，由用户测试。
