# 蓝色魔法粉尘材质

按用户要求，将瓶内粉末与晶粒改为蓝色魔法粉尘。

- 粉末：原颜色纹理的明暗细节映射为深蓝色，保留烘焙法线与粗糙度，降低金属反射并添加低强度蓝色微光。
- 晶粒：较明亮的冰蓝色，保持颗粒几何。
- 玻璃与金属盖的材质槽不变；独立材质为 `M_magic_dust_blue_powder`、`M_magic_dust_blue_grains`，原始材质仍保留。
- 脚本 `Tools/AssetPipeline/apply_blue_magic_dust.py` 按语义材质槽绑定；常规重导入末尾重新应用蓝色变体。
- 本次为 UE 材质变体，Delivery GLB/Blender 保留原始母版配色；没有重启 5080 建模。

导入结果：`Saved/BlueMagicDustMaterial.json`；运行日志：`Saved/BlueMagicDustRuntime.log`。

实际运行：首轮粉尘检查通过，强化石拾取相关两项失败；未修改玩法，独立新测试档 B 复核 27 项全部通过，无材质编译回退。两轮日志均保留，首轮原因未在本材质任务内确定。已查看最终游戏画面。

![游戏内蓝色粉尘](../../Saved/BlueMagicDustInGame.png)
