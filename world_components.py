"""Defines the different parts of the pacman game and world"""

from math import inf, ceil
from enum import Enum
from random import choice

from sprite import Sprite, MovingSprite, Rect, screen_coords_to_world_indices as screen2indices, world_indices_to_screen_coords as world2screen
from config import GAME_GRID_START_X, GAME_GRID_START_Y, GAME_GRID_WIDTH, GRID_NUM_CELLS_WIDTH
from vector import Vec2, UP, DOWN, LEFT, RIGHT

class Wall(Sprite):
	"""Represents a wall in the game.
	x and y co-ordinates are relative to the grid used in the game, not the screen"""
	def __init__(self, canvas, pos, scale=1):
		super().__init__(canvas, pos, [Rect(60, 0, 76, 16)], scale)

class Pellet(Sprite):
	"""Represents a single pellet in the world which pacman can eat.
	x and y co-ordinates are relative to the grid used in the game, not the screen"""
	def __init__(self, canvas, pos, image=Rect(80, 0, 100, 20), scale=1):
		super().__init__(canvas, pos, [image], scale)

		self.eaten = False

class Fruit(Pellet):
	"""Represents the bonus 'fruits' that spawn into the game for extra points"""
	def __init__(self, canvas, fruit_type, scale=1):
		self.fruit_type = fruit_type

		if self.fruit_type == "cherry":
			image = Rect(60, 60, 80, 80)
			self.score_bonus = 100
		elif self.fruit_type == "banana":
			image = Rect(80, 60, 100, 80)
			self.score_bonus = 200
		elif self.fruit_type == "strawberry":
			image = Rect(100, 60, 120, 80)
			self.score_bonus = 400
		elif self.fruit_type == "apple":
			image = Rect(60, 80, 80, 100)
			self.score_bonus = 750
		elif self.fruit_type == "key":
			image = Rect(80, 80, 100, 100)
			self.score_bonus = 1000

		super().__init__(canvas, Vec2(10, 15), image, scale)
		self.hide()

class PowerPellet(Pellet):
	"""Represents the glowing power pellets in the four corners"""
	def __init__(self, canvas, pos, scale=1):
		super().__init__(canvas, pos, Rect(100, 0, 120, 20), scale)

def num_pellets_eaten(world):
	eaten = 0

	for row in world:
		for cell in row:
			if isinstance(cell, Pellet) and not isinstance(cell, PowerPellet) and cell.eaten:
				eaten += 1

	return eaten

def generate_level(canvas, grid_path):
	"""Returns a 2D list of sprites to represent the world, based on the input text file, empty tiles are represented with -1"""

	sprites = []
	with open(grid_path, "r") as grid:
		for i, line in enumerate(grid.readlines()):
			tiles = line.split(" ")
			this_row = []
			for j, tile in enumerate(tiles):
				if tile[0] == "W":
					this_row.append(Wall(canvas, Vec2(j, i), scale=2))
				elif tile[0] == "P":
					this_row.append(Pellet(canvas, Vec2(j, i)))
				elif tile[0] == "U":
					this_row.append(PowerPellet(canvas, Vec2(j, i)))
				else:
					this_row.append(-1)
			sprites.append(this_row)

	return sprites

class GhostState(Enum):
	PEN = 0
	NORMAL = 1
	PANIC = 2
	DEAD = 3

class Ghost(MovingSprite):
	"""Represents one of the ghosts, with a custom 'pathing_function' to calculate where the ghost will move"""
	def __init__(self, canvas, pos, speed, frame_freq, sprite_rects, ghost_type, scale=1):
		super().__init__(canvas, pos, speed, frame_freq, sprite_rects, scale)

		if ghost_type == "blinky":
			self.pathing_function = self.blinky_path
		elif ghost_type == "pinky":
			self.pathing_function = self.pinky_path
		elif ghost_type == "inky":
			self.pathing_function = self.inky_path
		elif ghost_type == "clyde":
			self.pathing_function = self.clyde_path

		self.next_square = screen2indices(self.pos.x, self.pos.y)
		self.at_centre = True

		self.panic_images = self.process_sprite_sheet(scale, Rect(60, 40, 80, 60), Rect(80, 40, 100, 60), Rect(100, 40, 120, 60))
		self.dead_images = self.process_sprite_sheet(scale, Rect(60, 20, 80, 40), Rect(80, 20, 100, 40), Rect(100, 20, 120, 40))
		self.num_panic_images = len(self.panic_images)
		self.num_dead_images = len(self.dead_images)

		self.panic_timer = -1

		self.state = GhostState.PEN
		self.direction = RIGHT

	def to_save(self):
		return [self.pos, self.direction, self.next_square, self.state.value, self.panic_timer]

	def update(self, world, ghost_coords, pacman_coords, pacman_dir, blinky_pos):
		"""Re-evaluate next moves based on pacman's position and current state, and move based on this"""

		current_indices = screen2indices(ghost_coords.x, ghost_coords.y)

		# Only re-evaulate pathing if the Ghost has moved into a new square
		if current_indices.is_equal(self.next_square) and self.at_centre:
			# Allow entrance to the starting pen if ghost is dead
			if self.state == GhostState.DEAD:
				possibles = get_neighbours(world, ghost_coords, starting_pen=True)
			else:
				possibles = get_neighbours(world, ghost_coords)
			possibles_no_reverse = self.remove_reverse_moves(current_indices, possibles)


			# Only make a decision if the Ghost is at a junction, i.e. there are more than two possible squares to move into
			if len(possibles) > 2:
				pacman_indices = screen2indices(pacman_coords.x, pacman_coords.y)
				if self.state == GhostState.NORMAL:
					# Use pathing function if in normal state
					self.next_square = self.pathing_function(possibles_no_reverse, pacman_indices, pacman_dir, blinky_pos)
				elif self.state == GhostState.PANIC:
					# Take a random path if in panic mode
					self.next_square = get_next_step(possibles, choice(possibles_no_reverse))
				elif self.state == GhostState.DEAD:
					# Return to normal state if back in the pen
					if current_indices.is_equal(Vec2(10, 12)):
						self.state = GhostState.NORMAL
						self.next_square = Vec2(10, 10)
					else:
						# Otherwise move back towards the pen
						self.next_square = get_next_step(possibles_no_reverse, Vec2(10, 12))
				elif self.state == GhostState.PEN:
					self.next_square = choice([
						Vec2(9, 12),
						Vec2(10, 12),
						Vec2(11, 12),
						Vec2(9, 13),
						Vec2(10, 13),
						Vec2(11, 13)
					])
			elif len(possibles) == 2:
				# If not at a junction, choose the next square such that the Ghost does not reverse direction
				# If there are only two possible squares to move into, only one of these will not reverse the direction, so choose index 0

				self.next_square = possibles_no_reverse[0]
			else:
				# If there's only one possibility, the Ghost is about to go off the map, so teleport to the other side
				self.pos = world2screen(possibles[0].x, possibles[0].y)

				# Set next target so the Ghost doesn't teleport back immediately
				next_square = self.pos.add(self.direction.scale(GAME_GRID_WIDTH))
				self.next_square = screen2indices(next_square.x, next_square.y)

		target_centre = Vec2((self.next_square.x * GAME_GRID_WIDTH) + GAME_GRID_START_X + GAME_GRID_WIDTH / 2, (self.next_square.y * GAME_GRID_WIDTH) + GAME_GRID_START_Y + GAME_GRID_WIDTH / 2)

		# Check if the Ghost is close enough to the centre of its target
		speed_modifier = 1
		if self.state == GhostState.DEAD:
			speed_modifier = 4
		centre_x = abs(target_centre.x - self.pos.x) <= ceil(self.speed * speed_modifier / 2)
		centre_y = abs(target_centre.y - self.pos.y) <= ceil(self.speed * speed_modifier / 2)
		self.at_centre = centre_x and centre_y

		# Move toward the centre of the target
		if not centre_x:
			if target_centre.x > self.pos.x:
				self.direction = RIGHT
			elif target_centre.x < self.pos.x:
				self.direction = LEFT
			self.move(self.state.value)

		if not centre_y:
			if target_centre.y > self.pos.y:
				self.direction = DOWN
			elif target_centre.y < self.pos.y:
				self.direction = UP
			self.move(self.state.value)

		# If in panic mode, reduce panic timer and check if panic is over
		if self.state == GhostState.PANIC:
			self.panic_timer -= 1

			if self.panic_timer == 0:
				if not self.is_in_pen():
					self.state = GhostState.NORMAL
				else:
					self.state = GhostState.PEN

	def remove_reverse_moves(self, pos, possibles):
		"Return a list of possible next squares to move into which don't require direction to be reversed"
		updated_moves = []

		past_square = pos.add(self.direction.scale(-1))
		for p in possibles:
			if not p.is_equal(past_square): updated_moves.append(p)

		return updated_moves

	def is_in_pen(self):
		"""Returns True if the Ghost is in the starting pen, False otherwise"""
		pos_indices = screen2indices(self.pos.x, self.pos.y)
		for square in [Vec2(9, 12), Vec2(10, 12), Vec2(11, 12), Vec2(9, 13), Vec2(10, 13), Vec2(11, 13)]:
			if pos_indices.is_equal(square):
				return True
		return False

	def update_image(self, ticks):
		"""Update the sprite image depending on the number of game ticks and the frequency of image change"""
		if ticks % self.frame_freq == 0:
			if self.state == GhostState.PANIC:
				self.image = self.panic_images[int((ticks / self.frame_freq) % self.num_panic_images)]
			elif self.state == GhostState.DEAD:
				self.image = self.dead_images[int((ticks / self.frame_freq) % self.num_dead_images)]
			else:
				self.image = self.images[int((ticks / self.frame_freq) % self.num_images)]

			self.canvas.itemconfigure(self.image_id, image=self.image)

	# Ghost pathing functions
	# Each returns the next square the ghost should move towards based on its respective AI

	## Blinky (red)
	def blinky_path(self, possibles, pacman_coords, _2, _3):
		"""Chase pacman directly"""
		
		# Choose the square which is closest to pacman
		next_square = get_next_step(possibles, pacman_coords)

		return next_square

	## Pinky (pink)
	def pinky_path(self, possibles, pacman_coords, pacman_direction, blinky_coords):
		"""Chase inky's target square + 2 * the vector from blinky to pacman"""

		blinky_indices = screen2indices(blinky_coords.x, blinky_coords.y)

		blinky_to_pacman = pacman_coords.add(blinky_indices.scale(-1)) # pacman_coords - blinky_coords
		inky_target = pacman_coords.add(pacman_direction.scale(4))
		pinky_target = inky_target.add(blinky_to_pacman.scale(2))

		next_square = get_next_step(possibles, pinky_target)

		return next_square

	## Inky (cyan)
	def inky_path(self, possibles, pacman_coords, pacman_direction, _3):
		"""Chase the square 4 squares infront of pacman"""

		inky_target = pacman_coords.add(pacman_direction.scale(4))

		next_square = get_next_step(possibles, inky_target)

		return next_square

	## Clyde (orange)
	def clyde_path(self, possibles, pacman_coords, _2, _3):
		"""Chase blinky's target square, unless too close to pacman, in which case run away"""

		clyde_indices = screen2indices(self.pos.x, self.pos.y)

		target = pacman_coords
		if distance(pacman_coords, clyde_indices) <= 8:
			target = Vec2(0, 29)

		next_square = get_next_step(possibles, target)

		return next_square

def get_next_step(possibles, target):
	"""Given a target square, return the next possible square to move into which is closest to the target"""

	min_distance = inf

	for p in possibles:
		p_distance = distance(p, target)
		if p_distance < min_distance:
			min_distance = p_distance
			next_square = p

	return next_square

def get_neighbours(world, current, starting_pen=False):
	"""Returns a list of cells which can be moved into.
	If 'starting_pen' is True, the wall top centre wall in the pen will be ignored to allow access/exit"""

	possibles = []
	grid_indices = screen2indices(current.x, current.y)

	x, y = grid_indices.x, grid_indices.y

	# Check if its possible to go off the side of the map
	if x - 1 == -1:
		possibles.append(Vec2(GRID_NUM_CELLS_WIDTH-1, y))
		return possibles

	if x + 1 == GRID_NUM_CELLS_WIDTH:
		possibles.append(Vec2(0, y))
		return possibles

	# Check the adjacent squares are in the bounds of the world, and not a wall
	if y + 1 < len(world) and (not isinstance(world[y + 1][x], Wall) or (starting_pen and Vec2(x, y+1).is_equal(Vec2(10, 11)))):
		possibles.append(Vec2(x, y+1))
	if x + 1 < len(world[0]) and not isinstance(world[y][x + 1], Wall):
		possibles.append(Vec2(x+1, y))
	if y - 1 >= 0 and not isinstance(world[y - 1][x], Wall):
		possibles.append(Vec2(x, y-1))
	if x - 1 >= 0 and not isinstance(world[y][x - 1], Wall):
		possibles.append(Vec2(x-1, y))

	return possibles

def distance(current, target):
	"""Returns the Euclidian distance between current and target.
	'current' and 'target' are tuples of co-ordinates, (x, y)"""

	a = abs(current.x - target.x)
	b = abs(current.y - target.y)

	c = ((a ** 2) + (b ** 2)) ** 0.5
	return c

def check_ghost_collisions(pacman, ghosts):
	"""Returns the index of any ghosts which have collided with pacman"""

	ids = []
	for i, ghost in enumerate(ghosts):
		if screen2indices(ghost.pos.x, ghost.pos.y).is_equal(screen2indices(pacman.pos.x, pacman.pos.y)):
			ids.append(i+1)

	return ids
