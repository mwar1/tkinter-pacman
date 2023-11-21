"""Basic 2-D vector math"""

class Vec2:
	"""Basic 2-dimensional vector"""
	def __init__(self, x, y):
		self.x = x
		self.y = y

	def scale(self, k):
		"Scale the vector by a scale factor, k"
		new = Vec2(self.x * k, self.y * k)

		return new

	def add(self, vec):
		"Add two vectors together"
		new = Vec2(self.x + vec.x, self.y + vec.y)

		return new

	def is_equal(self, vec):
		"Returns True if 'vec' has the same x and y values as self"
		return self.x == vec.x and self.y == vec.y

# Define standard vectors
UP    = Vec2(0, -1)
DOWN  = Vec2(0, 1)
LEFT  = Vec2(-1, 0)
RIGHT = Vec2(1, 0)
