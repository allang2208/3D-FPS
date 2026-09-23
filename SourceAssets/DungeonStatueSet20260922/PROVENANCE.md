# 女神石像套件来源与许可

同一作者 **noe-3d.at**（<https://sketchfab.com/www.noe-3d.at>）
获取日期 **2026-09-22**，获取方式：Sketchfab Data API v3（用户提供的 API token），走系统代理 `127.0.0.1:7897` 下载。

## 逐件来源

| key | 作品 | 页面 | 许可 | 面数 |
| --- | --- | --- | --- | --- |
| venus | Venus | <https://sketchfab.com/3d-models/venus-47c7f4d3b6e640858e1d3afac28c1766> | **CC0 1.0**（公共领域，无需署名） | 597,703 |
| flora | Flora | <https://sketchfab.com/3d-models/flora-5cae3fbe60ba4a79b83ed12e0c26db44> | **CC BY 4.0**（需署名） | 502,658 |
| muse | Muse | <https://sketchfab.com/3d-models/muse-209c7842f0ab416cbdbd8a7484ab8930> | **CC BY 4.0**（需署名） | 477,835 |
| magnamater | Magna-Mater-Brunnen | <https://sketchfab.com/3d-models/magna-mater-brunnen-f6fa0a62a03149319e4fee21cb6dd5af> | **CC0 1.0**（公共领域，无需署名） | 604,948 |
| baroque | Barockstatue | <https://sketchfab.com/3d-models/barockstatue-ebc9a140626842fd8804b38c1dc8b8c9> | **CC BY 4.0**（需署名） | 373,544 |

CC BY 4.0：<https://creativecommons.org/licenses/by/4.0/> ｜ CC0 1.0：<https://creativecommons.org/publicdomain/zero/1.0/>

三件 CC BY 的署名文字（随项目对外分发时保留，另见 `FPSGAME/ThirdPartyNotices/STATUE_SET.md`）：

> "Flora" by noe-3d.at, licensed under CC BY 4.0.
> "Muse" by noe-3d.at, licensed under CC BY 4.0.
> "Barockstatue" by noe-3d.at, licensed under CC BY 4.0.
> Source: https://sketchfab.com/www.noe-3d.at

## 下载原件（本机保留，不入 Git；散列见 `Receipts/download.json`）

| key | source 包 | SHA-256 | glb 包 | SHA-256 |
| --- | --- | --- | --- | --- |
| venus | 213.1 MB | `316C5672…32BB` | 21.0 MB | `EAB738AD…D832` |
| flora | 205.0 MB | `97DC42DA…FCD5` | 17.7 MB | `E934FC0E…D901` |
| muse | 173.5 MB | `6F6DED31…45F2` | 17.2 MB | `E2DE4086…AA24` |
| magnamater | 140.8 MB | `9730CEBE…074B` | 20.0 MB | `B089AF92…D324` |
| baroque | 141.3 MB | `D6041540…9D33` | 12.7 MB | `59D0642B…C447` |

原包结构（5 件一致）：`source/<Name>_C/<Name>_C.obj` + `.mtl` + `<...>_u1_v1.png`（**8192 × 8192** 漫反射图集），外层另有一份 `textures/<同名>.png`。全部只有漫反射，没有法线／粗糙度／金属度贴图。导入用的是 source 包里的 8192² 原图，不是 glb 内嵌的压缩版本。

## 加工产物（本机）

| 文件 | 大小 | SHA-256 |
| --- | --- | --- |
| `Authored/SM_Statue_Venus.fbx` | 41.8 MB | `0C64B4D7…9DF8` |
| `Authored/SM_Statue_Flora.fbx` | 34.7 MB | `A7E59133…960E` |
| `Authored/SM_Statue_Muse.fbx` | 33.0 MB | `AFF1FD21…2641` |
| `Authored/SM_Statue_MagnaMater.fbx` | 40.7 MB | `A2F1029B…B027` |
| `Authored/SM_Statue_Baroque.fbx` | 25.9 MB | `0EDCCDB0…6A50` |
| `Textures/T_Statue_Venus_BaseColor.png` | 21.9 MB | `0D4F2796…A3DF` |
| `Textures/T_Statue_Flora_BaseColor.png` | 22.5 MB | `D7A05EEC…8F2E` |
| `Textures/T_Statue_Muse_BaseColor.png` | 20.6 MB | `884A845C…D413` |
| `Textures/T_Statue_Magnamater_BaseColor.png` | 14.6 MB | `B565F543…725E` |
| `Textures/T_Statue_Baroque_BaseColor.png` | 17.0 MB | `74DEC1A3…3D32` |
| `Authored/{venus,flora,muse,magnamater,baroque}_Editable.blend` | 33–48 MB | 见目录 |

## 修改说明（CC BY 要求记录改动）

对 5 件原作做了同样的加工，未改动比例与形状本身：

1. 立正并统一朝向：Muse 的源导出为 Y 轴向上，其余为 Z 轴向上；全部旋转到正立、正面朝 Blender −Y（UE 中 yaw 0 即朝 +X）；
2. 等比缩放到目标高度（立像 2.0 m、坐像 1.8 m），底面中心移到原点、底面 Z=0；
3. 漫反射图集由 8192² 降采样到 4096² 作为游戏贴图；
4. UE 内新建 `M_Statue_*` / `MI_Statue_*`（原 glTF 材质只有 baseColor），粗糙度、金属度、高光为项目设定值；关闭 Nanite；碰撞改用三角面。

网格拓扑、UV、法线与贴图内容未修改，未重新烘焙。
