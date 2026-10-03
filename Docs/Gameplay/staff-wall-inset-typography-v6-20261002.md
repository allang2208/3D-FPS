# 员工区厕所位置、水壶与字体 V6

按用户本轮纠正，将厕所移到原 L 形突出墙体后面的空间。入口在活动区原 y=8 墙面、x=12.2m 处；内部占用 x=9–15m、y=8–12m 的 6×4m 区域。移除 V5 外搭厕所的场景实例，复用原有正面及西侧墙体，将缺少的背面/侧面围护、地板、顶棚补在墙后。原正面墙体、完整瓷砖及门框同步开孔，使用 1.12m 宽、2.32m 高的入口，墙体碰撞随孔洞更新。

厕所内保留 V5 马桶，重新定位洗手盆、镜子、照明；补内侧完整墙裙、地砖、通风格栅、隔板、纸卷和直接复用作者函数的排水格栅。门向内开启并保持打开形态。公共活动区域恢复原有空间，未增加新的外搭盒形墙体。

水壶换用独立的干净不锈钢材质，金属度 1、基础粗糙度 0.27，加入随像素覆盖淡出的微弱拉丝法线。壶体轮廓更圆滑，补底座、壶盖接缝、铰链、圆滑手柄、空心壶嘴、内嵌水位窗、刻度、开关和指示灯。电线从底座应力释放套出线，沿台面连续走到墙上三孔插座，末端安装插头与防弯套；插座背面贴合原墙面瓷砖。

## 用户要求的字体审计

审计覆盖三个员工主题房间的告示、门牌、引导标牌和卫生间牌。

- 旧横向标牌统一取样 502×308 的近方形区域。淋浴牌的物理比例为 1.35:0.42，横纵缩放比约 1.972，字形明显横向拉长。
- 公告底部提醒使用 1000×400 区域，物理牌面为 0.68×0.115m，横纵缩放比约 2.365。
- 四张公告正文的旧比例约 0.879，字形略窄；公告顶栏的比例已正确。
- 新图集按各牌面的真实物理比例分配区域。文字重新以本机字体原生绘制，只调整布局坐标和统一字号，不对字形作横纵分开的缩放。字号以旧字体的竖向尺度为依据，保持文字高度；窄提醒区域保持其原文字高度。

图集审计：27 个区域、103 段公告文字，没有越界文字。
模型审计：29 个文字贴面，横纵比例最大误差约 0.000207%，没有超过 0.5% 阈值的变形。
四张地图保存时另记录实际字体 Actor 的缩放，结果见安装回执；审计不包含游戏截图、运行测试或用户视觉验收。

实际落盘：10 个网格、6 个材质/纹理资产已导入、完成必要资源构建并保存；四张原地图保存完成，后台导入退出码 0。地图审计覆盖 14 个文字组合实例，未发现非等比 Actor 缩放。

新资源命名空间：`/Game/Dungeons/StaffLiving20261002/WallInsetV6`。
制作源：`SourceAssets/DungeonStaffLiving20261002/WallInsetV6/Authored/StaffLivingTheme_WallInsetV6.blend`。
作者入口：`Scripts/author_wall_inset_v6.py`、`Scripts/author_typography_v6.py`。
导入入口：`Scripts/import_wall_inset_background_v6.ps1`、`Scripts/import_wall_inset_v6.py`。
字体回执：`WallInsetV6/Authored/typography-audit.json`、`typography-geometry-audit.json`。
安装和地图状态：`WallInsetV6/install.json`；交付状态：`WallInsetV6/completion.json`。
四张原地图及配置恢复备份：`WallInsetV6/Backups`。

本轮只改资产与作者脚本，没有 C++ 改动，不要求重新构建原生目标。不主动打开、关闭或重启编辑器，未运行游戏、PIE 或验收渲染。效果由用户测试。

```text
open /Game/GameMaps/Design/L_StaffRecreation_Subject
```

完整主题仍为 `open /Game/GameMaps/Design/L_StaffLiving_Theme_Subject`。
返回主场景：`open /Game/GameMaps/DayNight_Lighting`。
