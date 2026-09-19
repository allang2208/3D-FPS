# 手脑：原脸张口重做版

本版本从 `../../hunyuan_v01/delivery/HandBrain_Animated.blend` 重建。没有导入 `howl_v01` 的嚎叫人脸，也没有旧脸缩进、新脸展开的替换机制；没有新增云端生成调用。

原主体嘴部局部重新拓扑，八圈嘴周网格连接八圈口腔内壁。嘴唇、下巴、脸侧手臂受同一套骨架驱动；牙齿为本地制作的独立口腔零件。主体不是第二个头的蒙版或叠层。旧版拍击用的攻击臂和顶部手簇仍保留，所以文件并非只有一个网格对象。

## 文件

- `HandBrain_SingleFace.blend`：可编辑源文件，纹理已打包。
- `SK_HandBrain_SingleFace.fbx`：UE 用骨骼和四个动作。
- `HandBrain_SingleFace.glb`：便携预览导出。
- `Attack_Howl.mp4`：3 秒实模动画，使用原 howling.mp3 音频。
- `Attack_Howl.gif`：循环播放仅方便观察；游戏嚎叫动作本身不循环。
- `Face_*.png`：嘴部近景；`FBX_*.png`：重新导入 FBX 的渲染。
- `textures/`、`ue_materials.json`：各材质槽贴图及常量；独立法线贴图已转换 DirectX。FBX 内嵌法线采用 Blender/OpenGL 约定，UE 请使用提供的 DirectX 贴图。

## 动作及范围

保留 Idle（2 秒）、Move（1 秒）、Attack_Slam（2 秒，1 秒接触）；重做 Attack_Howl（3 秒，约 0.82–1.8 秒完全张口，2.62 秒闭合）。保留原来的骨骼动画曲线，新口部骨骼在旧动作中为中性状态。嘴部网格和贴图已经修改，因此不称整张脸的旧画面逐像素不变。

参考原 attacking-2.png 的 28 帧及大张口关键图。头顶原有手簇仅有限展开；这一版尚未逐根拆出参考图里所有竖起的手掌，不能称完整逐帧还原。

`validation.json` 记录旧动作骨骼矩阵、未修改区域蒙皮、权重、有限值和闭合检查；`fbx_validation.json` 记录四个动作的导出时长及回读结果。最多 8 个蒙皮影响，37 根骨骼。没有完成 UE 导入或实际战斗接入，不以 Blender/FBX 检查替代引擎验收。

本地重建运行上级 `rebuild_local.ps1`，只复用原闭口资产，不调用混元 API。上一版 howl_v01 为用户否决的换脸方案，不作为本版本依赖。
