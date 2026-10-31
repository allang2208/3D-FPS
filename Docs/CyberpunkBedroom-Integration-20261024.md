# 赛博朋克卧室：正式接入与试点退役

卧室 V3 已接入现有公寓 `/Game/GameMaps/L_CyberpunkApartment`，保存于 2026-10-24T19:11:31.245159+08:00。
本次在现有公寓内局部替换，不用试点整图覆盖正式关卡。

- 安装 17 组卧室陈设，替换原卧室床体引用；使用已保存的 V3 网格、材质和物理 UV 校准实例。
- 同步 19 个原有家具/附属 Actor 的已修正布局；储物 ID、柜门、电脑设备关联和床休息配置沿用现有身份。
- 两盏阅读灯接入现有 `AP7_Atmosphere` 的 Bed2 调度；保留其他灯光绑定、V21 时钟、其他房间、海湾和正式出生点。
- 已移除独立试点地图 `/Game/GameMaps/Design/L_CyberpunkBedroom_Pilot20261024`。退役地图归档在 `trash/cyberpunk-bedroom-pilot-retired-20261024/`，不再位于 Content 中，不作为第二套可运行场景。
- 旧试点安装入口已改为正式公寓入口，完整公寓的 V21 恢复链末尾也注册了卧室接入，避免重建后退回旧床或恢复测试地图。
- 保留正式公寓依赖的网格、材质、贴图与 Blender 制作源。目录中的 `BedroomPilot20261024` 是历史资产/制作源标识，不再对应独立测试场景。

当前唯一使用入口：

```text
open /Game/GameMaps/L_CyberpunkApartment
```

## 制作入口与记录

- 局部安装：`SourceAssets/CyberpunkApartmentRebuild20261022/BedroomPilot20261024/Integration20261024/install_level.py`
- 资产制作/发布：`BedroomPilot20261024/publish.py`，使用当前 V3 制作源并接入正式公寓。
- `approved-bedroom.json` 保存迁入的布局、材质、碰撞和灯具配置；不依赖退役地图继续存在。
- `installed.json` 记录正式地图保存；`retired.json` 记录退役文件及 SHA-256；`retired-entries.json` 记录停用的旧安装入口；`completed.json` 为本轮完成汇总。

本次仅完成接入、保存和清理，没有启动游戏或追加测试；实际游戏体验由用户测试。


> 2026-10-25：其余现有卧室已复用升级床铺，见 [床铺复用记录](CyberpunkApartment-BedReuse-20261025.md)。
