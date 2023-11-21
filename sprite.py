"""Defines the Sprite and MovingSprite class which enable images to be drawn and moved around the screen"""

from math import atan2
from PIL import Image, ImageTk

from config import GAME_GRID_WIDTH, GAME_GRID_START_X, GAME_GRID_START_Y, GRID_NUM_CELLS_WIDTH, GRID_NUM_CELLS_HEIGHT
from vector import Vec2, UP, DOWN, RIGHT, LEFT

class Rect:
	"""Simple class to represent a rectangle by the top, left and bottom, right co-ordinates"""
	def __init__(self, left, top, right, bottom):
		self.left = left
		self.top = top
		self.right = right
		self.bottom = bottom

class Sprite:
	"""Represents any drawn entity which doesn't move, for example the walls or pellets"""
	def __init__(self, canvas, pos, sprite_rects, scale=1):
		self.pos = pos

		self.canvas = canvas

		self.image = self.process_sprite_sheet(scale, *sprite_rects)[0]
		self.num_images = 1

		self.image_id = self.draw()

		self.w = self.image.width() # Assume image is square

	def process_sprite_sheet(self, scale, *bounding_boxes):
		"""Crops the main spritesheet according to the bounding boxes provided.
		Returns a list of the the resulting images"""

		base_image = Image.open("img/sprite_sheet.png")

		images = []
		for box in bounding_boxes:
			cropped = base_image.crop((box.left, box.top, box.right, box.bottom))
			w, _ = cropped.size
			cropped = cropped.resize((w * scale, w * scale))
			images.append(ImageTk.PhotoImage(cropped))

		return images

	def draw(self):
		centre = self.pos.scale(GAME_GRID_WIDTH).add(Vec2(GAME_GRID_WIDTH / 2 + GAME_GRID_START_X, GAME_GRID_WIDTH / 2 + GAME_GRID_START_Y))

		return self.canvas.create_image(centre.x, centre.y, image=self.image)

	def hide(self):
		self.canvas.delete(self.image_id)

class MovingSprite(Sprite):
	def __init__(self, canvas, pos, speed, frame_freq, sprite_rects, scale=1):
		super().__init__(canvas, pos, sprite_rects, scale)

		self.direction = RIGHT
		self.speed = speed
		self.frame_freq = frame_freq

		self.images = self.process_sprite_sheet(scale, *sprite_rects)
		self.num_images = len(self.images)
		self.image = self.images[0]

		self.image_id = self.draw()

		self.w = 10 # Allow sprite image to be outide of square

		self.alive = True

	def update_image(self, ticks, rotate=False):
		"""Update the sprite image depending on the number of game ticks and the frequency of image change"""
		if ticks % self.frame_freq == 0 or rotate:
			self.image = self.images[int((ticks / self.frame_freq) % self.num_images)]

			if rotate:
				rotated_image = ImageTk.getimage(self.image).rotate(atan2(-self.direction.y, self.direction.x) * 180/3.1415)
				self.image = ImageTk.PhotoImage(rotated_image)

			self.canvas.itemconfigure(self.image_id, image=self.image)

	def move(self, state=0):
		"""Move a MovingSprite based on its current speed.
		If 'state' is supplied, movement speed will be adjusted to reflect this"""
		adjusted_speed = self.speed

		# Adjust speed depending on state
		if state == 2:
			adjusted_speed *= 2/3
		elif state == 3:
			adjusted_speed *= 4

		move_offset = self.direction.scale(adjusted_speed)

		# Check if outside map bounds, and move to other side of map
		current_indices = screen_coords_to_world_indices(self.pos.add(move_offset).x, self.pos.add(move_offset).y)

		if current_indices.x < 0:
			current_indices.x = GRID_NUM_CELLS_WIDTH - 1
			self.pos = world_indices_to_screen_coords(current_indices.x, current_indices.y)
		elif current_indices.x >= GRID_NUM_CELLS_WIDTH:
			current_indices.x = 0
			self.pos = world_indices_to_screen_coords(current_indices.x, current_indices.y)

		if current_indices.y < 0:
			current_indices.y = GRID_NUM_CELLS_HEIGHT - 1
			self.pos = world_indices_to_screen_coords(current_indices.x, current_indices.y)
		elif current_indices.y >= GRID_NUM_CELLS_HEIGHT:
			current_indices.y = 0
			self.pos = world_indices_to_screen_coords(current_indices.x, current_indices.y)

		self.pos = self.pos.add(move_offset)

	def will_collide(self, world):
		"""Return True if the Sprite will collide with a wall in the next frame, False otherwise"""

		# Adjust for Tkinter setting x and y in the centre of the sprite
		top = self.pos.y - self.w/2
		bottom = self.pos.y + self.w/2
		left = self.pos.x - self.w/2
		right = self.pos.x + self.w/2

		# Adjust for the Sprite's movement next frame
		if   self.direction == UP:    top -= self.speed
		elif self.direction == DOWN:  bottom += self.speed
		elif self.direction == RIGHT: right += self.speed
		elif self.direction == LEFT:  left -= self.speed

		# Get the co-ordinates of each corner of the Sprite
		top_left = Vec2(left, top)
		bottom_left = Vec2(left, bottom)
		top_right = Vec2(right, top)
		bottom_right = Vec2(right, bottom)

		# Determine which points to check for collision, depending on movement direction
		if   self.direction.is_equal(UP):    collision_points = [top_left, top_right]
		elif self.direction.is_equal(DOWN):  collision_points = [bottom_left, bottom_right]
		elif self.direction.is_equal(RIGHT): collision_points = [top_right, bottom_right]
		elif self.direction.is_equal(LEFT):  collision_points = [top_left, bottom_left]

		# Get the indices of the cells which the Sprite will be in next frame
		cells = [screen_coords_to_world_indices(collision_points[0].x, collision_points[0].y),
		   		 screen_coords_to_world_indices(collision_points[1].x, collision_points[1].y)]

		# If the cells are outside the grid, don't check for collision
		# Only check one of the cells as, if one is out, they both will be
		if cells[0].x < 0 or cells[0].x >= GRID_NUM_CELLS_WIDTH or cells[0].y < 0 or cells[0].x >= GRID_NUM_CELLS_HEIGHT:
			return False

		# Otherwise, check if those cells are a wall
		return type(world[cells[0].y][cells[0].x]).__name__ == "Wall" or type(world[cells[1].y][cells[1].x]).__name__ == "Wall"

def screen_coords_to_world_indices(x, y):
	"""Returns the indices into the 2D list of sprites which corresponds to the screen co-ordinates (x, y)"""

	i = int((x - GAME_GRID_START_X) // GAME_GRID_WIDTH)
	j = int((y - GAME_GRID_START_Y) // GAME_GRID_WIDTH)
	return Vec2(i, j)

def world_indices_to_screen_coords(i, j):
	"""Returns the screen co-ordinates (x, y) which correspond to indices into the 2D list of sprites"""

	x = (i + 0.5) * GAME_GRID_WIDTH + GAME_GRID_START_X
	y = (j + 0.5) * GAME_GRID_WIDTH + GAME_GRID_START_Y
	return Vec2(x, y)
