---
name: ue5-clothing-workflow
description: FPSGAME 玩家服装制作、上衣裤装衔接、扎腰、腰臀覆盖和裤靴搭配的本机维护源入口。
---

读取 [玩家服装维护源](../_shared/ue5-clothing-workflow/SKILL.md)。工程生产入口、配方与交付范围见 [腰部衔接工作流](../../Docs/Characters/garment-waist-workflow.md)。共用规则在个人技能目录维护，不叠加旧镜像；跨机器交付时须另行导出依赖。 为什么：个人目录不随工程仓库传输，明确依赖可避免换机后入口失效。

- 腰带作为独立槽位接入、男女腰臀包络和侧挂箭袋，读取 [腰带与箭袋](../ue5-item-asset-workflow/references/belts-and-quivers.md)。 为什么：「腰带与箭袋」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

- 女体独立领口的头身表面、内折边及 LOD 配对见[ST6 女性领口](references/st6-female-collar.md)。 为什么：不同几何与变形需求需要不同制作路线，统一套用面数或生成参数会损失有效细节。
