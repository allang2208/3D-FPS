extends RefCounted
## CSS cubic-bezier: solve time on x, then evaluate progress on y.
static func bezier(t: float, x1: float, y1: float, x2: float, y2: float) -> float:
	var low := 0.0
	var high := 1.0
	for i in 18:
		var midpoint := (low + high) * 0.5
		var x := 3 * (1-midpoint) * (1-midpoint) * midpoint * x1 + 3 * (1-midpoint) * midpoint * midpoint * x2 + midpoint*midpoint*midpoint
		if x < t:
			low = midpoint
		else:
			high = midpoint
	var u := (low + high) * 0.5
	return 3 * (1-u) * (1-u) * u * y1 + 3 * (1-u) * u * u * y2 + u*u*u

static func standard(t: float) -> float:
	return bezier(t, 0.4, 0.0, 0.2, 1.0)

static func ease(t: float) -> float:
	return bezier(t, 0.25, 0.1, 0.25, 1.0)
