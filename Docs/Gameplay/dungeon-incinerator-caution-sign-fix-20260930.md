# 灰坑注意高差牌位置修正

用户截图指出「注意高差 / 保持检修通道畅通 / 请走楼梯」告示牌与栏杆穿插。原牌中心为作者坐标 `(-9.31,-2.525,0.75)`，牌身横跨 x=-9.45 的立柱，背板进入栏杆厚度。

本批将其中心调整为 `(-9.025,-2.43,0.75)`：沿栏杆平移 28.5 cm，居中到 x=-9.45 和 x=-8.60 两根立柱之间；向通道侧外移 9.5 cm，高度不变。两侧距立柱约 7.5 cm；背板也位于栏杆前侧。增加两条连接中横杆的支架，承接牌体。

位置由 `SourceAssets/DungeonIncineratorHall20260929/AshStation20260930/Config/layout.json` 的 `caution_sign_position_m` 维护；原建模函数同步使用此参数。沿用原有牌面贴图、单一实体正面及其他接灰区牌的位置。

局部制作目录为 `SourceAssets/DungeonIncineratorHall20260929/CautionFix20260930/`：

- `Scripts/author_fix.py` 只导出接灰区标牌组合。
- `Authored/AshSigns_CautionClearanceV4.blend` 为本批可编辑源。
- `Scripts/install_fix.py` 导入新包 `/Game/Dungeons/IncineratorHall20260929/CautionFixV4/Meshes/SM_Incinerator_AshSigns_V4`，复用原标牌材质，仅替换地图中接灰区标牌组合的网格引用。
- 主体重建链在接灰区与地面标识安装之后追加本修正；后续重装不会恢复旧牌位置。
- `Backup/` 保留首次编辑前地图，`Receipts/install.json` 以 `stage=caution_sign_position_saved`、`map_saved=true` 表示实际地图保存完成。

不改栏杆、翻下规则、设备、地面划线与其他标牌。未运行游戏、PIE、截图或渲染验收，实机效果由用户查看。
