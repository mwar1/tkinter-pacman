"""Abstractions of Tkinter widgets to more finely control their behaviour"""

from tkinter import Button, Entry
from tkinter.font import Font

class CanvasButton:
	"""Represents a single button in a canvas, used to perform a single function"""
	def __init__(self, window, canvas, x, y, options):
		self.button = Button(window, **options)
		self.button_id = canvas.create_window(x, y, window=self.button)

		font_family = options["font"].actual()["family"]
		self.normal_font = Font(size=24, family=font_family)
		self.hover_font = Font(size=30, family=font_family)

		self.button.bind('<Enter>', self.enter)
		self.button.bind('<Leave>', self.leave)

	def enter(self, event):
		self.button.configure(font=self.hover_font)

	def leave(self, event):
		self.button.configure(font=self.normal_font)


class CanvasEntry:
	"""Represents a Tkinter Entry widget, while also allowing clearing easily"""
	def __init__(self, window, canvas, x, y, options):
		self.canvas = canvas

		self.entry = Entry(window, **options)
		self.entry_id = canvas.create_window(x, y, window=self.entry)

	def clear_text(self):
		self.entry.delete(0, "end")
