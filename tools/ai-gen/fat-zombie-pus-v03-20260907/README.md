# 脓液材质 V03：偏写实候选
独立演示项目：E:/3d/fat-zombie-pus-preview-v03-20260907/project.godot。
本轮只改液体材质，保留 V02 的地形网格、断层裁切、分帧采样、随机外形与伤害逻辑。尚未替换主项目引用。

## 材质变化
降低荧光黄绿，使用污浊的橄榄黄绿和浅赭色；分层域扭曲噪声替代大块色斑；去掉规则扩散圆环。
低速连续流动，加入稀疏细小悬浮杂质。按实际坡面计算微小凹凸法线，粗糙度变化与薄层反光表现湿润感。边缘降低不透明度、变薄，但仍可见，展开裁切范围沿用原 UV 半径。
不是流体求解器，也没有真实体积散射；这是现有性能范围内的材质改进候选，审美效果以用户反馈为准。

## 对照与验证
comparison.png / Material-comparison.gif：左 V02，右 V03，使用同一随机种子、地面、相机和照明。
共同环境增加天空反射及一个掠射方向光，便于观察两版高光差异，并非仅为新版增亮。
render.log 完成标记 PUS_V03_RENDER_COMPLETE，render-error.log 为空。
terrain-v03.png：在 V02 原有六地形夹具与原灯光下再次验证；terrain-validation.json 为贴地和判定检查。
原伤害组件没有修改，未额外声称完成主项目游戏验收。V02 的静态地面、同一支撑碰撞体及采样精度边界继续适用。

## 模型来源
Fat Zombie Idle Animated，vicente betoret ferrero (deathcow)，CC BY 4.0。
https://sketchfab.com/3d-models/fat-zombie-idle-animated-ab45b1f5bf0947fa8a3f2d349f47e0ba
沿用已修改外观、动作的 backfall V02 模型。

## 仓库运行
先运行本目录 `python prepare.py`，从相邻 backfall V02 复制 model.glb，再以此目录为 Godot --path。test.gd 检查生命周期与伤害；terrain_check.gd 检查六地形并输出到 user://。原始日志未作为运行依赖上传，验证汇总见 docs/monster-publication-20260907.md。此项目仍为独立候选。
