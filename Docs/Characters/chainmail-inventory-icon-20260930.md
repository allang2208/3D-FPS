# 灰钢锁子甲装备图标（2026-09-30）

用户要求按现行规则调整锁子甲装备栏图标。本轮仅制作正式图标与维护出图入口；SVD 首次空仓换弹色块仍按其独立待办处理，没有在本轮改动穿戴姿态或衣袖。

## 制作与落盘

- 物品 `ue_chainmail_shirt`，保持 3×3 占格。按现行图标管线输出 320×320 RGBA、透明底、竖直正交展示，按相机空间轮廓居中、主轴约 91% 填充。
- 来源改为当前活动 Body 锁子甲对应的 `SourceAssets/ChainmailInterlace20260929/Editable/Body_ChainmailShirt.blend`。只在独立展示副本中将双上臂各放低 12°，保留骨长与衣物比例；不出现皮肤、人台或其他装备。
- 保留当前 Interlace 的 BaseColor、Normal、ORM、物理锁环密度；离线材质补入旧出图器忽略的 ORM.R 遮蔽信息，使用中性柔光表现钢灰反射、暗色空领口与袖口。Blender 的 AO 合成属于离线表现，不能宣称与 UE 着色逐像素相同。
- 正式 PNG：`Content/ColdSteelData/Icons/ChainmailInterlace20260929/ue_chainmail_shirt.png`。原 `ue_icon` 路径保持，背包、装备栏、仓库继续共用。
- 同步当前作者源 PNG，以及 `ChainmailShirt20260928` / `ChainmailRelief20260929` 两个旧目录图别名，覆盖旧存档持有的路径。未修改物品属性、占格、配方、穿戴网格、世界掉落或动画。
- 原图备份、独立 `.blend`、正式作者 PNG 和生成回执均位于 `SourceAssets/ChainmailInventoryIcon20260930/`；备份在 `Before/`，回执为 `production.json`。

## 后续制作入口

`Tools/ModularOutfit/render_chainmail_inventory_icon.py` 为当前入口，使用 Blender 后台运行。`build_chainmail_interlace.inventory()` 已转入此入口，旧 `author_chainmail_shirt.py --presentation-only` 也识别当前 InsetBinding 家族，避免重新出图恢复旧平铺光滑衣身。

本物品图标由 UI 直接从目录 PNG 载入，不需要导入 Texture2D 包、编译 C++ 或启动 UE。后台制作日志 `Saved/chainmail-inventory-icon-20260930.log` 已记录 PNG 和可编辑源保存成功。

未运行游戏、UI 测试或验收截图。已打开的 UI 可能持有旧图缓存；下次进入游戏重新加载。游戏内效果由用户测试。
