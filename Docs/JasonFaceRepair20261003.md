# Jason 独立头部脸面修复

用户截图：脸部大面积露空、眼球和牙齿外露，下颌出现白色区域。

## 根因

`MI_Face_Skin_Baked_LOD0` 并非无裁切的完整脸部材质。它启用了 `BLEND_Masked` 基础属性覆盖，其父材质 `M_skin_unified_baked` 内部调用的 `MF_skin_bakedInputs` 把 `T_head_maskDown02` 的 R 通道直接连到 `MakeMaterialAttributes.OpacityMask`。

该遮罩在脸部区域为黑色、下部边缘为白色。上一轮删除身体上的重叠脸面以后，给独立头部指定这份材质，仍会裁掉脸面。此前只根据材质名称和外层纹理引用判为完整皮肤，是接入遗漏。

源头部与身体脸面使用同套 UV；导出的 `T_Jason_head` 为正常皮肤贴图，Alpha 全为 255。此次保留网格、骨架、头发绑定和皮肤贴图。

## 修复制作

`Tools/PlayerBody/build_jason_face_material.py` 复制源材质为：

`/Game/Characters/ModularOutfit20260924/JasonPlayer20261003/MI_Jason_FullFace`

只把派生材质的混合模式明确设为 Opaque，保留其颜色、法线、粗糙度、散射和其他原生皮肤输入。新材质保存成功后才更新 `player_body.json` 中 Jason 的 `lambert1` 材质引用。该配置由现有独立头部路径统一应用于本地和远端角色，无需新增联机字段。

`finalize_jason_body.py` 同步制作该材质并将其写入身体制作回执，后续 `publish_jason.py` 不再恢复旧遮罩材质。

## 交付证据与边界

材质保存回执：`SourceAssets/JasonFaceRepair20261003/face_material_saved.json`。制作脚本在材质保存失败时停止，不发布缺失资产路径。

未启动游戏、渲染或联机回归；最终游戏画面由用户测试。当前游戏中已创建的角色持有旧配置，重新开始游戏后加载新引用。
