"""Allows saving and loading of games to/from JSON files"""

from json import dump, load as json_load
from os import path, makedirs

from world_components import Wall, Pellet, PowerPellet, Fruit

class Save:
	"""Stores all necessary information to save all aspects of a game"""
	def __init__(self, level,
				 pacman_pos, pacman_dir, pacman_lives,
				 ghosts, world, score):

		self.level = level

		self.pacman_pos = pacman_pos
		self.pacman_dir = pacman_dir
		self.pacman_lives = pacman_lives

		self.ghosts = ghosts
		self.world = world
		self.score = score

def save(save_name, level, pacman, lives, ghosts, world, score):
	"""Save the current gamestate in a local JSON file"""

	if not path.exists("saves"): makedirs("saves")

	json_ghosts = []
	for g in ghosts:
		json_ghosts.append(g.to_save())

	json_world = []
	for row in world:
		this_row = []
		for cell in row:
			if isinstance(cell, Wall):
				this_row.append(["W"])
			elif isinstance(cell, Pellet):
				this_row.append(["P", cell.eaten])
			elif isinstance(cell, PowerPellet):
				this_row.append(["U", cell.eaten])
			elif isinstance(cell, Fruit):
				this_row.append(["F", cell.fruit_type, cell.timer])
			else:
				this_row.append(("X"))

		json_world.append(this_row)


	new_save = Save(level, pacman.pos, pacman.direction, lives, json_ghosts, json_world, score)

	with open("saves/" + save_name + ".json", "w") as save_file:
		dump(new_save, save_file, default = lambda attr: attr.__dict__, indent=2)

def load(save_object, save_name):
	"""Load a JSON file to start a game from where it left off.
	Stores the fetched and decoded data in 'save_object'"""

	# Check if the save file exists
	if not path.exists("saves/" + save_name + ".json"):
		return

	with open("saves/" + save_name + ".json", "r") as save_file:
		save_json = json_load(save_file)

	loaded_save = Save(**save_json)

	# Avoid reassigning 'save_object' so the data can be accessed back in the main game
	save_object.level = loaded_save.level
	save_object.pacman_pos = loaded_save.pacman_pos
	save_object.pacman_dir = loaded_save.pacman_dir
	save_object.pacman_lives = loaded_save.pacman_lives
	save_object.ghosts = loaded_save.ghosts
	save_object.world = loaded_save.world
	save_object.score = loaded_save.score
