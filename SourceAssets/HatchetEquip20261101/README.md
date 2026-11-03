# 碳钢战斧拔斧（2026-11-01 / 11-02）

单持战斧的装备动画 `HatchetEquip`。当前是 V2：按 BV1pqkyYyEDY “切刀动作 #2 抛”还原翻斧、抛起、侧手接柄、前送翻面，最后收进与弯刀共用的持斧架势。设计、与参考的差别和交付状态见 [Docs/Weapons/tactical-hatchet-20261101.md](../../Docs/Weapons/tactical-hatchet-20261101.md) 的“装备动画 V2”一节。V1（竖直抛接）的源文件和预览在 `Work/v1/`。

| 文件 | 作用 |
| --- | --- |
| `author_hatchet_equip.py` | V2 作者源：参考读数表 `REF`、关键姿势求解、样条组装。生成 `Clips/HatchetEquip.json` 和 `clips.json`。`--header` 重写 `Source/FPSGAME/Weapons/Kukri/HatchetDrawRhythm.h`；`--preview` 渲染视频和参考对比图；`--refit` 重新求解关键姿势（缓存 `Work/v2_keys.json`）；`--poses` 只写 `Work/previews.json`。 |
| `hatchet_pose.py` | 由屏幕读数构造斧子姿势（头部点 NDC、深度、倾角、沿视线倾斜、绕柄朝向），以及手臂读数。 |
| `Reference/` | 下载参考、抽帧（`extract_ref.py`）；读数网格和拼图（`grid_ref.py`、`sheet_ref.py`）；镜头配准（`camera_ref.py`）。参考视频和帧保存在 `Saved/Reference/HatchetBV1pqkyYyEDY20261102/`，不进 Git。 |
| `render_hatchet_preview.py` | Blender 预览渲染：游戏镜头，V7 可编辑手模，真实斧模，可叠加作者镜头曲线。 |
| `check_contact.py` | Blender 接触读数：手部皮肤压入斧子真实网格的深度。 |
| `import_hatchet_equip.py` | UE 后台 commandlet 导入 `/Game/Weapons/TacticalHatchet20261101/Animations/A_TacticalHatchet_Equip`，回执写到 `import_receipt.json`。 |
| `Previews/` | 原速和 4 倍慢放 MP4；`compare_*.jpg`（上排参考、下排本作，每 1/30 s 一格）。 |

依赖 `../Kukri20261020` 的绑定解算（`kukri_rig.py`、`kmath.py`、`fit_reference.py`、`attack_keys.json`）。

重建顺序：

```
python author_hatchet_equip.py --header --preview
UnrealEditor-Cmd.exe D:/FPS3D/FPSGAME/FPSGAME.uproject -run=pythonscript -script=D:/FPS3D/FPSGAME/SourceAssets/HatchetEquip20261101/import_hatchet_equip.py -unattended -nosplash
```

改了 `HatchetDrawRhythm.h` 需要重新构建 C++；只重导 clip 不需要构建。
