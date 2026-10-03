# M07 V37：修复主体灰色默认材质

用户提供截图：背膜纹理正常，主体灰色。2026-10-03 当前编辑器日志明确记录：

```text
Material /Game/Monsters/BlindSupplicantM07/Materials/M07_Body_OriginalV07.M07_Body_OriginalV07 missing usage flag Clothing! Default Material will be used in game.
```

V36 将身体材质中的膜片折边接入布料，导致整个身体材质分区需要 Clothing 着色器用途；该母材质只启用了 SkeletalMesh。背膜材质原本已支持 Clothing，所以呈现主体灰、背膜正常。主体材质槽以及 BaseColor／Normal／Roughness／Metallic 四张贴图引用均完整，无需重导贴图或重做 UV。

已通过现有编辑器批次桥，将主体材质 Clothing 用途由 false 设为 true，完成材质编译，编译错误数组为空，修改前后四张贴图引用一致。首次保存被 PIE 阻挡；用户随后关闭整个 UE，改用后台 commandlet 完成保存，**当前主体材质已实际落盘，回执 `saved: true`，后台进程正常退出（0）。** 未重新导入网格、修改背膜物理、动作或数值，无需原生模块构建。

第一次编辑器读取得到的四张贴图保留在回执 `initial_diagnosis`。后台 `-nullrhi` 进程的 `GetMaterialUsedTextures` 从渲染资源查询得到空列表，该结果不代表材质图丢失贴图，也不作为视觉判断。实际保存日志为 `Saved/Logs/M07Import-20261003-232447.log`。

同步修订 `Tools/BlindSupplicantM07/import_witch_cloth_v36.py`：绑定布料之前，给涉及的材质补齐 Clothing 用途、编译并保存。避免后续重新制作又出现同样缺项。

- 修复脚本：`Tools/BlindSupplicantM07/repair_body_cloth_material_v37.py`
- 已编译材质继续保存：`Tools/BlindSupplicantM07/save_body_cloth_material_v37.py`
- 修改前材质备份、前后属性与保存回执：`SourceAssets/BlindSupplicantM07Meshy20261001/BodyClothMaterialV37/`
- 本轮只检查相关日志、材质槽、贴图引用与编译结果；未启动 PIE、渲染或游戏验收。
