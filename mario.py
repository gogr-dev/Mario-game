"""A small Mario-style platformer in pygame.

Run with the arrow keys to move, space/up to jump, and left-ctrl (or F) to throw
fireballs. Stomp goombas or burn them; touching one any other way costs a life.
Reach the end of the level to win. R restarts, Esc quits.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pygame

# --- tuning ---------------------------------------------------------------

SCREEN_W, SCREEN_H = 1000, 600
FPS = 60

GROUND_Y = 502          # y of the ground line (where feet rest)
GRAVITY = 0.5           # px/frame^2
JUMP_VELOCITY = -15.0   # px/frame
MOVE_SPEED = 4.0
CAMERA_OFFSET = 150     # where Mario sits on screen

GOOMBA_SPEED = 1.2
STOMP_BOUNCE = -8.0
BURN_FRAMES = 45        # how long a burned goomba smolders before despawning

FIREBALL_SPEED = 7.0
FIREBALL_GRAVITY = 0.4
FIREBALL_BOUNCE = -11.0
FIREBALL_COOLDOWN = 20  # frames between throws

START_LIVES = 3
HURT_INVINCIBLE_FRAMES = 120
LEVEL_END = 2400        # reach this x to win
LEVEL_W = 2600

ASSETS = Path(__file__).resolve().parent

# --- assets ---------------------------------------------------------------

_image_cache: dict[str, pygame.Surface] = {}


def load_image(name: str) -> pygame.Surface:
    """Load an image once; reuse it for every sprite that needs it."""
    if name not in _image_cache:
        image = pygame.image.load(str(ASSETS / name))
        if pygame.display.get_surface() is not None:
            image = image.convert_alpha()
        _image_cache[name] = image
    return _image_cache[name]


# --- sprites ----------------------------------------------------------------

class Sprite:
    """Anything with a position, size, and a place in the world."""

    def __init__(self, x: float, y: float, w: int, h: int):
        self.x, self.y, self.w, self.h = x, y, w, h

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def update(self, model: "Model") -> None:
        pass

    def draw(self, screen: pygame.Surface, camera_x: float) -> None:
        pass


class Mario(Sprite):
    W, H = 60, 95
    FRAMES = ["mario1.png", "mario2.png", "mario3.png", "mario4.png", "mario5.png"]

    def __init__(self, x: float, y: float):
        super().__init__(x, y, self.W, self.H)
        self.prev_x, self.prev_y = x, y
        self.vy = 0.0
        self.on_ground = False
        self.facing_right = True
        self.frame = 0
        self.anim_clock = 0
        self.invincible = 0

    # -- movement --

    def remember_position(self) -> None:
        self.prev_x, self.prev_y = self.x, self.y

    def walk(self, direction: int) -> None:
        """direction: -1 left, +1 right."""
        self.x += MOVE_SPEED * direction
        self.x = max(0.0, min(self.x, LEVEL_W - self.w))
        self.facing_right = direction > 0
        self.anim_clock += 1
        if self.anim_clock % 4 == 0:
            self.frame = (self.frame + 1) % len(self.FRAMES)

    def jump(self) -> None:
        if self.on_ground:
            self.vy = JUMP_VELOCITY
            self.on_ground = False

    def update(self, model: "Model") -> None:
        self.vy += GRAVITY
        self.y += self.vy
        self.on_ground = False

        if self.y + self.h >= GROUND_Y:           # land on the ground
            self.y = GROUND_Y - self.h
            self.vy = 0.0
            self.on_ground = True
        if self.y < 0:                            # ceiling
            self.y = 0
            self.vy = 0.0
        if self.invincible > 0:
            self.invincible -= 1

    # -- collisions --

    def push_out_of(self, tube: "Tube") -> None:
        """Resolve a tube collision using where Mario came from."""
        if self.prev_x + self.w <= tube.x:        # came from the left
            self.x = tube.x - self.w
        elif self.prev_x >= tube.x + tube.w:      # came from the right
            self.x = tube.x + tube.w
        elif self.prev_y + self.h <= tube.y:      # landed on top
            self.y = tube.y - self.h
            self.vy = 0.0
            self.on_ground = True
        else:                                     # bumped from below
            self.y = tube.y + tube.h
            self.vy = 0.0

    def hurt(self) -> bool:
        """Take a hit. Returns True if it actually landed (not invincible)."""
        if self.invincible > 0:
            return False
        self.invincible = HURT_INVINCIBLE_FRAMES
        return True

    # -- drawing --

    def draw(self, screen: pygame.Surface, camera_x: float) -> None:
        if self.invincible > 0 and (self.invincible // 4) % 2 == 0:
            return                                # flash while invincible
        image = load_image(self.FRAMES[self.frame])
        if not self.facing_right:
            image = pygame.transform.flip(image, True, False)
        screen.blit(image, (self.x - camera_x, self.y))


class Tube(Sprite):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, 55, 400)

    def draw(self, screen: pygame.Surface, camera_x: float) -> None:
        screen.blit(load_image("tube.png"), (self.x - camera_x, self.y))


class Goomba(Sprite):
    W, H = 50, 59

    def __init__(self, x: float, direction: int = 1):
        super().__init__(x, GROUND_Y - self.H, self.W, self.H)
        self.direction = direction
        self.burning = 0          # frames left to smolder; 0 = alive
        self.dead = False

    @property
    def alive(self) -> bool:
        return not self.dead and self.burning == 0

    def update(self, model: "Model") -> None:
        if self.burning > 0:
            self.burning -= 1
            if self.burning == 0:
                self.dead = True
            return
        self.x += GOOMBA_SPEED * self.direction
        if self.x <= 0 or self.x + self.w >= LEVEL_W:
            self.direction *= -1

    def turn_away_from(self, tube: "Tube") -> None:
        self.direction = -1 if self.x + self.w / 2 < tube.x + tube.w / 2 else 1
        # Step out of the tube so the collision doesn't re-trigger every frame.
        if self.direction < 0:
            self.x = tube.x - self.w
        else:
            self.x = tube.x + tube.w

    def burn(self) -> None:
        if self.alive:
            self.burning = BURN_FRAMES

    def stomp(self) -> None:
        self.dead = True

    def draw(self, screen: pygame.Surface, camera_x: float) -> None:
        name = "goomba_fire.png" if self.burning > 0 else "goomba.png"
        screen.blit(load_image(name), (self.x - camera_x, self.y))


class Fireball(Sprite):
    W, H = 47, 47

    def __init__(self, x: float, y: float, direction: int):
        super().__init__(x, y, self.W, self.H)
        self.vy = 0.0
        self.direction = direction
        self.done = False

    def update(self, model: "Model") -> None:
        self.vy += FIREBALL_GRAVITY
        self.y += self.vy
        self.x += FIREBALL_SPEED * self.direction

        if self.y + self.h >= GROUND_Y:           # bounce along the ground
            self.y = GROUND_Y - self.h
            self.vy = FIREBALL_BOUNCE
        # Despawn once it leaves the visible world.
        if (self.x < model.camera_x - self.w or self.x > model.camera_x + SCREEN_W
                or self.x < 0 or self.x > LEVEL_W):
            self.done = True

    def draw(self, screen: pygame.Surface, camera_x: float) -> None:
        screen.blit(load_image("fireball.png"), (self.x - camera_x, self.y))


# --- model -------------------------------------------------------------------

class Model:
    """Owns the world: sprites, score, lives, and all collision rules."""

    def __init__(self):
        self.reset()

    def reset(self) -> None:
        self.mario = Mario(100, GROUND_Y - Mario.H)
        self.tubes = [Tube(270, 350), Tube(600, 390), Tube(800, 350),
                      Tube(1100, 400), Tube(1500, 370), Tube(1900, 390)]
        self.goombas = [Goomba(420), Goomba(950), Goomba(1350),
                        Goomba(1700, -1), Goomba(2100)]
        self.fireballs: list[Fireball] = []
        self.score = 0
        self.lives = START_LIVES
        self.state = "playing"        # playing | won | game over
        self.fire_cooldown = 0
        self.camera_x = 0.0

    # -- actions --

    def throw_fireball(self) -> None:
        if self.state != "playing" or self.fire_cooldown > 0:
            return
        direction = 1 if self.mario.facing_right else -1
        x = self.mario.x + (self.mario.w if direction > 0 else -Fireball.W)
        self.fireballs.append(Fireball(x, self.mario.y, direction))
        self.fire_cooldown = FIREBALL_COOLDOWN

    # -- frame update --

    def update(self) -> None:
        if self.state != "playing":
            return
        if self.fire_cooldown > 0:
            self.fire_cooldown -= 1

        for sprite in [self.mario, *self.goombas, *self.fireballs]:
            sprite.update(self)

        self._collide()

        # Remove finished sprites by building new lists (never mutate mid-loop).
        self.goombas = [g for g in self.goombas if not g.dead]
        self.fireballs = [f for f in self.fireballs if not f.done]

        self.camera_x = max(0.0, min(self.mario.x - CAMERA_OFFSET,
                                     LEVEL_W - SCREEN_W))
        if self.mario.x + self.mario.w >= LEVEL_END:
            self.state = "won"

    def _collide(self) -> None:
        mario = self.mario

        for tube in self.tubes:
            if mario.rect.colliderect(tube.rect):
                mario.push_out_of(tube)
            for goomba in self.goombas:
                if goomba.alive and goomba.rect.colliderect(tube.rect):
                    goomba.turn_away_from(tube)

        for goomba in self.goombas:
            if not goomba.alive:
                continue
            for fireball in self.fireballs:
                if fireball.rect.colliderect(goomba.rect):
                    goomba.burn()
                    fireball.done = True
                    self.score += 100
                    break
            if goomba.alive and mario.rect.colliderect(goomba.rect):
                stomped = mario.vy > 0 and mario.prev_y + mario.h <= goomba.y + 12
                if stomped:
                    goomba.stomp()
                    mario.vy = STOMP_BOUNCE
                    self.score += 100
                elif mario.hurt():
                    self.lives -= 1
                    if self.lives <= 0:
                        self.state = "game over"


# --- view / controller -------------------------------------------------------

class View:
    BG_Y = SCREEN_H - 720          # align the background's brick floor to the bottom

    def __init__(self, model: Model):
        self.model = model
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.font = pygame.font.SysFont(None, 32)
        self.big_font = pygame.font.SysFont(None, 72)

    def update(self) -> None:
        model = self.model
        self._draw_background(model.camera_x)
        for sprite in [*model.tubes, *model.goombas, *model.fireballs, model.mario]:
            sprite.draw(self.screen, model.camera_x)
        self._draw_hud()
        pygame.display.flip()

    def _draw_background(self, camera_x: float) -> None:
        background = load_image("background.png")
        bg_w = background.get_width()
        offset = int(camera_x * 0.5) % bg_w     # gentle parallax scroll
        self.screen.blit(background, (-offset, self.BG_Y))
        self.screen.blit(background, (bg_w - offset, self.BG_Y))

    def _draw_hud(self) -> None:
        model = self.model
        hud = self.font.render(
            f"SCORE {model.score:05d}    LIVES {model.lives}", True, (255, 255, 255))
        self.screen.blit(hud, (16, 12))
        if model.state != "playing":
            text = "YOU WIN!" if model.state == "won" else "GAME OVER"
            banner = self.big_font.render(text, True, (255, 255, 255))
            again = self.font.render("press R to play again", True, (255, 255, 255))
            self.screen.blit(banner, banner.get_rect(center=(SCREEN_W // 2, 250)))
            self.screen.blit(again, again.get_rect(center=(SCREEN_W // 2, 310)))


class Controller:
    def __init__(self, model: Model):
        self.model = model
        self.keep_going = True

    def update(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.keep_going = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.keep_going = False
                elif event.key in (pygame.K_SPACE, pygame.K_UP):
                    self.model.mario.jump()
                elif event.key == pygame.K_r and self.model.state != "playing":
                    self.model.reset()

        keys = pygame.key.get_pressed()
        self.model.mario.remember_position()
        if keys[pygame.K_LEFT]:
            self.model.mario.walk(-1)
        if keys[pygame.K_RIGHT]:
            self.model.mario.walk(1)
        if keys[pygame.K_LCTRL] or keys[pygame.K_f]:
            self.model.throw_fireball()


# --- entry point ---------------------------------------------------------

def main() -> None:
    pygame.init()
    pygame.display.set_caption("Super Mario")
    model = Model()
    view = View(model)
    controller = Controller(model)
    clock = pygame.time.Clock()

    while controller.keep_going:
        controller.update()
        model.update()
        view.update()
        clock.tick(FPS)
    pygame.quit()


if __name__ == "__main__":
    main()
