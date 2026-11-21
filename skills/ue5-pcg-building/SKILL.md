---
name: ue5-pcg-building
description: UE5.6-UE5.8 PCG generation and runtime-heightfield ground workflow for modular buildings, blockouts, facade rules, runtime generation, and layered terrain ground materials. Use when requests involve Procedural Content Generation (PCG), Shape Grammar, lot-based building spawn, deterministic random seeds, density/filter pipelines, converting designer constraints into reusable PCG graphs, or the detail/layering of a streamed non-Landscape ground surface.
---

# 共用规则入口

**第一条（FPSGAME）　文件位置与引用路径。** 从当前工程的[制作目录与功能索引](../../Docs/Production/README.md)和[存储规则第 4.1 节](../../WORKFLOW.md#41-存储分配与文件操作边界)查找对应功能。先确定制作源、正式资产和输出目录，再创建或引入文件。工程 Content 资产用 `/Game/...` 包名引用，制作脚本从工程根或已配置的制作源根解析相对路径。交付时在同一功能条目登记实际位置、引用及备份状态。

共用流程读取仓库发布快照：[ue5-pcg-building](../_shared/ue5-pcg-building/SKILL.md)，不要叠加旧镜像流程。 为什么：共用流程只维护一个来源，避免工程镜像与个人版本给出相互冲突的步骤。

工程专属规则以当前 AGENTS.md、WORKFLOW.md 和本次用户要求为准。维护源不可用或需要查找未合入的工程经验时，读取[整理前工程资料](LOCAL-HISTORY.md)及原 references；其中历史测试与协调条款不构成执行授权。 为什么：当前用户授权决定操作范围，历史测试与协调记录不能自动成为新任务授权。

本入口随仓库提供共用规则快照；日常修订仍回到个人维护源，发布时更新快照。 为什么：相对链接支持换机阅读，单一维护源避免两套规则分叉。

## 地牢表面与整站重复控制

墙面颗粒、板缝、墙裙厚度、稀疏剥落与积灰，以及固定机位对照，读取 [地牢表面制作](references/dungeon-surface-authoring.md)。已认可样板向整站扩展时，按承接面与使用痕迹组织变化，保留用户指定的原墙地材质和玩法。 为什么：样板与正式入口生命周期不同，明确边界能保留共用资产并清除退役入口。

## 场景光源与最低照明

制作或调整室内灯具、吊灯方向、廊下和暗角照明时，读取 [灯具与照明层次标准](references/fixture-lighting-standard.md)。向下灯不得向上直射天花板；保留已认可主灯，按实际楼层补光。 为什么：「灯具与照明层次标准」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

## 固定观景点的城市远景与栏杆

公寓海湾建筑分层、办公条形窗灯、动态广告/水面反射、侧挡板替换玻璃栏杆及增量重建，读取 [远景与栏杆制作](references/layered-harbor-and-balcony.md)。保留当前天气和共享资产，版本编号不作为退役依据。 为什么：「远景与栏杆制作」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

## 城市街区与室内接触

围绕公寓生成街道、楼群、沿岸绿化，修复道路衔接、停车穿插及实例成本时，读取 [城市分区制作](references/city-district-production.md)。灯具厚度、厨房接触和自然电线走线读 [公寓接触与线材](references/apartment-contact-and-cables.md)。 为什么：「城市分区制作」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

## 流送场景入口与多人室内适应

换图后碰撞晚到、按控制器安全重试和逐视图室内亮度，读取 [安全出生与室内视图](references/streamed-entry-and-interior-view.md)。 为什么：「安全出生与室内视图」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

## 丘陵雨林植被与水坑

修改雨林专属草、联机生态参数或扩大水坑选址时，读 [雨林植被与局部积水](references/hills-vegetation-and-pools.md)。 为什么：「雨林植被与局部积水」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

丘陵道路保护、河湖高度连续、树簇与林床关联、扫描岩壁补面，读取 [丘陵道路保护、河湖高度连续、树簇与林床关联、扫描岩壁补面](references/hills-scenery-continuity.md)。

可修复酒馆的房壳、通行碰撞和桌面摆放见[酒馆两态与室内承托](references/reusable-interior-assemblies.md#丘陵酒馆的残破与修复)。

丘陵铁匠铺的铁砧侧光与炉膛火光见[铁匠铺照明](references/fixture-lighting-standard.md#铁匠铺的铁砧与炉膛)。木工驱动水晶、草药铺瓶身与药液、店铺同机位对照见[店铺工作台近景](references/reusable-interior-assemblies.md#村庄店铺的工作台近景)。
