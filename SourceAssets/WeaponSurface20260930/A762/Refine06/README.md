# A762 Refine06 — 表面精修

本轮面向 Meshy 枪械与 AKM／HK416／M4 精修成品之间的表面质感差距。沿用 A762 已有 V5 局部去噪、真实倒角和弹匣曲面，不重复进行整枪平滑。制作记录见 `Docs/Weapons/a762-finish-refine06-20261001.md`。

## 制作链

1. `capture_inputs.py` 通过现有 UE 批次入口读取实际绑定的 28 个网格和 90 个 WS1 实例，保留生产输入。它不修改 UE 资产。
2. `produce.py` 在 CPython 3.11 下生成四张数学构造的周期 PBR 数据纹理和 `recipe.json`；不生成验收图。
3. `apply_finish.py` 使用当前材质路径，仅覆盖配方中的参数并导入新纹理，逐个保存生产回执。保留原父实例、结构法线、UV 遮罩、两面属性、机械骨骼和湿润参数。83 个表面实例纳入精修，7 个内腔实例保留。

从项目根目录执行生产保存：

```powershell
& .\SourceAssets\WeaponSurface20260930\run_ue.ps1 -Script 'A762\Refine06\apply_finish.py'
```

默认通过无界面 commandlet 执行；若该工程已有编辑器，则使用原桥的互斥入口，不另开编辑器。脚本发现未保存或已被其它工作修改的目标时保留现场。

## 纹理与回退

- `T_A762_R06_Grain`：1024² RGBA 线性数据；4 cm 三平面周期，R 为约 0.17–0.5 mm 的细颗粒粗糙度，G 为更小尺度的涂层变化，B 为零划痕，A 为浅聚合物颗粒。
- 三张 `*_N`：512²、DirectX 切线法线、导入不翻转绿色通道；只替换指定重建槽原来的 DefaultNormal。金属／聚合物／橡胶 RMS 坡度分别 .012／.040／.028，不参与轮廓和倒角制造。
- 原厂与加长弹匣保留金属身份、相同配方；原曲面面板的程序亮边和磨损仍关闭。
- `Input/current.json` 保留制作前有效参数；`Before/` 保存本轮实际修改的原 uasset；`apply_receipt.json` 记录每项保存结果和散列。
- 本轮保持原实例路径，因此无需替换网格引用、更新天气表或编译 C++。雨天仍由现有 `M_WeaponSurface` 和 `WeaponWetness` 接入，未进行雨天运行测试。

后续制作以本轮入口为准。历史 `../install_a762.py` 和 `../install_accessories.py` 会清空实例覆盖，不能用它们代替本轮重放入口。若需要重新改动旧几何／绑定制作链，先保留并合并本轮配方。

`apply_receipt.json` 的 `complete=true` 仅表示生产保存完成。未自动打开 UE、运行游戏、截图、渲染或测试；视觉效果由用户测试。
