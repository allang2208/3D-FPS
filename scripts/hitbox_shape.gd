class_name HitboxShape
extends CollisionShape3D
## 部位命中盒：挂在敌人身上的独立碰撞形状，携带伤害倍率
## 射线命中后由 enemy.gd 按 shape 索引查倍率（Unity Hitbox 的 Godot 实现）

@export var multiplier := 1.0
