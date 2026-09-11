# 规则机械旋钮修整

用户指出顶部与侧面旋钮仍粗糙。本轮在 Blender 中替换剩余生成控制件，保留已验证的光学通道、目镜防滑圈、主体布局和安装基准。

原粗糙感来自生成面不规则、圆度不稳定，以及重采样/减面后留下的软塌端面。增加三角面不会自动恢复规则机械结构。本次使用解析旋转曲面重建两枚旋钮：平整端面、上下倒角、40 道等距浅槽、12 个径向刻度和同轴底座。当前可见几何全部由本地规则建模构建；5080 母版保留为设计和尺寸来源，不宣称本次是重新生成。

最终 18,040 三角面，上一版 22,620；3 材质槽、4 张 2K 烘焙纹理。主体边界、非流形、退化面均为零；玻璃仍为双面薄片。2× FOV、视野扩展和底座 25 mm 不变。

`build_model.py` 读取上级母版，生成规则零件、烘焙、导出和渲染；`Scope2X_SeparateParts.blend` 是烘焙前分件源，旋钮及刻度可独立编辑；`PrismScope2X_Editable.blend` 是烘焙导出版本。`controls_closeup.png` 为真实 Blender 近景。

当前 UE 资产 `/Game/Weapons/PrismScope2XMachined/SM_PrismScope2X.SM_PrismScope2X`，独立路径避免覆盖使用中的资产。角色路径和打包目录同步更新。原生编译成功；导入 PASS 且保存成功，commandlet 退出码 1 为已有 GameFeatureData/HTTP 端口错误。最终游戏验证见 `machined-final` 与 `acceptance.json`，不以导入标记替代实机验收。
