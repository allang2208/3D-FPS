# 工作台材质绑定

用于 FPSGAME 木工、制药、枪械及普通工作台的同系列材质统一。2026-11-08 的结果是可复用流程，不要求其他家具强套同一色调。

- 先核对当前 Palette 实际选用网格、各槽材质／父材质、纹理引用及运行时 Surface 覆盖；仅检查静态网格槽可能漏掉运行时槽 0 被旧 Palette 覆盖。
- 复用现有合适贴图时，修正木材颜色、粗糙度、法线强度和介电反射参数，保持 UV、金属分区和表面身份。独立新材质，不随意改共享母材质。
- 区分木面、端纹、漆面、机加工钢、橡胶与图集；保留玻璃、液体、标签、功能发光和锯刃引导。不同桌面的坐标积尘／磨损遮罩不能无条件套用。
- `material_mapping.json` 维护允许网格、原到新材质映射及 Palette ID。重导入后运行正式批次 `run.ps1 -Stage Reapply` 恢复绑定，而非重放旧一次性导入脚本覆盖当前母版；Author、Reapply、Readback 各自作用不同。
- `Before/` 与散列清单是仍有效的回滚输入，不因名字叫备份就归入废案。回退先检查编辑器占用及后续修改，不覆盖别人新版包。
- 资产读回核对网格材质绑定、LOD 三角数、依赖纹理和 Palette；成功保存／读回不代表最终视觉、游戏或性能验收。默认不因此自动启动测试。

当前制作源：`SourceAssets/WorkbenchMaterialUnification20261108/README.md`、`Scripts/author_and_apply.py`、`Scripts/reapply_after_import.py`、`material_mapping.json`；生产资产 `/Game/Building/WorkbenchSurfaces20261108`。

历史范围：6 类工作台、38 网格、112 材质／父材质检查；11 新材质、24 网格 51 槽与 2 个 Palette 覆盖，磁盘读回无缺失纹理。铸造专用材质及强化 V6 保留。已有素材足够，未下载或购买 Fab／Quixel；缺少时先向用户报告并优先筛选免费 Quixel／Fab，不把免费可用误当再分发许可。第三方纹理与模型不随源码公开。
