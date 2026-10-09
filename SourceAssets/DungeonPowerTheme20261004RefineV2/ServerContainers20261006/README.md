# 发电区服务器抽拉容器

2026-10-06：按用户截图，将红圈内的上排左侧服务器模块拆为活动分件，接入现有搜寻容器。

## 已保存内容

- 原发电区测试地图中的 `PowerTheme_ControlServerRack01`、`PowerTheme_ControlServerRack02` 已由静态 Actor 替换为 `ColdSteelSceneContainer`，保留原位置、朝向、大小及显示名称。
- 准星指向服务器按 E，原生容器系统用 0.55 秒平滑抽出模块 32 厘米，随后打开原搜寻界面。每台服务器拥有独立容器身份和一页空间；关闭界面后模块保持拉出，再次交互沿用已搜寻状态。
- 活动模块保留原把手、面板、指示灯、螺钉和锁孔；补充约 59 厘米深的金属机壳、通风缝、内部板件、滑轨和后接头。柜体内对应位置已做实际开口和固定导轨，不会留下原来的重复模块或实心堵板。
- 保留既有中文铭牌及不拉伸的文字 UV；只导入两个专用派生网格，没有重导共享服务器母资产，没有新增纹理或原生 C++ 类。
- 柜体使用 Nanite；活动模块使用普通静态网格。复用原容器提示、绿色/黄色描边、距离与遮挡判定，只有开启期间启用原生 Tick。
- 原总控室四扇门的正数开合速度参数也已在本次同一地图保存中补齐。

## 路径与制作源

- 地图：`/Game/GameMaps/Design/L_PowerTheme20261004_Subject`。
- 资产：`/Game/Dungeons/PowerTheme20261004/ServerContainers20261006/Meshes/SM_Power_ServerContainer_Body`、`SM_Power_ServerContainer_Cartridge`。
- 来源：既有 `TextCards20261005/Authored/SM_Archive_ServerRack_V1.fbx`，其母模型来自本项目档案区 `Equipment20260930`。现有模型、材质与纹理直接复用，来源散列记录在 `manifest.json`。
- 可编辑源：`Authored/ServerPulloutContainer.blend`；分件制作：`author.py`；后台导入及地图接入：`install.py` / `install_background.ps1`。
- 保存回执：`Receipts/install.json`，阶段为 `map_saved`，两个网格、两个独立容器。修改前地图保留在 `Snapshots/`。
- `Scripts/server_container_revision.py` 已接到样板重建与 `Config/module-drafts.json` 输出。模块草案使用原生 `scene_container` 描述，柜体和模块进入资产队列，不再把对应服务器合并为静态零件；仍未发布到正式随机池。

本轮完成建模、导出、导入和保存，没有启动游戏、PIE、截图、渲染或测试。由用户自行测试视觉、碰撞和搜寻交互。
