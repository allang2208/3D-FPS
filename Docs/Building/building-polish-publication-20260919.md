# 喷泉、凉亭穹顶与建筑面板发布整理

## 发布范围

- 蛋糕塔喷泉：V7单层溢流、V8自然水束与飞沫预算、V9湿石材／局部倒角／连续双层水声及用户要求的三倍音量；保留作者链和声音来源记录。
- 凉亭：用户采用的C4白色大理石穹顶、真实星座连线和顶饰，保留星图数据、BSD许可、当前作者数据、共用制作和C4接入入口。
- 建筑面板：目录归属、完整静态装配预览、冷钢主题与字体、完整居中等比图片、名称横排及滚动条占宽／网格重建换行修复。
- 本任务与并行文件共享位置时仅提交对应改动；门框尺寸、构件支撑／脱落、武器、天气等其他工作不随本次发布。

## 归档

已将未采用的A/B/初版C和被C4替代的C2/C3可编辑模型、导出、预览、记录及旧C3专用接入入口移入本机 `trash/building-polish-20260919`。每个文件移动前确认绝对路径在授权目录内，移动后读回SHA-256；原路径、归档位置、大小、散列和保留替代物见 [归档清单](../AssetArchives/building-polish-20260919.json)。trash不推送。

V7脚本、薄膜网格和飞沫基础资产仍被V8复用，V8噪声继续被V9引用；凉亭原主体 `SourceBackup/*_BeforeC2`、共用制作脚本、当前C4源及其许可数据继续保留。未仅凭旧版本号移动Content资产，UE历史资产的引用未做运行时盘点。

## 资源恢复与公开边界

- 喷泉需恢复本机 `Props/RomanFountain20260917` 的盆水／WaterFX、OverflowV7、OverflowV8、PolishV9及Audio，并保留原石材和Niagara基础依赖。V9音量写入资产制作器，两条SoundWave的volume均为3.0。
- 声音来自Nox_Sound的两条CC0作品，具体来源、HQ MP3版本、处理参数与源／成品散列在 `SourceAssets/RomanFountain20260917/AudioV9/sources-and-processing.json`。公开提交脚本与来源记录，网页快照、MP3、WAV和uasset留本机。
- 凉亭需恢复 `RomanColumn20260915` 正式整体／穹顶及石材、`RomanPavilionRoof20260919/WhiteCelestial` 的当前C4、原主体SourceBackup，及调色板中的47格高度。FBX、Blend、贴图、预览和uasset保留本机；d3-celestial数据与BSD许可一起发布。
- UI需恢复 `DA_VoxelBuildPalette`、工作台环境／预览材质，以及带原许可的Noto Sans SC与JetBrains Mono字体。代码发布不等于完整素材备份，仍遵守 [AssetSetup](../AssetSetup.md)。

## SKILL 与完成边界

建筑面板规则维护在 `ue5-ui-umg-slate/references/building-panel.md`；喷泉水流／音频与穹顶制作分别进入 `ue5-pcg-building/references/fountain-water-audio.md`、`pavilion-roof-decoration.md`，个人技能与工程对应章节同步，保留无关条款。

历史必要构建：本次布局修复已在 `build-20260919-213304.log` 完成28项Editor构建动作并返回Succeeded。此次发布整理只执行用户授权的归档散列、提交内容、许可、敏感信息和Git推送检查；未重新运行游戏、渲染、试听或性能测试。用户已认可喷泉与C4外观；最终面板布局的实机显示仍由用户测试。
