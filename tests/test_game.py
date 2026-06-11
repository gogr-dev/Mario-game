"""Headless tests for the game model. Run: python -m unittest discover -s tests"""

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame  # noqa: E402

pygame.init()

import mario as game  # noqa: E402
from mario import Fireball, Goomba, Mario, Model, Tube  # noqa: E402


class ModelTest(unittest.TestCase):
    def setUp(self):
        self.model = Model()
        # A controlled world: one tube, one goomba, far from each other.
        self.model.tubes = [Tube(600, 390)]
        self.model.goombas = [Goomba(400)]
        self.model.fireballs = []
        self.mario = self.model.mario

    def place_mario(self, x, y, vy=0.0):
        self.mario.x, self.mario.y, self.mario.vy = x, y, vy
        self.mario.remember_position()

    # -- stomping ----------------------------------------------------------

    def test_stomp_kills_goomba_and_bounces(self):
        goomba = self.model.goombas[0]
        self.place_mario(goomba.x, goomba.y - self.mario.h - 4, vy=8.0)
        self.model.update()
        self.assertEqual(self.model.goombas, [])           # squashed + removed
        self.assertLess(self.mario.vy, 0)                  # bounced up
        self.assertEqual(self.model.score, 100)
        self.assertEqual(self.model.lives, game.START_LIVES)  # unhurt

    def test_side_contact_costs_a_life(self):
        goomba = self.model.goombas[0]
        self.place_mario(goomba.x - self.mario.w + 10, goomba.y - 10)
        self.mario.update(self.model)
        self.mario.remember_position()                     # walked in, not falling
        self.model.update()
        self.assertEqual(self.model.lives, game.START_LIVES - 1)
        self.assertEqual(len(self.model.goombas), 1)       # goomba survives

    def test_invincibility_prevents_repeat_hits(self):
        goomba = self.model.goombas[0]
        self.place_mario(goomba.x, goomba.y)
        self.mario.remember_position()
        for _ in range(10):                                # overlapping for 10 frames
            self.model.update()
            self.mario.x, self.mario.y = goomba.x, goomba.y
            self.mario.remember_position()
        self.assertEqual(self.model.lives, game.START_LIVES - 1)  # only one hit

    def test_three_hits_is_game_over(self):
        goomba = self.model.goombas[0]
        for _ in range(3):
            self.mario.invincible = 0
            self.place_mario(goomba.x, goomba.y)
            self.model.update()
        self.assertEqual(self.model.lives, 0)
        self.assertEqual(self.model.state, "game over")

    # -- fireballs -----------------------------------------------------------

    def test_fireball_burns_goomba_then_despawns_it(self):
        goomba = self.model.goombas[0]
        self.model.fireballs = [Fireball(goomba.x - 5, goomba.y, 1)]
        self.model.update()
        self.assertTrue(goomba.burning > 0)
        self.assertEqual(self.model.fireballs, [])         # fireball consumed
        self.assertEqual(self.model.score, 100)
        for _ in range(game.BURN_FRAMES + 1):              # smolders, then gone
            self.model.update()
        self.assertEqual(self.model.goombas, [])

    def test_fireball_cooldown_prevents_spam(self):
        for _ in range(5):                                 # "hold the button"
            self.model.throw_fireball()
        self.assertEqual(len(self.model.fireballs), 1)
        for _ in range(game.FIREBALL_COOLDOWN + 1):
            self.model.update()
        self.model.throw_fireball()
        self.assertEqual(len(self.model.fireballs), 2)

    def test_fireball_thrown_in_facing_direction(self):
        self.mario.facing_right = False
        self.model.throw_fireball()
        self.assertEqual(self.model.fireballs[0].direction, -1)

    # -- tubes ---------------------------------------------------------------

    def test_tube_blocks_from_the_left(self):
        tube = self.model.tubes[0]
        self.place_mario(tube.x - self.mario.w + 2, tube.y + 5)
        self.mario.prev_x = tube.x - self.mario.w - 6      # walked in from the left
        self.model.update()
        self.assertLessEqual(self.mario.x + self.mario.w, tube.x)

    def test_tube_blocks_from_the_right(self):
        tube = self.model.tubes[0]
        self.place_mario(tube.x + tube.w - 2, tube.y + 5)
        self.mario.prev_x = tube.x + tube.w + 6            # walked in from the right
        self.model.update()
        self.assertGreaterEqual(self.mario.x, tube.x + tube.w)  # exact, not w-1 off

    def test_mario_lands_on_tube_top(self):
        tube = self.model.tubes[0]
        self.place_mario(tube.x, tube.y - self.mario.h - 2, vy=6.0)
        self.model.update()
        self.assertEqual(self.mario.y, tube.y - self.mario.h)
        self.assertTrue(self.mario.on_ground)

    def test_goomba_turns_around_at_tube(self):
        tube = self.model.tubes[0]
        goomba = self.model.goombas[0]
        goomba.x = tube.x - goomba.w + 2                   # walking right into it
        goomba.direction = 1
        self.model.update()
        self.assertEqual(goomba.direction, -1)

    # -- bookkeeping -----------------------------------------------------------

    def test_adjacent_dead_goombas_all_removed_in_one_frame(self):
        # Regression: removing from a list while iterating skipped neighbours.
        self.model.goombas = [Goomba(300), Goomba(305), Goomba(310)]
        for goomba in self.model.goombas:
            goomba.stomp()
        self.model.update()
        self.assertEqual(self.model.goombas, [])

    def test_reaching_level_end_wins(self):
        self.place_mario(game.LEVEL_END + 1, game.GROUND_Y - self.mario.h)
        self.model.update()
        self.assertEqual(self.model.state, "won")
        score = self.model.score
        self.model.update()                                # frozen after winning
        self.assertEqual(self.model.score, score)

    def test_reset_restores_everything(self):
        self.model.score = 500
        self.model.lives = 1
        self.model.state = "game over"
        self.model.reset()
        self.assertEqual(self.model.score, 0)
        self.assertEqual(self.model.lives, game.START_LIVES)
        self.assertEqual(self.model.state, "playing")
        self.assertGreater(len(self.model.goombas), 0)

    def test_camera_clamps_to_level(self):
        self.place_mario(0, game.GROUND_Y - self.mario.h)
        self.model.update()
        self.assertEqual(self.model.camera_x, 0)
        self.place_mario(game.LEVEL_END - 10, game.GROUND_Y - self.mario.h)
        self.model.update()
        self.assertLessEqual(self.model.camera_x, game.LEVEL_W - game.SCREEN_W)


class MarioPhysicsTest(unittest.TestCase):
    def test_jump_only_from_ground(self):
        m = Mario(100, game.GROUND_Y - Mario.H)
        m.update(Model())                                  # settle onto the ground
        self.assertTrue(m.on_ground)
        m.jump()
        self.assertLess(m.vy, 0)
        vy_mid_jump = m.vy
        m.jump()                                           # no double jump
        self.assertEqual(m.vy, vy_mid_jump)

    def test_walk_clamps_to_level_bounds(self):
        m = Mario(2, 100)
        m.walk(-1)
        self.assertEqual(m.x, 0)

    def test_walk_animates_and_faces(self):
        m = Mario(100, 100)
        for _ in range(8):
            m.walk(1)
        self.assertTrue(m.facing_right)
        self.assertNotEqual(m.frame, 0)
        m.walk(-1)
        self.assertFalse(m.facing_right)


if __name__ == "__main__":
    unittest.main()
