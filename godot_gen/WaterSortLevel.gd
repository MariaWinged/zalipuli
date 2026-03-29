extends Control

@export var bottle_scene: PackedScene
@export var capacity: int = 4

# ВАЖНО:
# Каждый массив = один флакон
# Порядок значений: СНИЗУ -> ВВЕРХ
# Пример: [1, 2, 2, 3] значит снизу 1, сверху 3
@export var level_data: Array = [
	[1, 2, 3, 4],
	[4, 3, 2, 1],
	[1, 3, 2, 4],
	[4, 2, 1, 3],
	[],
	[]
]

# Можно задать свои фиксированные цвета:
# {1: Color(...), 2: Color(...)}
@export var custom_colors: Dictionary = {}

@onready var bottles_container: HFlowContainer = %Bottles
@onready var status_label: Label = %StatusLabel
@onready var reset_button: Button = %ResetButton

var initial_level_data: Array = []
var bottles_data: Array = []
var bottle_views: Array = []
var color_map: Dictionary = {}
var selected_index: int = -1
var is_completed: bool = false

const FALLBACK_PALETTE := [
	Color8(255, 99, 132),
	Color8(54, 162, 235),
	Color8(255, 206, 86),
	Color8(75, 192, 192),
	Color8(153, 102, 255),
	Color8(255, 159, 64),
	Color8(46, 204, 113),
	Color8(231, 76, 60),
	Color8(26, 188, 156),
	Color8(241, 196, 15),
	Color8(52, 152, 219),
	Color8(155, 89, 182),
]

func _ready() -> void:
	if bottle_scene == null:
		push_error("Не назначен bottle_scene в WaterSortLevel.tscn")
		return

	reset_button.pressed.connect(_on_reset_pressed)

	initial_level_data = _deep_copy_level(level_data)
	_build_level(initial_level_data)

func set_level(new_level: Array) -> void:
	initial_level_data = _deep_copy_level(new_level)
	_build_level(initial_level_data)

func _build_level(data: Array) -> void:
	bottles_data = _deep_copy_level(data)
	selected_index = -1
	is_completed = false
	color_map = _make_color_map(bottles_data)

	_clear_bottle_nodes()
	_create_bottle_nodes()
	_refresh_views()
	_update_status()

func _clear_bottle_nodes() -> void:
	for child in bottles_container.get_children():
		child.queue_free()
	bottle_views.clear()

func _create_bottle_nodes() -> void:
	for i in range(bottles_data.size()):
		var bottle: BottleView = bottle_scene.instantiate()
		bottle.bottle_clicked.connect(_on_bottle_clicked)
		bottles_container.add_child(bottle)
		bottle_views.append(bottle)

func _refresh_views() -> void:
	for i in range(bottles_data.size()):
		var bottle: BottleView = bottle_views[i]
		bottle.setup(i, bottles_data[i], capacity, color_map)
		bottle.set_selected(i == selected_index)

func _on_reset_pressed() -> void:
	_build_level(initial_level_data)

func _on_bottle_clicked(index: int) -> void:
	if is_completed:
		return

	if index < 0 or index >= bottles_data.size():
		return

	# Ничего не выбрано
	if selected_index == -1:
		if bottles_data[index].is_empty():
			return
		selected_index = index
		_refresh_views()
		_update_status()
		return

	# Повторный клик снимает выбор
	if selected_index == index:
		selected_index = -1
		_refresh_views()
		_update_status()
		return

	# Пытаемся перелить
	if _try_pour(selected_index, index):
		selected_index = -1
		_refresh_views()

		if _is_solved():
			is_completed = true
			status_label.text = "Уровень пройден!"
		else:
			_update_status()
	else:
		# Если перелить нельзя, но кликнули по непустому — просто меняем выбор
		if not bottles_data[index].is_empty():
			selected_index = index
			_refresh_views()
			_update_status()

func _try_pour(from_idx: int, to_idx: int) -> bool:
	if from_idx == to_idx:
		return false

	var source: Array = bottles_data[from_idx]
	var target: Array = bottles_data[to_idx]

	if source.is_empty():
		return false
	if target.size() >= capacity:
		return false

	var moving_color: int = int(source.back())

	if not target.is_empty() and int(target.back()) != moving_color:
		return false

	var run_count := _top_run_count(source)
	var free_space := capacity - target.size()
	var amount := min(run_count, free_space)

	if amount <= 0:
		return false

	for i in range(amount):
		target.append(source.pop_back())

	return true

func _top_run_count(stack: Array) -> int:
	if stack.is_empty():
		return 0

	var color := int(stack.back())
	var count := 0

	for i in range(stack.size() - 1, -1, -1):
		if int(stack[i]) == color:
			count += 1
		else:
			break

	return count

func _is_solved() -> bool:
	for stack in bottles_data:
		if stack.is_empty():
			continue

		if stack.size() != capacity:
			return false

		var c := int(stack[0])
		for v in stack:
			if int(v) != c:
				return false

	return true

func _update_status() -> void:
	if is_completed:
		status_label.text = "Уровень пройден!"
		return

	if selected_index == -1:
		status_label.text = "Выбери флакон"
	else:
		status_label.text = "Выбран флакон %d. Выбери, куда перелить." % selected_index

func _deep_copy_level(data: Array) -> Array:
	var result: Array = []
	for stack in data:
		result.append((stack as Array).duplicate())
	return result

func _make_color_map(data: Array) -> Dictionary:
	var ids: Array = []

	for stack in data:
		for v in stack:
			var id := int(v)
			if not ids.has(id):
				ids.append(id)

	ids.sort()

	var result: Dictionary = {}
	for i in range(ids.size()):
		var id: int = ids[i]

		if custom_colors.has(id):
			result[id] = custom_colors[id]
		elif i < FALLBACK_PALETTE.size():
			result[id] = FALLBACK_PALETTE[i]
		else:
			var hue := float(i) / max(1.0, float(ids.size()))
			result[id] = Color.from_hsv(hue, 0.70, 0.95)

	return result
