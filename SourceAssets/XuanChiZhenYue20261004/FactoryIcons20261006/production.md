# 玄螭镇岳原装图标修正 · 2026-10-06

- 补充原装剑身Ⅱ `ue_xuanchi_zhenyue_blade_2_false`：水平银色剑身，剑尖朝左，保留原装云纹蚀刻。
- 更新原装握把 `ue_xuanchi_zhenyue_grip_false` 与分类入口 `ue_xuanchi_zhenyue_category_grip`：共用一张横向图，原上端朝左，下端朝右，保留双段缠柄与中间金属箍。
- 使用内置 image_gen，来源为既有镇岳图标，唐刀握把仅作为横向构图参考。完整提示词与生成来源在 `prompts.json`。
- 两张源图保存在 `Icons/`；UE 目标为 `/Game/ColdSteelData/AttachmentIcons20260913/` 下上述三个同名 Texture2D。
- `ModelV1/deploy_part_icons.py` 已同步新源图引用；本次仅由 `deploy_icons.py` 更新三个目标 PNG 和对应部署记录，不执行整套旧图标覆盖。
- `install_icons.py` 导入并保存 UI/sRGB/不流送/无 Mip 的纹理资产，逐项保存状态记在 `import_receipt.json`。
- 旧目标文件保存在 `Before/`。仅修改图标，不修改实际模型、材质或玩法。

用户关闭 UE 后，通过无界面 commandlet 完成三项 Texture2D 导入与保存，逐项结果见 `import_receipt.json`；三项 PNG 和源部署记录也已落盘。UE 保持关闭。未运行游戏测试或截图验收，交由用户测试。
