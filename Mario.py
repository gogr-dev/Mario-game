# 12/10/2020

import pygame
from pygame.locals import*
from time import sleep

####################################
# Classes
####################################

class Sprite():
	def __init__(self, x, y):
		self.x = x
		self.y = y

	def isTube(self):
		return False
	def isGoomba(self):
		return False
	def isFireball(self):
		return False


class Mario(Sprite):
	def __init__(self, x, y):
		super(Mario, self).__init__(x, y)
		self.px = x
		self.py = y
		self.h = 95
		self.w = 56
		self.imgNum = 0
		self.Vert_vel = 0
		self.Air = 0
		self.marioOffset = 150
		self.onGround = False

		self.mario_images = []
		self.mario_images.append(pygame.image.load("mario1.png"))
		self.mario_images.append(pygame.image.load("mario2.png"))
		self.mario_images.append(pygame.image.load("mario3.png"))
		self.mario_images.append(pygame.image.load("mario4.png"))
		self.mario_images.append(pygame.image.load("mario5.png"))

	def draw(self, screen):
		screen.blit(self.mario_images[self.imgNum], (self.marioOffset, self.y))

	def update(self):
		self.Vert_vel += 5
		self.y += self.Vert_vel
		self.Air += 1

		# Mario ground
		if self.y > 407:
			self.Vert_vel = 0
			self.y = 407
			self.Air = 0
			self.onGround = True

		# Mario ceiling
		if self.y < 50:
			self.y = 50

		if self.imgNum > 4:
			self.imgNum = 0;

	def jump(self):
		if self.Air < 5:
			self.Vert_vel -= 13

	def previous(self):
		self.px = self.x
		self.py = self.y

	def getOutOfTube(self, tube):
		if self.px + self.w <= tube.x:
			self.x = tube.x-self.w
		if self.px >= tube.x + tube.w:
			self.x = tube.x + self.w
		if self.py + self.h <= tube.y:
			self.y = tube.y - self.h
			self.Vert_vel = 0
			self.Air = 0
			self.onGround = True


class Tube(Sprite):
	def __init__(self, x, y, model):
		super(Tube, self).__init__(x, y)
		self.model = model
		self.w = 55
		self.h = 400
		self.tube = pygame.image.load("tube.png")

	def update(self):
		return

	def draw(self, screen):
		screen.blit(self.tube, (self.x - self.model.mario.x + self.model.mario.marioOffset, self.y))

	def isTube(self):
		return True


class Goomba(Sprite):
	def __init__(self, x, y, model):
		super(Goomba, self).__init__(x, y)
		self.model = model
		self.w = 48
		self.h = 60
		self.px = x
		self.py = y
		self.timer = 30
		self.hitLeft = False
		self.hitRight = False
		self.onFire = False
		self.goomba = pygame.image.load("goomba.png")
		self.goomba2 = pygame.image.load("goomba_fire.png")

	def update(self):
		self.previous()
		if self.hitLeft == True:
			self.x -= 2.5
		elif self.hitRight == True:
			self.x += 2.5
		else:
			self.x += 2.5

	def previous(self):
		self.px = self.x
		self.py = self.y

	def getOutOfTube(self, tube):
		if self.px + self.w <= tube.x:
			self.hitRight = False
			self.hitLeft = True
		if self.px >= tube.x + tube.w:
			self.hitRight = True
			self.hitLeft = False

	def isGoomba(self):
		return True

	def draw(self, screen):
		if self.onFire == False:
			screen.blit(self.goomba, (self.x - self.model.mario.x + self.model.mario.marioOffset, self.y))
		else:
			screen.blit(self.goomba2, (self.x - self.model.mario.x + self.model.mario.marioOffset, self.y))


class Fireball(Sprite):
	def __init__(self, x, y, model):
		super(Fireball, self).__init__(x, y)
		self.model = model
		self.y = self.model.mario.y
		self.w = 47
		self.h = 47
		self.Vert_vel = 0
		self.offScreen = False
		self.fireball = pygame.image.load("fireball.png")

	def update(self):
		self.Vert_vel += 4
		self.y += self.Vert_vel
		self.x += 10

		if self.y - self.h > 420:
			self.Vert_vel = 0
			self.y = 420
			self.Vert_vel = -15
		if self.x - self.model.mario.x + self.model.mario.marioOffset - 25 >= 1000:
			self.offScreen = True

	def isFireball(self):
		return True

	def draw(self, screen):
		screen.blit(self.fireball, (self.x - self.model.mario.x + self.model.mario.marioOffset - 25, self.y))


class Model():
	def __init__(self):
		self.mario = Mario(100, 305)
		self.sprites = []
		self.sprites.append(self.mario)
		self.tube = Tube(270, 350, self)
		self.sprites.append(self.tube)
		self.tube = Tube(600, 390, self)
		self.sprites.append(self.tube)
		self.tube = Tube(800, 350, self)
		self.sprites.append(self.tube)
		self.tube = Tube(1000, 400, self)
		self.sprites.append(self.tube)
		self.goomba = Goomba(350, 448, self)
		self.sprites.append(self.goomba)
		self.goomba = Goomba(900, 448, self)
		self.sprites.append(self.goomba)


	def update(self):
		for i in range(len(self.sprites)):
			self.sprites[i].update()
			if self.sprites[i].isTube():
				self.t = self.sprites[i]
				if self.spriteCollision(self.mario, self.t):
					self.mario.getOutOfTube(self.t)
				for j in range(len(self.sprites)):
					self.g = self.sprites[j]
					if self.g.isGoomba():
						if self.spriteCollision(self.g, self.t):
							self.g.getOutOfTube(self.t)
						for k in range(len(self.sprites)):
							if self.sprites[k].isFireball():
								self.f = self.sprites[k]
								if self.spriteCollision(self.f, self.g):
									self.g.onFire = True
		for sprite in self.sprites:
			if sprite.isGoomba():
				if sprite.onFire == True:
					sprite.timer -= 1
					if sprite.timer == 0:
						self.sprites.remove(sprite)
						sprite.timer = 42;
		for sprite in self.sprites:
			if sprite.isFireball():
				if sprite.offScreen == True:
					self.sprites.remove(sprite)

	def spriteCollision(self, a, b):
		self.a = a;
		self.b = b;

		if self.a.x + self.a.w < self.b.x:
			return False
		if self.a.x > self.b.x + self.b.w:
			return False
		if self.a.y + self.a.h < self.b.y:
			return False
		if self.a.y > self.b.y + self.b.h:
			return False
		else:
			return True


class View():
	def __init__(self, model):
		self.model = model
		screen_size = (1000, 600)
		self.screen = pygame.display.set_mode(screen_size, 32)
		self.background = pygame.image.load("background.png")

	def update(self):
		self.screen.blit(self.background, (0, -120))
		for i in range(len(self.model.sprites)):
			self.model.sprites[i].draw(self.screen)
		pygame.display.flip()

class Controller():
	def __init__(self, model, view):
		self.model = model
		self.view = view
		self.keep_going = True

	def update(self):
		for event in pygame.event.get():
			if event.type == QUIT:
				self.keep_going = False

			elif event.type == KEYDOWN:
				if event.key == K_ESCAPE:
					self.keep_going = False

		key = pygame.key.get_pressed()
		self.model.mario.previous()

		if key[K_SPACE] or key[K_UP]:
			if self.model.mario.onGround == True:
				self.model.mario.jump()
			if self.model.mario.onGround == False:
				return

		if key[K_LEFT]:
			self.model.mario.x -= 6
			self.model.mario.imgNum += 1

		if key[K_RIGHT]:
			self.model.mario.x += 6
			self.model.mario.imgNum += 1

		if key[K_LCTRL]:
			self.fireball = Fireball(self.model.mario.x + self.model.mario.w, self.model.mario.y, self.model)
			self.model.sprites.append(self.fireball)


pygame.display.set_caption("Super Mario Bros")
print("Use the arrow keys to move. Press Esc to quit.")
pygame.init()
m = Model()
v = View(m)
c = Controller(m, v)

# Main game loop
while c.keep_going:
	c.update()
	m.update()
	v.update()
	sleep(0.04)
print("Goodbye")
