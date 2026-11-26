# 钢制头盔第一人称开口拓宽

用户反馈锁子甲配套金属头盔的中央视野过小，要求先调整第一人称的上下开口。

现役入口为 `player_body.json → head_equipment → ue_steel_armet → first_person_overlay`，由 `FPSHelmetVisorWidget` 将透明视野层铺满当前玩家视口。当前 V5 开口高度约为画面的 19.8%，宽度约为 90%。

本轮将上、下轮廓各外移画面高度的 6%，中央可视高度调整为约 31.8%。在 Blender 中重新生成同厚度的内壁、倒角和皮衬，侧壁沿原宽度连接；下方缝线与铆钉跟随下沿移动。相机 FOV、准星和瞄准射线沿用现状。

只制作并切换第一人称透明贴图，第三人称头盔、掉落网格、装备图标和属性均沿用当前配置。V6/V7 外部造型候选不属于这次调整。

- 制作入口：`Tools/SteelArmet/author_reference_visor.py --vertical-padding 0.12 --production-only`。
- 源与回执：`SourceAssets/SteelArmet20261019/FirstPersonWide20261020/`。
- 独立材质贴图包：`/Game/Characters/ModularOutfit20260924/SteelArmet20261019/FirstPersonWide20261020/T_SteelArmet_VisorWide`。
- 接入：`save_wide_visor.py` 保存新纹理，`publish_wide_visor.py` 只替换上述 overlay 字段并保留配置前态。

后台已生成可编辑内壁源和 3072×1728 透明纹理；`first-person-wide-save-01` commandlet 退出码为 0，新纹理已保存，`saved_assets.json` 和 `published.json` 已记录完成。当前配置已指向独立的宽开口纹理，C++ 无修改、无需重编。

本轮只渲染游戏所需的透明纹理，没有生成验收图、启动编辑器或游戏、操作当前试玩角色。配置在玩家组件 `BeginPlay` 读取，下一次进入试玩生效；实际视野由用户自行试玩确认。
