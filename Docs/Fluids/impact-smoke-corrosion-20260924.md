# 火球／陨星命中烟与毒雾、腐液

本轮针对爆燃后的烟气，以及现有毒蛆喷吐、落点和腐液表面。水花保持用户认可的版本。

## 运行入口

- 火球沿用 `NS_FireballImpactRealistic`，保留 ContactIgnition、OutwardCombustion、ShortEmbers。
- 陨星沿用 `NS_MeteorNaturalImpact`，保留 NativeExplosion、MolotovRoll 和原有燃烧地带。
- 两者仅替换旧的单层短烟，增加 ImpactRollingSmoke、ImpactGroundSmoke、ImpactLingeringSmoke。地面层只在朝上的实际接触面生成；空爆、墙面命中保留翻卷与余烟。
- 密度复用项目原创 Mantaflow `T_MuzzleSmokeMantaflowV14`，读取 R 通道，两帧插值。新材质自行做边缘归零、年龄侵蚀、轻微域扭曲及随机镜像；原枪口贴图和材质不改。
- 毒蛆 `UPoisonMaggotVenomFX` 使用既有 ISM 池。第三个实例参数传递归一化年龄，驱动同一密度序列；落点雾寿命改为 0.85–1.25 秒，现有 Tick 中加入轻微旋转流动。
- 毒蛆湿痕复用现有 40 个 Decal，每槽保留一个 MID，命中时设置随机种子和起始时间。0.24 秒内铺开，内部液纹缓慢流动；仍在 4.5 秒后开始淡出，2.5 秒内消失。
- 肥僵尸残留、地牢落点和腐液槽只在现有颜色、法线、粗糙度上增加小幅流动与气泡细节。原顶点覆盖、扩散到达时间、位移、透明边界不改。

## 开销边界

| 对象 | 近处 | 距离处理 |
|---|---|---|
| 火球新增烟 | 最多 9 粒，最长约 3.05 秒后结束 | 35 米后最多 4 粒，60–85 米淡出 |
| 陨星新增烟 | 最多 12 粒，最长约 3.05 秒后结束 | 35 米后最多 5 粒，60–85 米淡出 |
| 毒蛆喷吐拖尾 | 原有液滴；稀疏雾团 | 雾 18 米内，液滴 35 米内 |
| 毒蛆落点 | 9 液滴＋3 雾团 | 20 米后 4＋1，55 米外省略装饰效果 |
| 毒蛆共享池 | 192 液滴、48 雾、40 湿痕 | 池容量不增长，复用旧槽 |
| 腐液表面 | 小幅解析流动 | 无新增纹理、Actor 或模拟器 |

新增烟无实时流体解算、粒子碰撞、灯光或阴影；不修改项目光追／Lumen 设置。实际帧时未采样，以上为实现预算，不是测得的性能结果。

## 玩法与重建

没有改变法术伤害、击中时序、弹坑、燃烧地带、毒蛆毒伤或肥僵尸／地牢危险区域。毒蛆湿痕仍只是装饰，不新增伤害。

集中作者脚本：`Tools/Fluids/author_impact_smoke_corrosion.py`。三个 HLSL 源位于 `SourceAssets/ImpactSmokeCorrosion20260924/`。火球、陨星、毒蛆、肥僵尸与地牢相关重建脚本接入对应局部作者函数。本轮执行集中脚本，未执行旧全量重建链。原资产备份位于同目录 `Backup/`，不替代其他资产制作记录。

## 交付状态

10 个资产已保存，清单见 `SourceAssets/ImpactSmokeCorrosion20260924/assets-saved.json`。材质后台作者进程 `author-cmd-03.log` 退出码 0；两个 Niagara 系统在 `author-cmd-02.log` 已编译保存。早期命令行制作遇到旧毒雾节点 rooted 删除断言，现集中作者脚本保留断开的旧节点，改接新输出图；再次执行复用有标识的新节点，不叠加图层。

常规 C++ 构建 `Saved/BuildEditor/build-20260924-111854.log` 返回 Succeeded／Target is up to date；结果另记 `build-status.json`。未主动打开交互编辑器、游戏、PIE 或预览，没有进行视觉／性能测试，最终观感交由用户确认。
