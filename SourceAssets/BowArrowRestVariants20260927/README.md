# 箭台改造 — 2026-09-27

- 开口速搭箭台：搭箭耗时 −80%、拉满耗时 −10%、子弹速度 +5%、腰射扩散 +10%。
- 双叉导向箭台：腰射扩散 −25%、子弹速度 −5%。

作者参数以 `series.json` 为准。独立搭箭使用 nock_mult，快速入弓/连续入弓继续沿用现有单独时钟；不把搭箭倍率解释为整轮连射间隔。

制作链：`author_assets.py` → `run_import.ps1` → `install_config.py`。Blender 5.1 后台制作；编辑器运行时通过现有 MCP 桥批次互斥导入，未运行时使用后台 commandlet。不启动游戏或验收。

`Bow_ArrowRestVariants.blend` 保留厘米制安装坐标、当前贴合底座、原木材 UV、两款接触结构和材料。FBX 导出位于 `Export/`；`Textures/` 保存本轮制作的角片和皮衬各三张 512 纹理。法线按 OpenGL 生成、UE 导入翻绿一次；ORM 的 AO 为中性白，Metallic 为零。

木制底座来自本工程当前箭台 `SourceAssets/BowModular20260926/Bow_ModularParts.blend`，运行时继续使用当前绑定的 `M_Bow_CarvedWood`。新增托架几何和角片／皮衬纹理由本地程序化制作；未下载、上传或公开分发素材。

`Bow_ArrowRestIcons.blend` 是独立灰阶图标场景；真实部件 1024 RGBA，枪械前向沿当前安装轴保持朝画面左侧、相机保持水平，不改变运行材质配色。`render-receipt.json` 记录产物。

`import-receipt.json` 记录实际成功保存的 UE 资产；`install-receipt.json` 记录正式目录接入。脚本仅保存本批目标包，数据修改前副本位于 `Saved/BowArrowRestVariants20260927/Before/`。现有原装/皮垫箭台和其他改造槽保留，玩家当前选择与存档不直接改写。

未进行游戏测试、视觉验收或额外静态检查，由用户测试。制作渲染只用于交付图标。
