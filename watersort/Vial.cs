using Godot;
using System;
using System.Linq;
using Godot.Collections;

public partial class Vial : Node2D
{
	 public Array<int> Segments;
	 public Array<Color> Colors;

	 public const uint Capacity = 4;
	 
	 
	 public int LastSegment()
	 {
		 return Segments.Count == 0 ? 0 : Segments[-1];
	 }

	 public bool AddSegment(int segment)
	 {
		 bool added;
		 if (Segments.Count == 0)
		 {
			 added = true;
		 }
		 else if (Segments.Count >= Capacity)
		 {
			 added = false;
		 }
		 else if (Segments[-1] == segment)
		 {
			 added = true;
		 }
		 else
		 {
			 added = false;
		 }

		 if (added)
		 {
			 Segments.Add(segment);
		 }

		 return added;
	 }

	 public int RemoveSegment()
	 {
		 if (Segments.Count == 0)
		 {
			 return 0;
		 }

		 var segment = Segments[-1];
		 Segments.RemoveAt(-1);
		 
		 return segment;
	 }

	 public override void _Draw()
	 {  
		 GD.Print("VIAL DRAW");
		 
		 for (var i = 0; i < Segments.Count; i++)
		 {
			 var segmentName = "Segment" + (i + 1);
			 
			 if (FindChild(segmentName) is not Sprite2D nodeSegment)
			 {
				 throw new Exception("Segment not found: " + segmentName);
			 }
			 
			 nodeSegment.SetInstanceShaderParameter( "color", Colors[Segments[i]]);
			 nodeSegment.SetInstanceShaderParameter("filled", 1);
		 }
		 
		 for (var i = Segments.Count; i < Capacity; i++)
		 {
			 var segmentName = "Segment" + (i + 1);
			 
			 if (FindChild(segmentName) is not Sprite2D nodeSegment)
			 {
				 throw new Exception("Segment not found: " + segmentName);
			 }
			 
			 nodeSegment.SetInstanceShaderParameter( "color", Colors[0]);
			 nodeSegment.SetInstanceShaderParameter("filled", 0);
		 }
	 }
	 
}
