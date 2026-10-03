# 高地·双手剑：背包兜底图标修正（2026-09-23）

## 症状

高地·双手剑在背包／仓库格子里的贴图与其他近战武器不一致：剑身横躺、只占格子约四分之一高度。符文长剑正常，寒晶·双手剑在捕获未就绪时是空格子。

## 根因

近战图标有两层，`ColdSteelInventoryWidget::ItemBrush`（`Source/FPSGAME/UI/ColdSteelInventoryWidget.cpp:114-118`）优先用运行时场景捕获，捕获未就绪或超预算时退回 `Icons/<definition>.png`：

- 运行时捕获：`ColdSteelMeleeIcon.cpp:32-42` 按包围盒最长轴把剑身立起（`ColdSteelMeleePreview::Rotation(..., Portrait=true)`），渲染目标固定 **384×768**，长轴占画面 91%（`/.91f`）。
- 兜底 PNG 的设计约定是**由同一套捕获代码离线产出**，见 `SourceAssets/WeaponInventoryIcons20260913/README.md:13`。

`ColdSteelWeaponIconCatalogCommandlet.cpp:20` 的默认清单里有 `ue_rune_sword`，但**没有** `ue_highland_claymore` 和 `ue_frost_crystal_sword`。于是：

| 武器 | 兜底 PNG | 实测构图 |
|---|---|---|
| `ue_rune_sword` | 由 commandlet 生成 | 384×768，bbox 229×697，纵向填充 **90.8%**，中心 (0.5, 0.5) —— 与捕获一致 |
| `ue_highland_claymore` | 来自 `Integration/render_menu_icons.py` 的**改造件机位** | 1024×1024，bbox 849×259，纵向填充 **25.3%**，剑尖朝左 |
| `ue_frost_crystal_sword` | **文件不存在** | 无兜底，捕获失败即空格子 |

高地那张是 Blender 配件棚拍脚本的 `inventory` 任务直接复用了配件机位（`ortho_scale=size/.83`，长轴横向），从未走过引擎捕获通道。

触发条件不是必现：`Saved/Logs/FPSGAME-backup-2026.09.23-13.47.36.log` 里同一条目连吃 5 次 defer（2/4/6/8/8 秒，reason 依次 `MaterialShader`→`TextureStreaming`）后按 `Icon.ReadinessBudget` 判失败并整局不再重试；而 14:56 那轮只 defer 3 次就 `ready key=ue_highland_claymore|...`。纹理流送与材质就绪一慢，玩家看到的就是那张错图。

## 改动

- `Tools/UI/build_weapon_catalog_icons.ps1`：新增 `-Definitions`，按条目逐个传 `-Definition=`（当前已构建的二进制即支持该参数，**不需要等重编**）；每个条目先备份再跑；进程退出码不可靠（GameFeatureData／端口噪声会导致非零），改以 PNG 时间戳是否前进判定结果，并回显 `ICON <id> written=.. size=WxH ..`。
- `Source/FPSGAME/UI/ColdSteelWeaponIconCatalogCommandlet.cpp:20`：默认清单补 `ue_frost_crystal_sword`、`ue_highland_claymore`，并加注释说明「`Supports()` 里每个条目都必须在此有图」。该改动待下次构建生效，见「遗留」。
- `Before/ue_highland_claymore.png`：原图备份，sha256 `322729C0D2433F27657DF3494ACE6062A0D7B90205F4D2B0CEC95A5AC0DFF25D`。

## 已执行（2026-09-23 23:08–23:09，UE 关闭后）

```
& Tools/UI/build_weapon_catalog_icons.ps1 -Definitions ue_highland_claymore,ue_frost_crystal_sword
```

两轮 commandlet 各自 `COMPLETE failures=0`、`Success - 0 error(s), 9 warning(s)`，日志 `SourceAssets/WeaponInventoryIcons20260913/export-ue_highland_claymore.log` 与 `export-ue_frost_crystal_sword.log`。

| 图标 | 结果 |
|---|---|
| `Icons/ue_highland_claymore.png` | 384×768，bbox 211×697，纵向 **90.8%**，中心 (0.497, 0.5)，sha256 `FF65A5771ED42267…` |
| `Icons/ue_frost_crystal_sword.png` | 384×768，bbox 139×697，纵向 **90.8%**，中心 (0.497, 0.5)，sha256 `AFFEBCB097F7F586…`（新建，此前无兜底图） |
| `Icons/ue_rune_sword.png` | 基准未动：384×768，bbox 229×697，纵向 90.8%，中心 (0.5, 0.5) |

三张同构：纵向填充与中心一致，横向差异是武器本体比例（阔剑 59.6% ＜ 高地 54.9% ＜ 细晶 36.2%）。画面为出厂装配正视图，高地带原生蓝色符文，寒晶带自带侵蚀的精神迸发纹样。

顺带效果：两轮日志都出现 `Missing cached shadermap for M_HighlandClaymoreSurface / M_FrostCrystalSword_SeamlessBronze in PCD3D_SM6 … compiling`，即这两件材质此前在 DDC 里没有 SM6 编辑器着色器映射 —— 正是运行时捕获连吃 `MaterialShader`／`RenderReadiness` defer 的直接原因，本次离线导出已把它们编进 DDC。

## 遗留

- `Icons/*.uasset` 仍是旧图（高地那份还是 1024² Blender 渲染）。全工程没有任何一处 `LoadObject` 引用它们，背包、工具提示、快捷栏、熔炼与强化面板一律 `ImportFileAsTexture2D` 读盘上的 PNG，所以不影响显示。**不要**为刷新它们去跑 `HighlandClaymoreMeshy20260922/Integration/import_icons.py`：它从 `Integration/Icons/` 取源，会把旧图倒灌回 uasset。要刷新就针对新 PNG 单独导入。
- 源码改动（commandlet 默认清单）本轮未编译：23:03 那轮构建的 obj 停在 22:29，DLL 在 23:07 重链但没有重编该 TU，改动留给下一次构建。定向重导不依赖它。
- `render_menu_icons.py` 仍负责改造件（配件）图标，那套 1024 方图、剑尖朝左是正确构图，不要改；只有 `slot=='inventory'` 那个任务被引擎通道取代。
- 未运行游戏、未截图、未做游戏内视觉验收。
