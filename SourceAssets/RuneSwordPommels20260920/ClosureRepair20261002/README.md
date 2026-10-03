# 陨星配重锤的外壳朝向修复

用户报告唐刀安装 `ballast_hardened` 后锤体表面像空壳。本次仅排查并修复这个共用配重，不启动游戏或制作验收渲染。

## 原因

唐刀、符文长剑、寒晶剑和高地双手剑通过 `shared-sword-pommels.json` 共用 `SM_RunePommel_Meteor`。唐刀只用 `tang_dao_surface_v2` 覆盖金属材质，并没有使用另一份锤体模型。

`MeteorBody` 原始旋转体的三角面绕序朝内。源锤体没有开口边，带倒角的源锤体侧面和端面朝内，实际 UE 资产导出的锤体也保留了这个朝向。单面不透明材质从外侧会剔除这些背面，因而只能看到外面的加强筋和装饰，误看成没有封闭。

排查记录：`geometry_findings.json`（修复前源文件、FBX 和实际 UE 导出）、`asset_findings.json`（实际模型及各宿主材质）。原锤体侧面样本外向 0、内向 40；修复前源锤体有符号体积约 −349.06 cm³，重新统一外向后为 +349.06 cm³，开口边仍为 0。记录见 `source_repair_receipt.json`。

原金属材质、唐刀表面材质和寒晶铜色主题均为不透明单面材质；唐刀没有透明或挖空设置。问题属于共享锤体的制作源。

## 修改

- `author_models.py`：陨星锤体载入时统一外向面绕序，随后才生成倒角，避免重新制作时恢复错误。
- `RuneSword_Pommels_Editable.blend` 与 `RuneSword_Pommels_PBR.blend`：修正锤体朝向，保留真实安装端、形状、尺寸和其他配重。
- `bake_export.py -- --only meteor`：仅重新制作陨星配重的五张 PBR 贴图及 FBX/GLB；保留其他两款配重。重建时保留固定材质槽名，使用新烘焙图而非旧的打包图像。
- `export_lods.py`：制作包含全部三档正确朝向网格的 FBX LOD Group，源三角面分别为 31198、17158、7799。
- `import_repair.py`：更新原共用网格和五张纹理；沿用原资产路径、安装配置和现有主题材质。接入时现有编辑器已退出，因此最终用无界面 commandlet 导入并保存完整三档 LOD，没有重新启动编辑器。`import_receipt.json` 的 `complete` 为 true，保存六个资产；完成日志为 `import-resume-commandlet.log`，退出码 0。

修复前制作源、导出文件、贴图和 UE 资产保存在 `Before`，实际 UE 排查导出为 `CurrentUE_Meteor.fbx`。本次没有改变配重属性、ID、唐刀前后朝向或安装配置。

保存后的实际 UE 三档网格留存为 `SavedUE_Meteor_LODs.fbx`；本问题范围内的面朝向记录见 `geometry_after.json`。

修复后的源锤体侧面样本为外向 40、内向 0；带倒角锤体有符号体积约 +349.01 cm³。已保存 UE 的 LOD0/1/2 完整配重有符号体积约为 +383.15/+383.01/+383.27 cm³，三档均已载入修正后的外向锤体。装饰筋条各有内外表面，因此完整配重侧面统计中的内向面不代表锤体仍朝内。

没有运行游戏、截图、渲染或追加回归测试，游戏效果由用户自行测试。
