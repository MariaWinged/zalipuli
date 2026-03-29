extends Control
class_name BottleView

signal bottle_clicked(index: int)

var bottle_index: int = -1
var capacity: int = 4
var values: Array = []          # bottom -> top
var color_map: Dictionary = {}  # int -> Color
var is_selected: bool = false

const GLASS_FILL := Color(1, 1, 1, 0.04)
const GLASS_LINE := Color(1, 1, 1, 0.85)
const SELECT_LINE := Color(1.0, 0.9, 0.35, 1.0)
const EMPTY_SLOT := Color(1, 1, 1, 0.05)

func setup(index: int, stack: Array, p_capacity: int, p_color_map: Dictionary) -> void:
	bottle_index = index
	values = stack.duplicate()
	capacity = p_capacity
	color_map = p_color_map
	queue_redraw()

func set_selected(v: bool) -> void:
	is_selected = v
	queue_redraw()

func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT and event.pressed:
		emit_signal("bottle_clicked", bottle_index)

func _draw() -> void:
	var w := size.x
	var h := size.y

	var neck_w := w * 0.38
	var neck_h := 36.0
	var neck_x := (w - neck_w) * 0.5
	var neck_y := 8.0

	var body_margin_x := 18.0
	var body_top := neck_y + neck_h - 4.0
	var body_bottom_margin := 14.0
	var body_rect := Rect2(
		Vector2(body_margin_x, body_top),
		Vector2(w - body_margin_x * 2.0, h - body_top - body_bottom_margin)
	)

	var neck_rect := Rect2(Vector2(neck_x, neck_y), Vector2(neck_w, neck_h))

	# Стекло
	draw_rect(neck_rect, GLASS_FILL, true)
	draw_rect(neck_rect, GLASS_LINE, false, 3.0, true)

	draw_rect(body_rect, GLASS_FILL, true)
	draw_rect(body_rect, GLASS_LINE, false, 3.0, true)

	# Внутренняя область жидкости
	var liquid_rect := body_rect.grow(-10.0)
	liquid_rect.position.y += 8.0
	liquid_rect.size.y -= 8.0

	var slot_h := liquid_rect.size.y / float(capacity)
	var gap := 4.0

	# Пустые слоты
	for i in range(capacity):
		var y := liquid_rect.position.y + liquid_rect.size.y - (i + 1) * slot_h
		var slot_rect := Rect2(
			Vector2(liquid_rect.position.x + 2.0, y + gap * 0.5),
			Vector2(liquid_rect.size.x - 4.0, slot_h - gap)
		)
		draw_rect(slot_rect, EMPTY_SLOT, true)

	# Жидкость
	for i in range(values.size()):
		var value: int = int(values[i])
		var c: Color = color_map.get(value, Color(1, 1, 1, 0.9))

		var y := liquid_rect.position.y + liquid_rect.size.y - (i + 1) * slot_h
		var seg_rect := Rect2(
			Vector2(liquid_rect.position.x + 2.0, y + gap * 0.5),
			Vector2(liquid_rect.size.x - 4.0, slot_h - gap)
		)

		draw_rect(seg_rect, c, true)

		# Блик
		var highlight_w := max(5.0, seg_rect.size.x * 0.12)
		var highlight_rect := Rect2(
			seg_rect.position + Vector2(5.0, 3.0),
			Vector2(highlight_w, max(2.0, seg_rect.size.y - 6.0))
		)
		draw_rect(highlight_rect, c.lightened(0.22), true)

	# Внешняя подсветка выбора
	if is_selected:
		draw_rect(body_rect.grow(6.0), SELECT_LINE, false, 4.0, true)

	# Индекс флакона
	var font := ThemeDB.fallback_font
	var font_size := 16
	var txt := str(bottle_index)
	draw_string(font, Vector2(w * 0.5 - 5.0, h - 2.0), txt, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, Color(1, 1, 1, 0.7))
