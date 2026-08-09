@tool
extends EditorPlugin

const AUTOLOAD_NAME := "AudioManager"
const AUTOLOAD_PATH := "res://addons/audio_manager_lite/audio_manager.gd"


func _enter_tree() -> void:
	add_autoload_singleton(AUTOLOAD_NAME, AUTOLOAD_PATH)


func _exit_tree() -> void:
	remove_autoload_singleton(AUTOLOAD_NAME)
