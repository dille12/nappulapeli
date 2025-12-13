import pygame


from pathlib import Path

def register_gun_kill(gun_name, team_kill = False, path="weapon_kills.txt"):
    p = Path(path)
    kills = {}

    if p.exists():
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().rsplit(" ", 1)
                if len(parts) == 2 and parts[1].isdigit():
                    kills[parts[0]] = int(parts[1])

    kills[gun_name] = kills.get(gun_name, 0) + 1

    with p.open("w", encoding="utf-8") as f:
        for k, v in sorted(kills.items(), key=lambda x: -x[1]):
            f.write(f"{k} {v}\n")


class KillFeed:
    def __init__(self, killer, killed, gun, saved = False):
        self.app = killed.app
        self.killer = killer
        self.killed = killed
        self.gun = gun
        if self.killer:
            self.killer.gainKill(killed)

            self.color = killer.teamColor.copy()
        else:
            self.color = killed.teamColor.copy()
        for i, x in enumerate(self.color):
            self.color[i] = int(100*x/255)


        self.app.killfeed.append(self)
        self.lifetime = 3
        self.maxL = self.lifetime

        if self.gun == "melee":
            self.gunIcon = self.app.killFeedMeleeIcon
        elif not self.gun:
            self.gunIcon = None
        else:
            self.gunIcon = self.gun.imageKillFeed

            name = self.gun.name
            register_gun_kill(name)

        assist = None
        if getattr(self.killed, "flashedBy", None):
            if self.killed.flashedBy is not self.killer:
                assist = self.killed.flashedBy
        
        if self.killer:
            t1 = self.app.font.render(self.killer.name, True, killer.teamColor)
        else:
            t1 = self.app.font.render("", True, [0,0,0])
            self.gunIcon = self.app.skullKillFeed
        t2 = self.app.font.render(self.killed.name, True, killed.teamColor)

        if assist:

            plus_surf = self.app.font.render("+", True, (255, 255, 255))


            t_assist = self.app.font.render(assist.name, True, assist.teamColor)
            flash_icon = self.app.flashKillFeed

            w = (
                t1.get_width()
                + plus_surf.get_width()
                + flash_icon.get_width()
                + t_assist.get_width()
                + self.gunIcon.get_width()
                + t2.get_width()
                + 55
            )
        else:
            if self.gunIcon:
                w = t1.get_width() + self.gunIcon.get_width() + t2.get_width() + 30
            else:
                w = t1.get_width() + t2.get_width() + 25

        h = max(t1.get_height(), t2.get_height()) + 10
        self.surface = pygame.Surface((w, h))
        self.surface.fill(self.color)

        x = 5
        self.surface.blit(t1, (x, 5))
        x += t1.get_width() + 5

        if assist:

            self.surface.blit(plus_surf, (x, h // 2 - plus_surf.get_height() // 2))
            x += plus_surf.get_width() + 5

            self.surface.blit(flash_icon, (x, h // 2 - flash_icon.get_height() // 2))
            x += flash_icon.get_width() + 5
            

            self.surface.blit(t_assist, (x, 5))
            x += t_assist.get_width() + 10

        if self.gunIcon:
            self.surface.blit(
                self.gunIcon,
                (x, h // 2 - self.gunIcon.get_height() // 2)
            )
            x += self.gunIcon.get_width() + 5

        self.surface.blit(t2, (x, 5))


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
