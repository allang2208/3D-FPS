# 货运区（车站）搬运工 M-01、技术员 M-01

按用户 2026-10-14 要求，从当前安保员派生两个人形怪物，只更换衣物和职业外观，复用现有身体、骨架、动画与战斗行为。搜索物品和货运区自动刷怪编排不在本次制作范围内。2026-10-16 编号规则改为**人形 NPC 统一 M-01**，以名字区分个体。

| 怪物 | 编号 | 职业外观 | 蓝图 / F6 稳定 ID |
| --- | --- | --- | --- |
| 搬运工 | M-01 | 炭灰长袖、橙色反光背心、反光横带与肩带、工装口袋、黄色安全帽 | `CargoPorter` |
| 技术员 | M-01 | 蓝灰维修工装、深色肩部与护膝、胸袋、工具收纳袋、白色安全帽 | `CargoTechnician` |
| 沉匣 | M-33 | 外观和行为保持原样，仅更改对外编号 | 原 `M10Mawcrawler` 保留 |

沉匣旧内部 ID、类名、导航名称、资源目录不改名，已有引用继续有效。当前对外编号以本文和 F6 / 战斗名称为准；旧制作记录中的 M-10、M-11、M-12、M-20 属于历史编号。

## 制作与复用

- 母版：`SourceAssets/FacelessSecurity20261008/V13/Authoring/FacelessSecurity_V13.blend`。保留完整身体、显示身体、骨架、皮肤材质、衣袖与手腕覆盖以及原靴内处理。
- 删除安保领带、警用肩章、纽扣、身份牌、字样和原胸袋；从现有衣身表面制作新工装裁片，沿用该位置的蒙皮、UV 和实体厚度。新增裁片合并到各角色运行骨骼网格，不新增逐帧衣物组件或模拟。
- 新增 8 个 PBR 材质家族、24 张 1024 贴图；颜色、法线、ORM 同源程序化制作。皮肤、鞋靴、皮带与小五金复用已有材质，保留纹理流送。
- 搬运工穿衣模型 248,891 三角面，技术员 224,187 三角面。安全帽各 4,064 三角面，带独立凸碰撞，复用安保帽头部命中掉落及回收组件。
- 两个蓝图独立复制当前 `BP_FacelessSecurity`；共享 `SKEL_FacelessSecurity` 和现有物理资产，直接保留 V06 待机/移动、V10 攻击、V12 受击/眩晕/倒地/两种起身，共八段动画。
- 胶囊、NavAgent、AI、移速、攻击时序、伤害、奖励、死亡布娃娃与复制沿用安保默认值。新身份标签接入安保同类的动作过渡与双足接地；F6 占地半径沿用 44 cm。

## 文件与重建

- 作者源、独立衣物与穿衣 FBX、安全帽、贴图：`SourceAssets/CargoStationStaff20261014/V01/`。
- 制作：`Tools/CargoStationStaff/author_variants.py`，Blender 5.1 后台执行。
- 导入/保存：`Tools/CargoStationStaff/import_assets.py`。已有编辑器时使用 `Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript`；编辑器关闭时可用 UE Python commandlet。导入过程不生成或播放怪物。
- 必要原生构建：`Tools/CargoStationStaff/build_native.ps1`，共享二进制被编辑器占用时不强行覆盖。
- UE 目标：`/Game/Monsters/CargoPorter/BP_CargoPorter`、`/Game/Monsters/CargoTechnician/BP_CargoTechnician`；共享新材质在 `/Game/Monsters/CargoStationStaff`。
- 实际导出、保存和构建状态分别记录于 `authoring_receipt.json`、`ue_delivery.json`、`build_receipt.json` 与 `Logs/`。脚本存在不表示导入完成，以保存回执为准。

未进行游戏、动画、多人、截图或渲染测试，由用户通过 **F6 → 怪物生成 → 搬运工 M-01 / 技术员 M-01** 体验。自动波次与搜索物品后续单独制作。

## 本轮落盘结果

两只蓝图、4 个骨骼网格（穿衣和独立衣物）、2 顶安全帽、8 个材质和 24 张贴图，共 **40 个 UE 资产已实际保存**。无界面 Python commandlet 完成，退出码 0；`FPSGAMEEditor` 与 `FPSGAME` 常规构建均成功。汇总回执为 `SourceAssets/CargoStationStaff20261014/V01/delivery_receipt.json`。

制作期间共享编辑器被外部打开，本任务为导入请求结束过正在运行的 PIE，没有启动编辑器或游戏。一次桥接热编译请求断连后，原操作最终记录 `NoChanges`；随后共享编辑器正常退出，最终交付通过常规 Editor 构建和后台 commandlet 完成，不依赖该热补丁。没有保存或覆盖原安保员蓝图、身体和动画。
