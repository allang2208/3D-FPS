# 云层、雷电与柔和火光发布整理

本轮整理范围是夜间青铜火把/枪口光斑、暴雨云层、闪电和延迟雷声。按 `WORKFLOW.md` 第 8 节在 `D:/FPS3D/FPSGAME` 精确提交，目标为 `https://github.com/allang2208/3D-FPS.git` 的 `main`。并行的 ASH12、枪匠、角色等修改不随本轮发布。

## 当前结果

- 火把使用有限半径柔光与较低火焰发光；枪口缩短闪光、压低镜内叠加并保护瞄准中心。详见 [火光调整](../Lighting/fire-lighting-soft-20260919.md)。
- 项目云材质接入引擎工作实例的四张纹理，保留非零消光、积云层次和连续风动。详见 [纹理绑定修复](cloud-visibility-fix-20260919.md)。
- 天空/云按昼夜调节闪电亮度；保持时间最终为 0.5 秒，另有 0.05 秒起亮和 1.5 秒恢复。三段雷声已制作派生资产，剪除弱前奏并限制峰值，闪电后随机延迟 2–5 秒播放，期间平滑压低雨声。详见 [声画修正](lightning-audibility-fix-20260919.md)。
- 用户在声画修正后反馈“成功了”；随后提出 0.5 秒调整。该小调整 Live Coding 返回成功并更新当前编辑器类默认值，未启动额外测试。基础 DLL、后续重启及打包覆盖以常规构建为准。本次发布整理不新增游戏测试或性能结论。

## 废案归档

新增归档 `trash/weather-lighting-20260919/`：12 个被替代备份/已结束的临时制作工程目录，共 32 个文件。连同之前归档的三个诊断云材质，共 35 项列入 [归档散列清单](../AssetArchives/weather-lighting-20260919.json)。所有移动前限定源/目标在本工程内，拒绝目录联接，移动后读取 SHA-256 对照。

历史文档中的 `Saved/.../Before*` 与临时 `CloudAssetAuthor` 路径由此清单映射至 trash。`Saved/LightningDiagnosis20260919/Before` 是声画对照基线，并非被替代资产备份，仍保留；Probe、云材质对照截图、作者结果、制作脚本和源音频也保留。`repair_layered_cloud_density.py` 与 `repair_layered_cloud_textures.py` 仍被正式重建脚本调用，不属于废案。

## 完整资源恢复

公开仓库发布源码、作者脚本、说明和来源/散列元数据；运行 uasset/umap、引擎/Fab 素材、WAV 和 trash 保留本机。源码发布不等于完整游戏资产备份。

恢复本机合法内容时保留：

- `Content/Weather/Materials/M_FPSLayeredClouds`、`MI_FPSLayeredClouds`、`MPC_FPS_Weather`，丘陵 `MI_HillsClouds` 与 `M_HillsDayNightSky`，`Content/Weather/NaturalV2` 天空适配材质及 `DA_WeatherPresentation` 引用。
- 引擎 `/Engine/EngineSky/VolumetricClouds/` 的布局、剖面、遮罩和体积噪声纹理。新云是基于项目/引擎图的调整，不能将 Fab 页面评估描述为导入替换已经完成。
- `Content/Weather/Audio/S_Thunder_I/II/III` 和原 `Content/Thunder_Sounds` 授权素材。派生 WAV 与散列来源在本机 `SourceAssets/Weather/Thunder`，公开仅保留 `provenance.json`。若需要重建，先从原三个无风雨背景 SoundWave 导出 `thunder-source-0/1/2.wav`，交 `prepare_thunder_audio.py --source <导出目录>` 制作，再运行 UE 内 `import_thunder_audio.py`。
- `Content/Props/RomanColumn20260915/NS_TorchFlame`、`MI_TorchSoft_Flame01/02` 与原 Vefects 火焰依赖；`Content/Weapons/GunplayFX/NS_FPS_MuzzleFlashV10`。原素材制作之后运行 `Tools/AssetPipeline/soften_fire_lighting_20260919.py` 恢复柔光配置。

云的完整制作入口 `Tools/Weather/build_layered_cloud_material.py` 会调用纹理、密度、运动和闪电接入函数；已有天空资产补接闪电使用 `build_storm_lightning_materials.py`。这些依赖均使用同一项目路径，作者执行与游戏验收分别记录。

## 技能沉淀

天气技能新增云纹理、闪电与音频输出参考；更新火把现行柔光档位和直接在 D 盘精确发布的规则。调试技能增加对应入口，武器技能记录相机/粒子/点光/镜内叠加的区分与中心面片保护。仅同步本次增量至个人技能目录和工程镜像，保留其他会话的技能修改。
