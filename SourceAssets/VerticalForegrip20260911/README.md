# 当前状态

已完成精修、M4 材质统一、专用抓握/换弹和游戏接入。最终交付见 [Integration/README.md](Integration/README.md)。以下保留最初 5080 生成阶段记录。

# 垂直握把：5080 首版候选

## 本次范围
按改造配件标准搜索参考，使用真实 RTX 5080 / TRELLIS.2 生成初版模型。候选独立保存，尚未接入 UE、统一 M4 材质或制作抓握动画。

## 参考与生成
- 参考页面：https://charliescustomclones.com/m4a1-vertical-grip-mil-spec-vfg/
- `reference.jpg`：已查看的黑色直筒式握把产品图；顶部连接座、窄腰直筒和底部环形凹槽是本轮轮廓依据。
- 参考仅用于本机制作；未确认图片再分发许可。候选不可直接作为授权原厂精确复刻发布。
- 单张照片输入，背面与遮挡结构为模型推断；未宣称三视图重建。
- 设备与服务实查见 `system_stats.json`：NVIDIA GeForce RTX 5080，16GB 级显存。
- `workflow.json` / `request.json` / `receipt.json`：完整生成参数与回执。512 首版档，结构12步、形状16步、纹理12步、seed 91143，另输出2K贴图、10万面目标候选。目标面数不是实际面数。
- 背景阈值沿用已成功的前握把管线；不下载额外抠图模型。单张干净背景参考已人工检查。

## 文件与复现
- `status_download.py`：只查询本任务，成功后下载独立输出目录中的生成 GLB。
- `render_candidate.py`：Blender 导入实际生成的带贴图 GLB，报告实测网格统计并渲染多角度图、保存可编辑文件。
- 原始高模与带贴图候选分别保存；未做手工替换网格。生成颜色和表面信息不能视为完成当前 M4 材质统一。
- 生成归一化尺寸不作为游戏装配尺寸。下一阶段应核对现有 M4 挂点及手模，在明确尺寸后处理拓扑、轮廓、UV和手臂接触。

## 首版结果（已实际检查）

5080 任务成功，计算 61.036 秒（不含排队）。带贴图候选 95,198 三角面，可编辑文件为 `VerticalForegrip_5080_Editable.blend`。已检查 beauty/back/side 实际 Blender 渲染：直筒轮廓与底部环槽得到保留；顶部有破碎状瑕疵，背面存在明显接缝，仍需精修。未接入游戏。原始网格统计与散列见 `acceptance.json`。

## 后续精修和当前接入

模型精修、M4 材质统一及配件接入见 `Integration/README.md`。用户随后指出未抓紧，当前九条运行时动画已由 `TightGrip/README.md` 的紧握修订替换；实机标签 `vertical-tight-v1`，340 项通过，446 个几何采样无手套/握把相交。上文“未接入游戏”仅描述 5080 首版生成阶段。

最新修订见 `Compact75/README.md`：三轴缩小 25%、安装槽底贴合下导轨，并重新匹配抓握与九条动作；当前运行目录为 `/Game/Weapons/M4VerticalGripCompact75`，实机标签 vertical-compact75-v1。

腕肘最新修订见 `WristNatural/README.md`：复用 Compact75 模型与抓握，按共振握把方法重新求解肩肘支撑。运行动画目录 `/Game/Weapons/M4VerticalWristNatural`；实机标签 vertical-wrist-natural-v1。
