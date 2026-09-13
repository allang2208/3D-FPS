# 技能与顶部 HUD 源码发布（2026-09-13）

本批发布技能页、步枪精通配置与存档成长、升级提示和音效播放入口、事件进度栏折叠、顶部生命／法力显示及世界时钟；包含它们使用的共享冷钢字体、主题与抽屉布局。时钟修正自绘填色，增加昼夜颜色与指针轮廓对比。

## 发布范围

共享文件按功能拆分暂存，保留并行枪械、建造、强化附魔、仓库空间网格与拖放修改。发射和命中代码只发布技能快照及经验入口。`Docs/AssetSetup.md` 的原有暂存内容属于其他工作，保留原状。

完整本机宿主包含更多尚未提交的工作。本批 Git 源码不代表全部本机改动已经公开发布；历史各面板文档仍只描述其对应版本。

## 资源恢复

- 技能配置随源码发布：`Content/ColdSteelData/skills.json`。
- 当前实际使用原 game-dev 图标与升级音，来源、SHA-256 和目标路径见 `SourceAssets/Skills20260913/provenance.json`。原始二进制留在本机，未声称取得公开再分发许可。
- 在拥有原资源的机器执行 `py -3.11 Tools/UI/prepare_skill_assets.py`，需要脚本指定的 game-dev 路径及 `imageio_ffmpeg`。恢复 `Content/ColdSteelData/Skills/rifle_mastery.png` 和 44.1 kHz 双声道 16 位 PCM 的 `player_upgrade.wav`。
- 字体位于 `Content/UI/GunsmithWorkbench/Fonts/`：Noto Sans SC Regular／Medium、JetBrains Mono Regular／Medium，按 `Docs/AssetSetup.md` 恢复字体和随附许可；本批增加字体运行时打包入口，不上传字体二进制。
- 选中的第二款去准心 M4 图标仍为候选，尚未替换运行时原图。发布 `SourceAssets/Skills20260913/Candidates/rifle_mastery_B_M4_v2.json` 制作记录；候选 PNG 保留本机。

## 废案处理

本批没有确认退役的独立文件，移动清单为空。技能图标／音效原件、选中候选和修改前备份仍承担恢复、制作或历史记录用途，予以保留。Codex 生成目录中的历史候选不属于工程废案目录，不移动。后续明确退役项遵循 `WORKFLOW.md` 的 `trash/<task>/` 散列归档规则。

## SKILL 与交付边界

更新 `ue5-ui-umg-slate/references/fpsgame-panels.md` 及个人技能镜像：顶部布局统一计算、时间零点换算、Slate 显式填色、折叠装饰层同步隐藏、技能属性派生、发射快照与提交后升级通知。

本轮只执行用户要求的仓库整理和发布检查，不启动 UE，不新增游戏测试、截图或视觉验收。此前本机宿主必要构建记录留在 `Saved/`；它们不是本次拆分提交的独立构建结果。界面、成长、音效和时钟效果由用户测试。
