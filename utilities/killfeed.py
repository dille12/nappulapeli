import pygame

class KillFeed:
    def __init__(self, killer, killed, gun, saved = False):
        self.app = killer.app
        self.killer = killer
        self.killed = killed
        self.gun = gun
        self.killer.gainKill(killed)

        self.color = killer.teamColor.copy()
        for i, x in enumerate(self.color):
            self.color[i] = int(100*x/255)


        self.app.killfeed.append(self)
        self.lifetime = 3
        self.maxL = self.lifetime
        
        t1 = self.app.font.render(self.killer.name, True, killer.teamColor)
        t2 = self.app.font.render(self.killed.name, True, killed.teamColor)
        self.surface = pygame.Surface((t1.get_width() + t2.get_width() + gun.imageKillFeed.get_width() + 30, max(t1.get_height(), t2.get_height()) + 10))
        self.surface.fill(self.color)
        self.surface.blit(t1, [5,5])
        self.surface.blit(gun.imageKillFeed, [15 + t1.get_width(), self.surface.get_height()/2-gun.imageKillFeed.get_height()/2])
        self.surface.blit(t2, [self.surface.get_width() - t2.get_width() - 5, 5])


    def tick(self):
        self.lifetime -= self.app.deltaTime
        if self.lifetime <= 0:
            self.app.killfeed.remove(self)
            return
        
        pos = [self.app.res[0] - self.surface.get_width() - 5, 30 + self.app.killfeed.index(self)*55]

        if self.lifetime >= self.maxL - 0.2:
            i = 1-((self.maxL - self.lifetime)/0.2)
            pos[0] += self.surface.get_width() * 1.25 * i**2

        elif self.lifetime < 0.5:
            i = ((0.5 - self.lifetime)/0.5)
            pos[0] += self.surface.get_width() * 1.25 * i**2

        self.app.screen.blit(self.surface, pos)
