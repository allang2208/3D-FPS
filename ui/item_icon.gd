extends RefCounted
## Presentation-only lookup: old saved instances receive new art without mutation.

const BACKPACK_FIREARM_PATHS := {
	# These are exported from the current GunsmithPreview model/material pipeline.
	"akm": "res://assets/ui/icons/equip/gunsmith/fps_akm_gunsmith.png",
	"qbz191": "res://assets/ui/icons/equip/gunsmith/fps_qbz191_gunsmith.png",
	"fps_akm": "res://assets/ui/icons/equip/gunsmith/fps_akm_gunsmith.png",
	"fps_hk416": "res://assets/ui/icons/equip/gunsmith/fps_hk416_gunsmith.png",
	"fps_p9": "res://assets/ui/icons/equip/gunsmith/fps_p9_gunsmith.png",
	"fps_m16": "res://assets/ui/icons/equip/gunsmith/fps_m16_gunsmith.png",
	"fps_qbz191": "res://assets/ui/icons/equip/gunsmith/fps_qbz191_gunsmith.png",
}

const EQUIPMENT_FIREARM_PATHS := {
	# Equipment slots keep the large upward-diagonal presentation renders.
	"akm": "res://assets/ui/icons/equip/fps_akm.png",
	"qbz191": "res://assets/ui/icons/equip/fps_qbz191.png",
	"fps_akm": "res://assets/ui/icons/equip/fps_akm.png",
	"fps_hk416": "res://assets/ui/icons/equip/fps_hk416.png",
	"fps_p9": "res://assets/ui/icons/equip/fps_p9.png",
	"fps_qbz191": "res://assets/ui/icons/equip/fps_qbz191.png",
	"fps_m16": "res://assets/ui/icons/equip/fps_m16.png",
}

static func path(item: Dictionary) -> String:
	var id := str(item.get("id", ""))
	if id in ["fps_akm", "fps_hk416", "fps_p9", "fps_qbz191", "fps_m16", "ammo_762", "ammo_556", "ammo_9", "ammo_58"]:
		return "res://assets/ui/icons/equip/" + id + ".png"
	return str(item.get("icon", ""))

static func backpack_path(item: Dictionary) -> String:
	var explicit := str(item.get("backpack_icon", ""))
	if not explicit.is_empty():
		return explicit
	return str(BACKPACK_FIREARM_PATHS.get(str(item.get("id", "")), path(item)))

static func equipment_path(item: Dictionary) -> String:
	var explicit := str(item.get("equipment_icon", ""))
	if not explicit.is_empty():
		return explicit
	return str(EQUIPMENT_FIREARM_PATHS.get(str(item.get("id", "")), path(item)))
