# Project Adapter

Use this file to map generic PCG building workflow to a concrete project. 原因：项目适配页连接通用 PCG 流程与具体目录，避免把单项目路径写成通用前提。

## Fill-in Items
- PCG graph assets under `/Game/...` and owning map(s)
- Building module mesh sets and pivot conventions
- Lot, district, or biome tags used by filters
- Runtime generation trigger source (volume, player source, subsystem)
- Target output mode (ISM/HISM, actor spawn, dynamic mesh)
- Save/load and replication requirements for generated results

## Current Default
- Keep this skill generic by default. 原因：通用技能面向不同工程，项目专属路径和约束应保留在适配层。
- Add project-specific mappings here only when needed. 原因：通用适配页只需记录真实项目差异，无需求的映射会增加维护噪声。
