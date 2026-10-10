#!/usr/bin/env python3
"""Rhodochrosite Roll — neon pinball arcade for ElbowOS. Python 3 + pygame."""
import math, os, random, subprocess, sys

RECORD = "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1"
PLAY = "--play" in sys.argv

if RECORD or not PLAY:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

W, H, FPS, SECS = 1080, 1920, 30, 15
OUT = os.environ.get("ELBOWOS_MP4", "/workspace/artifacts/RHODOCHROSITE_ROLL_ElbowOS.mp4")
TITLE, HANDLE = "RHODO ROLL", "x.com/ElbowOS"

BG = (12, 4, 20)
PINK = (255, 40, 120)
CYAN = (40, 255, 220)
YELLOW = (255, 220, 40)
WHITE = (255, 255, 255)
DARK = (30, 10, 40)

class Ball:
    def __init__(self):
        self.reset()
    def reset(self):
        self.x = W // 2 + random.randint(-100, 100)
        self.y = 400
        self.vx = random.uniform(-8, 8)
        self.vy = random.uniform(2, 6)
        self.r = 28
    def update(self, flippers):
        self.vy += 0.35  # gravity
        self.x += self.vx
        self.y += self.vy
        # walls
        if self.x < self.r:
            self.x = self.r
            self.vx = abs(self.vx) * 0.9
        if self.x > W - self.r:
            self.x = W - self.r
            self.vx = -abs(self.vx) * 0.9
        # ceiling
        if self.y < self.r:
            self.y = self.r
            self.vy = abs(self.vy) * 0.8
        # floor drain
        if self.y > H - 80:
            self.reset()
            return -50
        # flippers
        for fl in flippers:
            if fl.active and abs(self.x - fl.x) < 140 and abs(self.y - fl.y) < 40:
                self.vy = -abs(self.vy) * 1.1 - 8
                self.vx += (self.x - fl.x) * 0.08
                return 10
        return 0

class Flipper:
    def __init__(self, x, side):
        self.x = x
        self.y = H - 280
        self.side = side  # -1 left, 1 right
        self.active = False
        self.timer = 0
    def update(self):
        if self.active:
            self.timer -= 1
            if self.timer <= 0:
                self.active = False
    def activate(self):
        self.active = True
        self.timer = 8

class Bumper:
    def __init__(self, x, y, r=50):
        self.x = x
        self.y = y
        self.r = r
        self.flash = 0
    def hit(self, ball):
        dx = ball.x - self.x
        dy = ball.y - self.y
        dist = math.hypot(dx, dy)
        if dist < self.r + ball.r:
            if dist > 0:
                nx, ny = dx / dist, dy / dist
                ball.vx = nx * 12 + random.uniform(-2, 2)
                ball.vy = ny * 12 + random.uniform(-2, 2)
                ball.x = self.x + nx * (self.r + ball.r + 2)
                ball.y = self.y + ny * (self.r + ball.r + 2)
            self.flash = 10
            return 25
        return 0
    def update(self):
        if self.flash > 0:
            self.flash -= 1

class Game:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        flags = 0 if PLAY else pygame.HIDDEN
        try:
            self.screen = pygame.display.set_mode((W, H), flags)
        except pygame.error:
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            self.screen = pygame.display.set_mode((W, H), pygame.HIDDEN)
        self.surf = pygame.Surface((W, H))
        self.clock = pygame.time.Clock()
        self.font_big = pygame.font.SysFont("Arial", 72, bold=True)
        self.font_med = pygame.font.SysFont("Arial", 48, bold=True)
        self.font_sm = pygame.font.SysFont("Arial", 36)
        self.ball = Ball()
        self.flip_l = Flipper(W//2 - 220, -1)
        self.flip_r = Flipper(W//2 + 220, 1)
        self.bumpers = [
            Bumper(300, 700), Bumper(780, 700),
            Bumper(540, 500), Bumper(200, 1100),
            Bumper(880, 1100), Bumper(540, 1400)
        ]
        self.score = 0
        self.frame = 0
        self.auto_timer = 0

    def draw(self):
        self.surf.fill(BG)
        # side walls
        pygame.draw.rect(self.surf, CYAN, (0, 0, 20, H))
        pygame.draw.rect(self.surf, CYAN, (W-20, 0, 20, H))
        # bumpers
        for b in self.bumpers:
            col = YELLOW if b.flash > 0 else PINK
            pygame.draw.circle(self.surf, col, (int(b.x), int(b.y)), b.r)
            pygame.draw.circle(self.surf, WHITE, (int(b.x), int(b.y)), b.r, 4)
        # flippers
        for fl in (self.flip_l, self.flip_r):
            col = CYAN if fl.active else (80, 200, 180)
            ang = -0.6 if fl.side < 0 else 0.6
            if fl.active:
                ang *= -1
            pts = []
            for i in range(3):
                a = ang + (i - 1) * 0.3
                pts.append((fl.x + math.cos(a)*120, fl.y + math.sin(a)*30))
            pygame.draw.polygon(self.surf, col, pts)
            pygame.draw.polygon(self.surf, WHITE, pts, 3)
        # ball
        pygame.draw.circle(self.surf, WHITE, (int(self.ball.x), int(self.ball.y)), self.ball.r)
        pygame.draw.circle(self.surf, PINK, (int(self.ball.x), int(self.ball.y)), self.ball.r, 5)
        # overlays
        title = self.font_big.render(TITLE, True, CYAN)
        self.surf.blit(title, (W//2 - title.get_width()//2, 40))
        sc = self.font_med.render(f"SCORE {self.score}", True, YELLOW)
        self.surf.blit(sc, (W//2 - sc.get_width()//2, 140))
        handle = self.font_sm.render(HANDLE, True, WHITE)
        self.surf.blit(handle, (W//2 - handle.get_width()//2, H - 80))
        self.screen.blit(self.surf, (0, 0))
        if PLAY:
            pygame.display.flip()

    def update(self, keys=None):
        self.flip_l.update()
        self.flip_r.update()
        for b in self.bumpers:
            b.update()
        # auto or keys
        if not PLAY or RECORD:
            self.auto_timer -= 1
            if self.auto_timer <= 0:
                self.auto_timer = random.randint(4, 12)
                if self.ball.x < W//2 and self.ball.y > H//2:
                    self.flip_l.activate()
                elif self.ball.x > W//2 and self.ball.y > H//2:
                    self.flip_r.activate()
                else:
                    if random.random() < 0.5:
                        self.flip_l.activate()
                    else:
                        self.flip_r.activate()
        else:
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.flip_l.activate()
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.flip_r.activate()
        pts = self.ball.update([self.flip_l, self.flip_r])
        self.score += pts
        for b in self.bumpers:
            self.score += b.hit(self.ball)
        self.score = max(0, self.score)
        self.frame += 1

    def record(self):
        cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-vcodec", "rawvideo",
            "-s", f"{W}x{H}", "-pix_fmt", "rgb24", "-r", str(FPS),
            "-i", "-", "-an", "-vcodec", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "20", "-preset", "fast", "-movflags", "+faststart",
            OUT
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        frames = FPS * SECS
        try:
            for _ in range(frames):
                self.update()
                self.draw()
                raw = pygame.image.tostring(self.surf, "RGB")
                proc.stdin.write(raw)
            proc.stdin.close()
        except BrokenPipeError:
            err = proc.stderr.read().decode("utf-8", "ignore")
            raise SystemExit(f"ffmpeg broken pipe:\n{err[-2000:]}")
        err = proc.stderr.read().decode("utf-8", "ignore")
        rc = proc.wait()
        if rc != 0:
            raise SystemExit(f"ffmpeg failed ({rc}):\n{err[-1200:]}")
        print("wrote", OUT)
        pygame.quit()

    def play_interactive(self):
        running = True
        while running:
            for e in pygame.event.get():
                if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                    running = False
            keys = pygame.key.get_pressed()
            self.update(keys)
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()

def main():
    g = Game()
    if PLAY and not RECORD:
        g.play_interactive()
    else:
        g.record()

if __name__ == "__main__":
    main()
