# M4 左斜握把

以持枪者从枪托朝枪口观察为准，向左下方侧倾 45°。该 M4 作者安装坐标的 +Y 是左手侧，不能直接套用一般坐标约定。模型与手腕目标用旋转构建；骨架、蒙皮、骨长、手指局部位移及缩放保持。

## 来源与制作

原始 5080 输出保存在上级目录，成功任务 `7d0144f9-654b-47fe-8277-6c4e27b08a94`。三视图由 Blender 原生模型渲染；5080 使用单张主视角，不是三视图融合。最初多反转一次 alpha 导致方块，该结果作失败记录保留。正确原始输入另存为 `5080_input_original.png`。

生成结果保留宽轮廓参考，使用干净拓扑修整毛刺、防滑环及安装座，约 2.63 万三角面；最终材质复用当前 M4。方向经用户指出后纠正，原始生成文件不覆盖。详见上级 `provenance.json`、`direction_correction.md`。

## 复现入口

`prepare_canted.py` 从当前紧凑垂直握把源与新生成径向轮廓构建候选。`apply_clearance.py` 只在刚准备的参数上运行一次，将整手沿握把下移以避开安装座；不改手指关节平移。`build_animation.py` 使用冻结的 `ReferenceWorkflow`，当前肩带参数为原 M4 源空间的 `(0.06,0.12,0)` 米。松手早段侧移稍慢，并在第 4 帧恢复完整侧移曲线。随后运行 `validate_source.py`、`check_geometry.py -- --full`、`import_assets.py`、`run_validation.ps1`、`run_ui.ps1`、`assemble_editable.py` 和 `make_delivery.py <run>`。

`measure_grasp.py`、`fit_clearance.py`、`fit_release_clearance.py` 是诊断记录，不能再次当作最终参数入口。`refine_grasp.py` 属于纠正左右方向前的候选，最终不使用。完整状态以 `acceptance.json` 及运行日志为准，未生成验收文件前不是交付完成。

## 游戏接入

配件 ID `canted_foregrip`，M4 枪匠下挂分类中的“45°侧倾握把”。独立目录 `/Game/Weapons/M4CantedForegrip` 包含静态模型和九条专用动画；共振握把、垂直握把、棱镜阻手器保留。换弹机械轨道、右手、弹药时钟和中段取弹插入接触沿用原动作。

测试使用隔离存档，不更改用户存档。尚未进行打包运行验收；静音视频只证明画面，不代表音效验证。

## 本次验收

运行标签 `canted-left45-v1`：342 项运行检查、24 项枪匠事务检查通过；九条动画源合同及 UE 压缩读回通过；446 个手指/配件采样无相交。实机已查看掌侧、正面、腕肘、第一人称和退握/回握关键帧。静态拓扑无开放边、非流形边和零面积面。腕轴折角约 8.49°，这是本 rig 的比较指标。

导入 commandlet 退出码为 1，日志为既有 GameFeatureData 资产管理器配置错误；九条资源的导入/读回标记通过，新游戏进程亦通过。未验证完整打包，未修改声音。

可编辑汇总：`M4_CantedForegrip_Integrated_Editable.blend`；实机静音视频：`M4_CantedForegrip_Gameplay.mp4`；所有九条 FBX 与逐条 Blend 保留。
