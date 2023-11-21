# Screen resolution: 1600x900

from tkinter import Tk, Canvas, StringVar
from tkinter.font import Font, families
from PIL import Image, ImageTk

from config import S_HEIGHT, S_WIDTH, FPS
from sprite import Rect, Sprite, MovingSprite, world_indices_to_screen_coords as world2screen, screen_coords_to_world_indices as screen2world
from world_components import Ghost, GhostState, Pellet, PowerPellet, Fruit, generate_level, num_pellets_eaten, check_ghost_collisions
from vector import Vec2, UP, DOWN, RIGHT, LEFT
from widget import CanvasButton, CanvasEntry
from progress import save, load, Save


def create_window(w, h):
	window = Tk()
	window.title("Pacman")

	window_width = window.winfo_screenwidth()
	window_height = window.winfo_screenheight()
	window_x = window_width / 2 - w / 2
	window_y = window_height / 2 - h / 2
	window.geometry("%dx%d+%d+%d" % (w, h, window_x, window_y))

	return window

def direction_up(event):
	if not paused:
		pacman.direction = UP

def direction_down(event):
	if not paused:
		pacman.direction = DOWN

def direction_left(event):
	if not paused:
		pacman.direction = LEFT

def direction_right(event):
	if not paused:
		pacman.direction = RIGHT

def toggle_pause(event):
	global paused

	# Don't allow pausing during game setup / countdown
	if playing:
		if paused:
			game_screen_canvas.coords(save_button.button_id, (-100, -100))
			game_screen_canvas.delete(text["paused"])
		else:
			game_screen_canvas.coords(save_button.button_id, (S_WIDTH/2, 650))
			text["paused"] = game_screen_canvas.create_text(S_WIDTH / 2, S_HEIGHT / 2, width=1400, font=big_font, fill="yellow", text="PAUSED")

		paused = not paused

def start_ghost_panic():
	global ghosts_eaten

	for i in range(1, 5):
		if moving_sprites[i].state != GhostState.DEAD:
			moving_sprites[i].state = GhostState.PANIC
			moving_sprites[i].panic_timer = panic_time * FPS

	ghosts_eaten = 0

def reset_game(new_game=False, increase_level=False, death=False, loaded=False):
	global ticks, pacman, speed, ticks, current_level, panic_time, score, pacman_lives, playing, paused, gained_extra_life, world

	playing = paused = False
	ticks = 0
	save_name_entry.clear_text()

	if increase_level:
		current_level += 1
		speed += 0.5
		panic_time -= 1

	if new_game or increase_level:
		world = generate_level(game_screen_canvas, "grid.txt")

	if loaded or new_game:
		game_screen_canvas.coords(save_button.button_id, (-100, -100))
		try:
			game_screen_canvas.delete(text["paused"])
		except KeyError:
			pass

	if loaded:
		speed = 3 + 0.5 * current_level
		panic_time = 10 - current_level

		if score >= 10000:
			gained_extra_life = True

	if new_game:
		speed = 3
		panic_time = 10

		score = 0
		pacman_lives = 3
		current_level = 0

	if not death and not loaded:
		for row in world:
			for cell in row:
				if isinstance(cell, Pellet) or isinstance(cell, PowerPellet) or isinstance(cell, Fruit):
					cell.eaten = False

		world[15][10] = -1

	if not loaded:
		for sprite in moving_sprites:
			sprite.hide()

		moving_sprites[0:5] = [MovingSprite(game_screen_canvas, p_start, speed, 5,
							[Rect(0, 0, 20, 20),
							Rect(20, 0, 40, 20),
							Rect(40, 0, 60, 20)], scale=2),
		Ghost(game_screen_canvas, ghost_start[0], speed, 5, [Rect(0, 20, 20, 40),
										Rect(20, 20, 40, 40),
										Rect(40, 20, 60, 40)], "blinky", scale=2),
		Ghost(game_screen_canvas, ghost_start[1], speed, 5, [Rect(0, 40, 20, 60),
										Rect(20, 40, 40, 60),
										Rect(40, 40, 60, 60)], "inky", scale=2),
		Ghost(game_screen_canvas, ghost_start[2], speed, 5, [Rect(0, 60, 20, 80),
										Rect(20, 60, 40, 80),
										Rect(40, 60, 60, 80)], "pinky", scale=2),
		Ghost(game_screen_canvas, ghost_start[3], speed, 5, [Rect(0, 80, 20, 100),
										Rect(20, 80, 40, 100),
										Rect(40, 80, 60, 100)], "clyde", scale=2)]
		pacman = moving_sprites[0]


	pacman.alive = True

	switch_screens(main_screen_canvas, game_screen_canvas)
	start_game(loaded=loaded)


def start_game(loaded=False):
	global ticks, playing

	try:
		game_screen_canvas.delete(text["count"])
	except KeyError:
		pass

	ticks += 1
	if ticks < 3 * FPS:
		# Perform countdown
		text["count"] = game_screen_canvas.create_text(S_WIDTH / 2, S_HEIGHT / 2, width=500, font=big_font, fill="yellow", text=str(3 - (ticks // FPS)))

		game_screen_canvas.pack()

		window.after(int(1000 / FPS), lambda: start_game(loaded))
	else:
		if not loaded:
			# Start the game, release Blinky
			moving_sprites[1].state = GhostState.NORMAL

			moving_sprites[1].next_square = Vec2(10, 10)

		playing = True

		game_loop()

def game_loop():
	global ticks, score, ghosts_eaten, last_pellets_eaten, pacman_lives, playing, gained_extra_life

	if not paused:
		ticks += 1

		# Update the score text
		game_screen_canvas.delete(text["score"])
		text["score"] = game_screen_canvas.create_text(5, 0, width=500, font=score_font, fill="yellow", text="Score: " + str(score), anchor="nw")

		if not pacman.alive:
			if pacman_lives == 0:
				playing = False
				add_score_canvas.delete(text["score_screen_score"])
				text["score_screen_score"] = add_score_canvas.create_text(S_WIDTH/2, 100, width=1500, font=title_font, fill="yellow", text="You scored: " + str(score))
				switch_screens(game_screen_canvas, add_score_canvas)
			else:
				reset_game(death=True)

		for s in moving_sprites:
			if isinstance(s, Ghost):
				s.update_image(ticks)
				s.update(world, s.pos, pacman.pos, pacman.direction, moving_sprites[1].pos)
			else:
				s.update_image(ticks, rotate=True)

		fruit_square = world[15][10]
		if isinstance(fruit_square, Fruit):
			fruit_square.timer -= 1
			if fruit_square.timer == 0:
				world[15][10].hide()
				world[15][10] = -1

		if not pacman.will_collide(world):
			pacman.move()

			pacman_pos = screen2world(pacman.pos.x, pacman.pos.y)

			# Check if a pellet or fruit has been eaten, and update score
			this_square = world[pacman_pos.y][pacman_pos.x]
			if isinstance(this_square, PowerPellet) and not this_square.eaten:
				# Start Ghost panic

				score += 50
				this_square.eaten = True
				this_square.hide()

				start_ghost_panic()
			elif isinstance(this_square, Fruit) and not this_square.eaten:
				score += this_square.score_bonus

				world[15][10].hide()
				world[15][10] = -1
			elif isinstance(this_square, Pellet) and not this_square.eaten:
				this_square.eaten = True
				score += 10

				this_square.hide()

			# Check if its time to release another ghost, or add fruit to the world
			pellets_eaten = num_pellets_eaten(world)
			if pellets_eaten != last_pellets_eaten:
				if pellets_eaten >= 1 and moving_sprites[2].state == GhostState.PEN:
					# Release Pinky
					moving_sprites[2].state = GhostState.NORMAL
					moving_sprites[2].next_square = Vec2(10, 10)
				elif pellets_eaten >= 30 and moving_sprites[3].state == GhostState.PEN:
					# Release Inky
					moving_sprites[3].state = GhostState.NORMAL
					moving_sprites[3].next_square = Vec2(10, 10)
				elif pellets_eaten >= 63 and moving_sprites[4].state == GhostState.PEN:
					# Release Clyde
					moving_sprites[4].state = GhostState.NORMAL
					moving_sprites[4].next_square = Vec2(10, 10)
				elif pellets_eaten == 70:
					world[15][10] = fruits[current_level % 5]
					world[15][10].image_id = world[15][10].draw()
					world[15][10].timer = 10 * FPS
				elif pellets_eaten == 170 and world[15][10] == -1:
					world[15][10] = fruits[current_level % 5]
					world[15][10].image_id = world[15][10].draw()
					world[15][10].timer = 10 * FPS
				elif pellets_eaten == 189:
					# All pellets eaten, so start new level
					reset_game(increase_level=True)

				last_pellets_eaten = pellets_eaten

		# Actually move the sprites
		for sprite in moving_sprites:
			game_screen_canvas.coords(sprite.image_id, sprite.pos.x, sprite.pos.y)

		# Check if player has gained bonus life
		if score >= 10000 and not gained_extra_life:
			pacman_lives += 1
			life_sprites[pacman_lives-1].image_id = life_sprites[pacman_lives-1].draw()
			gained_extra_life = True

		# Check if pacman has collided with any ghosts
		ghost_collisions = check_ghost_collisions(pacman, moving_sprites[1:5])
		if len(ghost_collisions) > 0:
			for ghost_id in ghost_collisions:
				if moving_sprites[ghost_id].state == GhostState.NORMAL and pacman.alive:
					pacman_lives -= 1
					pacman.alive = False
					life_sprites[pacman_lives].hide()
				elif moving_sprites[ghost_id].state == GhostState.PANIC:
					moving_sprites[ghost_id].state = GhostState.DEAD
					score += (2 ** ghosts_eaten) * 200 # 200, 400, 800, 1600 for eating ghosts
					ghosts_eaten += 1

	if playing:
		game_screen_canvas.pack()

		window.after(int(1000 / FPS), game_loop)

def add_score(name, score):
	"""Writes 'score' to a text file containing all past scores"""

	# Don't allow empty names
	if len(name.strip()) == 0:
		return
	with open("scores.txt", "a") as score_file:
		score_file.write(name + "," + str(score) + "\n")

	score_entry.clear_text()
	switch_screens(add_score_canvas, main_screen_canvas)

def read_high_scores():
	"""Read the scores file and find the 5 highest scores"""

	scores = []
	with open("scores.txt", "r") as score_file:
		for line in score_file.readlines():
			name, score = line.split(",")
			scores.append([name, int(score)])

	scores.sort(reverse=True, key=lambda x: x[1])
	scores = scores[:5]

	for i, s in enumerate(scores):
		try:
			scores_screen_canvas.delete(text["score"+str(i)])
		except KeyError:
			pass

		text["score"+str(i)] = scores_screen_canvas.create_text(S_WIDTH/2, i*100+400, width=500, font=medium_font, fill="yellow", text=s[0] + "  -  " + str(s[1]))

	switch_screens(main_screen_canvas, scores_screen_canvas)

window = create_window(S_WIDTH, S_HEIGHT)

game_screen_canvas = Canvas(window, bg="black", width=S_WIDTH, height=S_HEIGHT)
main_screen_canvas = Canvas(window, bg="black", width=S_WIDTH, height=S_HEIGHT)
scores_screen_canvas = Canvas(window, bg="black", width=S_WIDTH, height=S_HEIGHT)
add_score_canvas = Canvas(window, bg="black", width=S_WIDTH, height=S_HEIGHT)
settings_screen_canvas = Canvas(window, bg="black", width=S_WIDTH, height=S_HEIGHT)
boss_screen_canvas = Canvas(window, width=S_WIDTH, height=S_HEIGHT)
save_game_canvas = Canvas(window, bg="black", width=S_WIDTH, height=S_HEIGHT)
load_game_canvas = Canvas(window, bg="black", width=S_WIDTH, height=S_HEIGHT)

# Keybindings
keybindings = {
	"up": "w",
	"left": "a",
	"down": "s",
	"right": "d",
	"pause": "p",
	"boss": "b"
}

def switch_screens(old, new):
	"""Switch between two canvases"""
	old.pack_forget()
	game_screen_canvas.pack_forget()

	new.pack()
	new.focus_force()

def bind_keybindings():
	"""Binds each keybinding to its respective movement"""

	game_screen_canvas.bind("<" + keybindings["up"] + ">", direction_up)
	game_screen_canvas.bind("<" + keybindings["left"] + ">", direction_left)
	game_screen_canvas.bind("<" + keybindings["down"] + ">", direction_down)
	game_screen_canvas.bind("<" + keybindings["right"] + ">", direction_right)
	game_screen_canvas.bind("<" + keybindings["pause"] + ">", toggle_pause)
	game_screen_canvas.bind("<" + keybindings["boss"] + ">", start_boss_screen)

	boss_screen_canvas.bind(keybindings["boss"], lambda _: switch_screens(boss_screen_canvas, game_screen_canvas))

	for l in "abcdefghijklmnopqrstuvwxyz":
		game_screen_canvas.bind(l, check_cheat_code, add="+")

def unbind_keybindings():
	"""Unbinds all keybindings"""

	game_screen_canvas.unbind(keybindings["up"])
	game_screen_canvas.unbind(keybindings["left"])
	game_screen_canvas.unbind(keybindings["down"])
	game_screen_canvas.unbind(keybindings["right"])
	game_screen_canvas.unbind(keybindings["pause"])
	game_screen_canvas.unbind(keybindings["boss"])

	boss_screen_canvas.unbind(keybindings["boss"])

def get_keypress(event, kb):
	"""Binds a new key to a certain keybinding (specified by 'kb').
	If this keybinding is already in use, an error message is displayed to the screen."""

	key = event.keysym

	# Check if entered key is already used by another binding
	key_free = True
	for binding in keybindings:
		if key == keybindings[binding]:
			key_free = False

			text["key_taken"] = settings_screen_canvas.create_text(S_WIDTH/2, 150, width=1000, font=medium_font, fill="yellow", text="Key already taken")

			# Flash the button with the same binding
			key_button_settings[binding].button.configure(activebackground="#aa1111")
			key_button_settings[binding].button.flash()
			key_button_settings[binding].button.configure(activebackground="black")


	if key_free:
		unbind_keybindings()

		keybindings[kb] = key

		# Update button text
		key_button_settings[kb].button.configure(text=kb.upper() + " - " + keybindings[kb])

		bind_keybindings()

	settings_screen_canvas.delete(text["key_prompt"])
	settings_screen_canvas.unbind("<Key>")

def change_keybinding(kb):
	settings_screen_canvas.bind("<Key>", lambda event: get_keypress(event, kb))

	try:
		settings_screen_canvas.delete(text["key_taken"])
	except KeyError:
		pass

	text["key_prompt"] = settings_screen_canvas.create_text(S_WIDTH / 2, S_HEIGHT - 100, width=1400, font=Font(size=100, family=font_family), fill="yellow", text="Press a key...")

def start_boss_screen(event):
	if playing:
		switch_screens(game_screen_canvas, boss_screen_canvas)

	if not paused:
		toggle_pause(-1)

def create_save(save_name, level, pacman, lives, ghosts, world, score):
	# Don't allow empty save names
	if len(save_name.strip()) == 0:
		return

	save(save_name, level, pacman, lives, ghosts, world, score)

	switch_screens(save_game_canvas, main_screen_canvas)

def start_load(save_name):
	global current_level, moving_sprites, pacman, pacman_lives, score

	try:
		load_game_canvas.delete(text["save_not_found"])
		text.pop("save_not_found")
	except KeyError:
		pass

	# Don't check for empty save names
	if len(save_name.strip()) == 0:
		return

	# Create 'empty' save object, this is loaded with information when we call load()
	loaded_game = Save(-1, -1, -1, -1, -1, -1, -1)
	load(loaded_game, save_name)

	# If Save attributes are not updated, the load failed because the save file doesn't exist
	if loaded_game.level == -1:
		if "save_not_found" not in text:
			text["save_not_found"] = load_game_canvas.create_text(S_WIDTH/2, 400, width=1500, font=score_font, fill="yellow", text="Save name not found")
		return

	json_ghosts = loaded_game.ghosts

	# Expand ghost data into Vec2 objects so they can be used in instantiation
	loaded_ghosts = []
	for ghost in json_ghosts:
		new_ghost = []
		for i in range(0, len(ghost)-2):
			new_ghost.append(Vec2(ghost[i]["x"], ghost[i]["y"]))

		new_ghost.append(ghost[len(ghost) - 2])
		new_ghost.append(ghost[len(ghost) - 1])

		loaded_ghosts.append(new_ghost)

	pacman_pos_vec = Vec2(loaded_game.pacman_pos["x"], loaded_game.pacman_pos["y"])

	current_level = loaded_game.level
	moving_sprites = [MovingSprite(game_screen_canvas, pacman_pos_vec, speed, 5,
						[Rect(0, 0, 20, 20),
						 Rect(20, 0, 40, 20),
						 Rect(40, 0, 60, 20)], scale=2),
	Ghost(game_screen_canvas, loaded_ghosts[0][0], speed, 5, [Rect(0, 20, 20, 40),
								      Rect(20, 20, 40, 40),
									  Rect(40, 20, 60, 40)], "blinky", scale=2),
	Ghost(game_screen_canvas, loaded_ghosts[1][0], speed, 5, [Rect(0, 40, 20, 60),
								      Rect(20, 40, 40, 60),
									  Rect(40, 40, 60, 60)], "inky", scale=2),
	Ghost(game_screen_canvas, loaded_ghosts[2][0], speed, 5, [Rect(0, 60, 20, 80),
								      Rect(20, 60, 40, 80),
									  Rect(40, 60, 60, 80)], "pinky", scale=2),
	Ghost(game_screen_canvas, loaded_ghosts[3][0], speed, 5, [Rect(0, 80, 20, 100),
								      Rect(20, 80, 40, 100),
									  Rect(40, 80, 60, 100)], "clyde", scale=2)]
	pacman = moving_sprites[0]

	pacman.direction = Vec2(loaded_game.pacman_dir["x"], loaded_game.pacman_dir["y"])

	# Recreate ghosts
	for i in range(1, 5):
		moving_sprites[i].direction = loaded_ghosts[i-1][1]
		moving_sprites[i].next_square = loaded_ghosts[i-1][2]
		moving_sprites[i].state = GhostState(loaded_ghosts[i-1][3])
		moving_sprites[i].panic_timer = loaded_ghosts[i-1][4]

	pacman_lives = loaded_game.pacman_lives
	score = loaded_game.score

	# Recreate world
	for i, row in enumerate(loaded_game.world):
		for j, cell in enumerate(row):
			if cell[0] == "X":
				world[i][j] = -1
			elif cell[0] == "W":
				pass
			elif cell[0] == "P" or cell[0] == "U":
				if cell[1]:
					world[i][j].eaten = True
					world[i][j].hide()
			elif cell[0] == "F":
				world[i][j] = Fruit(game_screen_canvas, cell[1], scale=2)
				world[i][j].timer = cell[2]

				world[i][j].image_id = world[i][j].draw()

	# Restart the game
	reset_game(loaded=True)
	switch_screens(load_game_canvas, game_screen_canvas)

def check_cheat_code(event):
	"""Check if the user has entered the cheat code 'mjw' and start ghost panic if so"""
	
	past_keypresses.append(event.char)

	if "".join(past_keypresses[-3:]) == "mjw":
		start_ghost_panic()

if "8-bit Operator+" in families():
	font_family = "8-bit Operator+"
else:
	font_family = "Tlwg Mono"

score_font = Font(size=14, family=font_family)
title_font = Font(size=50, family=font_family)
medium_font = Font(size=28, family=font_family)
big_font = Font(size=200, weight="bold", family=font_family)
button_font = Font(size=24, family=font_family)

button_styling = {
	"bg": "black",
	"activebackground": "black",
	"fg": "yellow",
	"activeforeground": "yellow",
	"bd": 0,
	"highlightthickness": 0,
	"font": button_font,
	"relief": "flat"
}

new_game_button = CanvasButton(window, main_screen_canvas, S_WIDTH/2, 200, {
	"text": "NEW GAME",
	"command": lambda: reset_game(new_game=True),
} | button_styling)

load_game_button = CanvasButton(window, main_screen_canvas, S_WIDTH/2, 300, {
	"text": "LOAD GAME",
	"command": lambda: switch_screens(main_screen_canvas, load_game_canvas),
} | button_styling)

scores_button = CanvasButton(window, main_screen_canvas, S_WIDTH/2, 400, {
	"text": "HIGH SCORES",
	"command": read_high_scores,
} | button_styling)

settings_button = CanvasButton(window, main_screen_canvas, S_WIDTH/2, 600, {
	"text": "SETTINGS",
	"command": lambda: switch_screens(main_screen_canvas, settings_screen_canvas),
} | button_styling)

quit_button = CanvasButton(window, main_screen_canvas, S_WIDTH/2, 800, {
	"text": "QUIT",
	"command": window.destroy,
	"activebackground": "red",
} | button_styling)

back_button_scores = CanvasButton(window, scores_screen_canvas, 60, 20, {
	"text": "BACK",
	"command": lambda: switch_screens(scores_screen_canvas, main_screen_canvas),
	"anchor": "se"
} | button_styling)

back_button_settings = CanvasButton(window, settings_screen_canvas, 60, 20, {
	"text": "BACK",
	"command": lambda: switch_screens(settings_screen_canvas, main_screen_canvas),
} | button_styling)

enter_button_add_scores = CanvasButton(window, add_score_canvas, S_WIDTH/2, 800, {
	"text": "ENTER",
	"command": lambda: add_score(player_name.get(), score),
} | button_styling)

up_button_settings = CanvasButton(window, settings_screen_canvas, S_WIDTH/3, 300, {
	"text": "UP - " + keybindings["up"],
	"command": lambda: change_keybinding("up"),
} | button_styling)

down_button_settings = CanvasButton(window, settings_screen_canvas, S_WIDTH/3, 400, {
	"text": "DOWN - " + keybindings["down"],
	"command": lambda: change_keybinding("down"),
} | button_styling)

left_button_settings = CanvasButton(window, settings_screen_canvas, S_WIDTH/3, 500, {
	"text": "LEFT - " + keybindings["left"],
	"command": lambda: change_keybinding("left"),
} | button_styling)

right_button_settings = CanvasButton(window, settings_screen_canvas, S_WIDTH/3, 600, {
	"text": "RIGHT - " + keybindings["right"],
	"command": lambda: change_keybinding("right"),
} | button_styling)

pause_button_settings = CanvasButton(window, settings_screen_canvas, S_WIDTH * 2/3, 350, {
	"text": "PAUSE - " + keybindings["pause"],
	"command": lambda: change_keybinding("pause"),
} | button_styling)

boss_button_settings = CanvasButton(window, settings_screen_canvas, S_WIDTH * 2/3, 550, {
	"text": "BOSS KEY - " + keybindings["boss"],
	"command": lambda: change_keybinding("boss"),
} | button_styling)

save_button = CanvasButton(window, game_screen_canvas, -100, -100, {
	"text": "SAVE AND QUIT",
	"command": lambda: switch_screens(game_screen_canvas, save_game_canvas),
} | button_styling)

enter_button_save_screen = CanvasButton(window, save_game_canvas, S_WIDTH/2, 600, {
	"text": "ENTER",
	"command": lambda: create_save(save_name.get(), current_level, pacman, pacman_lives, moving_sprites[1:5], world, score),
} | button_styling)

back_button_save_screen = CanvasButton(window, save_game_canvas, 60, 20, {
	"text": "BACK",
	"command": lambda: switch_screens(save_game_canvas, game_screen_canvas),
} | button_styling)

back_button_load_screen = CanvasButton(window, load_game_canvas, 60, 20, {
	"text": "BACK",
	"command": lambda: switch_screens(load_game_canvas, main_screen_canvas),
} | button_styling)

enter_button_save_screen = CanvasButton(window, load_game_canvas, S_WIDTH/2, 600, {
	"text": "ENTER",
	"command": lambda: start_load(save_name.get()),
} | button_styling)

key_button_settings = {
	"up": up_button_settings,
	"down": down_button_settings,
	"left": left_button_settings,
	"right": right_button_settings,
	"pause": pause_button_settings,
	"boss": boss_button_settings
}

player_name = StringVar()
score_entry = CanvasEntry(window, add_score_canvas, S_WIDTH/2, S_HEIGHT/2, {
	"textvariable": player_name,
	"font": button_font,
	"fg": "yellow",
	"relief": "flat",
	"bg": "#444444"
})

save_name = StringVar()
save_name_entry = CanvasEntry(window, save_game_canvas, S_WIDTH/2, S_HEIGHT/2, {
	"textvariable": save_name,
	"font": button_font,
	"fg": "yellow",
	"relief": "flat",
	"bg": "#444444"
})
load_name_entry = CanvasEntry(window, load_game_canvas, S_WIDTH/2, S_HEIGHT/2, {
	"textvariable": save_name,
	"font": button_font,
	"fg": "yellow",
	"relief": "flat",
	"bg": "#444444"
})

world = generate_level(game_screen_canvas, "grid.txt")

p_start = world2screen(10, 15)
ghost_start = [
	world2screen(9, 12),
	world2screen(11, 12),
	world2screen(9, 13),
	world2screen(11, 13)
]
panic_time = 10
speed = 3
moving_sprites = [MovingSprite(game_screen_canvas, p_start, speed, 5,
						[Rect(0, 0, 20, 20),
						 Rect(20, 0, 40, 20),
						 Rect(40, 0, 60, 20)], scale=2),
	Ghost(game_screen_canvas, ghost_start[0], speed, 5, [Rect(0, 20, 20, 40),
								      Rect(20, 20, 40, 40),
									  Rect(40, 20, 60, 40)], "blinky", scale=2),
	Ghost(game_screen_canvas, ghost_start[1], speed, 5, [Rect(0, 40, 20, 60),
								      Rect(20, 40, 40, 60),
									  Rect(40, 40, 60, 60)], "inky", scale=2),
	Ghost(game_screen_canvas, ghost_start[2], speed, 5, [Rect(0, 60, 20, 80),
								      Rect(20, 60, 40, 80),
									  Rect(40, 60, 60, 80)], "pinky", scale=2),
	Ghost(game_screen_canvas, ghost_start[3], speed, 5, [Rect(0, 80, 20, 100),
								      Rect(20, 80, 40, 100),
									  Rect(40, 80, 60, 100)], "clyde", scale=2)]
pacman = moving_sprites[0]

pacman_lives = 3
life_sprites = [Sprite(game_screen_canvas, Vec2(-2, i), [Rect(0, 0, 20, 20)]) for i in range(4)]
life_sprites[-1].hide()
gained_extra_life = False

score = 0
current_level = 0
ghosts_eaten = 0
last_pellets_eaten = 0

fruits = [
	Fruit(game_screen_canvas, fruit_type="cherry", scale=2),
	Fruit(game_screen_canvas, fruit_type="banana", scale=2),
	Fruit(game_screen_canvas, fruit_type="strawberry", scale=2),
	Fruit(game_screen_canvas, fruit_type="apple", scale=2),
	Fruit(game_screen_canvas, fruit_type="key", scale=2)
]

text = {"score": game_screen_canvas.create_text(5, 0, width=500, font=score_font, fill="yellow", text="Score: 0", anchor="nw"),
		"overwrite_save": save_game_canvas.create_text(S_WIDTH/2, 200, width=1500, font=score_font, justify="center",
												 fill="yellow", text="Enter a save name\nSaves will be OVERWRITTEN if they have the same name"),
		"load_help": load_game_canvas.create_text(S_WIDTH/2, 200, width=500, font=score_font, fill="yellow", text="Please enter save name to load:"),
		"score_screen_score": add_score_canvas.create_text(S_WIDTH/2, 100, width=1500, font=title_font, fill="yellow", text="You scored: "),
		"score_screen_help": add_score_canvas.create_text(S_WIDTH/2, 300, width=500, font=score_font, fill="yellow", text="Enter a name to save your score"),
		"load_game_title": load_game_canvas.create_text(S_WIDTH/2, 50, width=1000, font=title_font, fill="yellow", text="LOAD GAME"),
		"high_scores_title": scores_screen_canvas.create_text(S_WIDTH/2, 50, width=1000, font=title_font, fill="yellow", text="HIGH SCORES"),
		"settings_title": settings_screen_canvas.create_text(S_WIDTH/2, 50, width=1000, font=title_font, fill="yellow", text="SETTINGS"),}

past_keypresses = []
bind_keybindings()

# Add boss screen bindings
excel_gif = Image.open("img/vscode.png").resize((S_WIDTH, S_HEIGHT))
excel_gif = ImageTk.PhotoImage(excel_gif)
boss_screen_canvas.create_image(0, 0, image=excel_gif, anchor="nw")

paused = False
playing = False

main_screen_canvas.focus_set()

main_screen_canvas.pack()
ticks = 0
window.mainloop()
