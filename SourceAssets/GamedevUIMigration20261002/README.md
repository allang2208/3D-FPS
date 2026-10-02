# 原项目 gamedev UI／BGM 迁移

来源：`E:\无尽轮回\长期备份\2026-7-13-1\game-dev`（桌面 game-dev 快捷方式所指原项目）。仅记录为用户自有素材迁移，散列见 provenance.json。

## 迁移内容

| 源文件 | 原项目用途 | 本工程资产 | 接入 |
| --- | --- | --- | --- |
| `assets/sounds/ui/button_click.mp3` | audio-config `uiCues.buttonClick` 全局按钮点击确认音 | `/Game/Audio/GamedevUI20261002/S_Button_Click`（0.36s，48kHz PCM_16） | 抽屉页签（状态/装备与背包/弹药袋）、右侧栏目入口（ActivatePanelNavigation）、背包抽屉两个"整理"按钮；音量 1.0 |
| `assets/sounds/music/罗马庭院.wav` | audio-config `bgm.main`（main 场景＝主神空间） | `/Game/Audio/GodSpaceBGM20261002/S_RomanCourtyard`（77.96s，48kHz PCM_16，looping=true） | `AFPSGAMEPlayerController::BeginPlay` 在 Hub 地图（DayNight_Lighting）自动播放 2D 循环，音量 0.6＝原 music 声道；换图销毁自动停止 |

## 落盘状态

`import_audio.py` 经 UnrealEditor-Cmd `-run=pythonscript` 导入并保存，回执 `import-receipt.json`。换弹音（201→191/HK416 组）与本次迁移无关，见 FPSGAMECharacter.cpp 2026-10-02 注释。未试听验收。
