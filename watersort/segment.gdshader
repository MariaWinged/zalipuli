shader_type canvas_item;

instance uniform vec4 color : source_color = vec4(0.0, 0.0, 0.0, 0.0);
instance uniform int filled : hint_enum("No", "Yes")  = 0;
uniform sampler2D sparkles_texture;
uniform int hframes = 9;
uniform int vframes = 9;
uniform float fps = 18.0;
instance uniform int shift : hint_range(0, 81) = 0;

void fragment() {
	int total_frames = hframes * vframes;
    int frame = int(floor(TIME * fps) + float(shift)) % total_frames;
	
	int fx = frame % hframes;
	int fy = frame / hframes;
	vec2 frame_size = vec2(1.0 / float(hframes), 1.0 / float(vframes));
	vec2 sparkles_uv = UV * frame_size;
    sparkles_uv += vec2(float(fx), float(fy)) * frame_size;
	vec4 sparkles = texture(sparkles_texture, sparkles_uv);
	COLOR = mix(color.rgba, sparkles.rgba, sparkles.a);
	
	if (filled > 0) {
		COLOR.a = texture(TEXTURE, UV).a;
	} else {
		COLOR.a = 0.0;
	}
}