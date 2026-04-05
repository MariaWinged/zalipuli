using Godot;
using System;
using Godot.Collections;
using Array = System.Array;

public partial class Level : Node2D
{

	public Color[] Colors =
	[
		new Color(1, 0, 0),
		new Color(0, 1, 0),
		new Color(0, 0, 1),
		new Color(1, 1, 0),
		new Color(0, 1, 1),
		new Color(1, 0, 1),
		new Color(1, 1, 1),
		new Color(0, 0, 0),
		new Color(0.23f, 0.23f, 0.23f),
		new Color(0.553f, 0.553f, 0.553f),
		new Color(0.7255f, 0.502f, 0.8196f),
		new Color(0.882f, 0.449f, 0.146f),
		new Color(0.348f, 0.137f, 0.003f),
		new Color(0.38f, 0.598f, 0.706f),
		new Color(1, 0.598f, 0.669f),
	];
	
	int[][] Vials = [[1, 2, 3, 4], [5, 1, 2, 3], [4, 5, 1, 2], [3, 4, 5, 1], [1, 2, 3, 4], [], []];
	uint Steps = 0;
	uint MinSteps = 20;
	Array<Color> colors;

	public override void _Ready()
	{
		var randomColors = Colors.Clone() as Color[];
		Random.Shared.Shuffle(randomColors);
		var colorsCount = Vials.Length - 2;
		colors = [new Color(0, 0, 0, 0)];
		int i;
		for (i = 0; i < colorsCount; i++)
		{
			colors.Add(randomColors[i]);
		}
		

		var line13 = Vials.Length / 3 + (Vials.Length % 3 == 2 ? 1 : 0);
		var line2 = Vials.Length / 3 + (Vials.Length % 3 == 1 ? 1 : 0);

		var y1 = 850;
		var y2 = 1500;
		var y3 = 2150;
		var width = 1500.0;
		i = 0;

		for (var xi = 1; xi <= line13; xi++)
		{
			var x = Mathf.RoundToInt(width / (line13 + 1) * xi);
			AddVial(Vials[i++], new Vector2(x, y1), "Vial" + i);
			AddVial(Vials[i++], new Vector2(x, y3), "Vial" + i);
		}

		for (var xi = 1; xi <= line2; xi++)
		{
			var x = Mathf.RoundToInt(width / (line2 + 1) * xi);
			AddVial(Vials[i++], new Vector2(x, y2), "Vial" + i);
		}
		
		Scale = new Vector2(0.5f, 0.5f);
	}

	private void AddVial(int[] segments, Vector2 position, string name)
	{
		var vialScene = GD.Load<PackedScene>("res://vial.tscn");
		if (vialScene.Instantiate() is not Vial vial)
		{
			throw new Exception("Vial is null");
		}
		
		vial.Name = name;
		vial.Segments = [];
		foreach (var segment in segments)
		{
			vial.Segments.Add(segment);
		}
		vial.Colors = colors;
		vial.Position = position;
		
		AddChild(vial);
	}
	
	public void AddStep()
	{
		Steps++;
	}
	
}
