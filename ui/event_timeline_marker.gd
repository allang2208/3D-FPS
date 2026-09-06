extends Button
const Look := preload("res://ui/event_timeline_style.gd")
func _make_custom_tooltip(for_text: String) -> Object:
	var panel := PanelContainer.new()
	panel.add_theme_stylebox_override("panel",Look.Style.make_hud_surface(8,7))
	panel.custom_minimum_size.x = 240
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation",3)
	panel.add_child(column)
	var lines := for_text.split("\n")
	for index in lines.size():
		var label := Look.label(lines[index],12 if index==0 else 11,index==0)
		label.custom_minimum_size.x = 220
		label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		if index>0: label.add_theme_color_override("font_color",Look.MUTED)
		column.add_child(label)
	return panel
