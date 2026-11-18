# Project Adapter

Use this file to map generic skill workflow to a concrete project. 原因：项目适配页用于连接通用流程与具体目录，避免把某个项目的路径误当通用前提。

## Fill-in Items
- Module names and Build.cs paths
- Core gameplay classes and component names
- Blueprint asset paths under `/Game/...`
- Save slots, map names, and game mode classes
- Known project constraints and coding conventions

## Current Default
- Keep this skill generic by default. 原因：通用技能面向不同工程，项目专属路径和约束应保留在适配层。
- Add project-specific mappings here only when needed. 原因：通用适配页只需记录真实项目差异，无需求的映射会增加维护噪声。
