# 尼泊尔弯刀（Kukri）作者源 · 2026-10-20

单手近战武器 `ue_kukri` 的模型处理、第一人称动作作者源与后台导入脚本。说明与运行时接入见
[Docs/Weapons/kukri-20261020.md](../../Docs/Weapons/kukri-20261020.md)。**未做实机测试。**

## 来源与许可

| 项 | 值 |
| --- | --- |
| 原始资产 | Fab「Kukri」，作者 powers28，listing uid `0a08e297-e2d0-472b-b572-53077a548196`（发布 2026-07-07，标签 Machete/Weapon/Melee/Knife） |
| 本机原件 | `D:\FPS3D\VaultCache\FabLibrary\Kukri-0a08e297\fbx\kukri_extracted\`（`Model/kukri.fbx`，`Textures/Unreal/*` 2048 ORM 套，`Textures/PBR/*`） |
| 许可 | 以 Fab 购买条款为准；再分发许可未审核——原始 FBX/贴图与派生 `Content/Weapons/Kukri20261020` 二进制不公开提交 |
| 动作参考 | Bilibili [BV1CeYUeSE7b](https://www.bilibili.com/video/BV1CeYUeSE7b/)（Apex 班加罗尔传家宝全动作展示）；只取节奏、方向与构图，帧图在 `Saved/Reference/KukriBV1CeYUeSE7b20261020/`，不入库 |

## 文件

| 文件 | 作用 |
| --- | --- |
| `author_kukri_model.py` | Blender：导入 FBX，×1.65 放大（无挂绳 38.6 cm），拟合握柄中线，变换到握点坐标（原点=右拳握心，+Z 刀身，+X 刃口），导出 `Export/SM_Kukri.fbx`、`Kukri_Editable.blend`、`Icons/ue_kukri.png`（256×768，1×3 格）、`model.json` |
| `kmath.py` / `kukri_rig.py` | 纯 Python 变换与解算：共享剑臂骨架、右拳—刀柄锁定、伸手圆上选肘、前臂扭转按 V9 约定分给 twist_01 100% / twist_02 50%、左臂下垂出画；解剖诊断（ρ 旋前/旋后、背伸/掌屈、尺偏/桡偏） |
| `author_kukri_clips.py` | 七条 120 fps 作者动作：Idle 3.0 / Walk 0.9 / Run 0.667 / Equip 0.70 / Attack 1.267 / Attack2 1.0 / Attack3 1.1 s（长度均落在 30 fps 重采样网格），输出 `Clips/*.json` 与 `clips.json` 诊断摘要；V1 的 Slash1/Slash2/Pommel 已退役到 trash |
| `render_preview.py` / `preview_tools.py` | 作者期构图预览：用 V7 FrostArms 可编辑骨架在游戏机位（垂直 FOV 75、16:9）渲染关键帧，非实机验收 |
| `fit_reference.py` → `attack_keys.json` | **V2 单段横挥**：按参考 1:27.00-1:28.27 每帧屏幕目标（拳心/刀尖/刀把/前臂）在解剖参数上逐帧拟合（连续性、扭转走廊、腕限位、肘不挡视线、刀不贴/穿镜头），`--accept` 写出关键参数；`author_kukri_clips.py Attack` 读取并烘成 `Clips/Attack.json` |
| `Reference/` | 参考帧抽取、网格读数图、背景配准测镜头运动（`camera_atk2.py` → `atk2_camera.json`，换算后写入 `KukriRhythm.h` 镜头曲线）的脚本；视频与帧图本身留在 `Saved/Reference/`，不入库 |
| `make_kukri_textures.py` → `Textures/T_Kukri_*.png` | 刀面钢材重做（Fab 刀面原为非金属中灰 + 强锤纹，游戏里呈白色颗粒）；保留 UV 与锤纹，刀身岛改为金属钢，法线减弱；导入脚本按纹理修订号就地重导 |
| `import_kukri.py` | UE commandlet：贴图（BaseColor sRGB / Normal / ORM masks）、Substrate 材质 `M_Kukri`、`SM_Kukri`（自动简单碰撞）、七条 `A_Kukri_*`（AnimDataController 直写骨骼轨，骨架 `SK_AzureRunesword_Manny_Skeleton`，预览网格 `SK_FrostSword_Arms`），写 `import_receipt.json` |
| `dump_sword_rig.py` | UE 端骨架/剑动作数据导出 → `Work/ue_sword_dump.json`（86 MB 中间件，`kmath.load_dump`/`render_preview` 的输入，不入库，可由本脚本重生成） |
| `Work/` | 仅 `ue_sword_dump.json` 常驻；fit/预览等其余输出按需生成、不入库。旧搜索脚本、日志、对比图与各版 key 备份见 `trash/kukri-20261020-closeout/` |
| `Previews/` | 终审关键帧拼图（本地文件，不入库）：`cmp_v6_strike`、`sheet_Attack`、`sheet_attack2_v7`、`sheet_Attack3`、`sheet_attack3_v10` |

## 重建

```powershell
$blender='E:\Program Files\Blender Foundation\Blender 5.1\blender.exe'
& $blender -b --factory-startup --python author_kukri_model.py
python make_kukri_textures.py                                             # 刀面钢材贴图
$env:PYTHONPATH=(Get-Location).Path; python fit_reference.py --accept     # 第一段水平横劈逐帧拟合（VARIANT=chop，约 3 分钟）
python fit_reference.py --attack2 --accept                                # 第二段左上→右下斜劈（从第一段 17/30 s 接段姿态起）
python fit_reference.py --attack3 --accept                                # 第三段双手前刺（从第二段 0.40 s 接段姿态起；左手按压在 clip 里键控）
python author_kukri_clips.py Idle Walk Run Equip Attack Attack2 Attack3  # 加 --preview 出关键帧图
& 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' D:\FPS3D\FPSGAME\FPSGAME.uproject `
  -run=pythonscript -script=D:\FPS3D\FPSGAME\SourceAssets\Kukri20261020\import_kukri.py -unattended -nosplash -nop4
```

坑：

- 前臂扭转必须相对**绑定姿态**计算（`kukri_rig.solve_arm`），并逐帧展开；V1 相对剑锚点叠加，导致 twist_02 比例错误、前臂扭到 +120° 和收势翻腕（用户反馈“手部错误反转和扭曲”）。

- `-DisablePlugins=AutoFootstep` 已不能用于本工程 commandlet——`UnrealEditor-FPSGAME.dll` 现直接导入 AutoFootstep，禁用后模块加载失败（GetLastError=126）。
- 动画长度不在 30 fps 网格上（如 0.64 s、0.72 s）会触发 `Incompatible resampling frame rate` ensure，并在压缩线程崩溃；改长度后要先删掉旧包再导入。
- 用 PowerShell `Get-Content`/`Set-Content` 改含中文的 UTF-8 源文件会按 GBK 误读成乱码；源文件只用编辑工具改。
- 角色 `ExitSprintForWeapon` 等是私有接口，弯刀组件不直接调用；冲刺退出由 `FirePressed` 负责。
