import pygame
import random
from pygame.math import Vector2 as v2
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game
    from pawn.pawn import Pawn


class Button:
    def __init__(self, app: "Game", shop, pos, size, team, weapon = None):
        self.app = app
        self.rect = pygame.Rect(pos, size)
        self.weapon = weapon
        self.team = team
        self.shop = shop
        self.a = False
        self.weaponPos = v2(0,0)
        self.outOfStock = False

    def draw(self, surface, text="", font=None):
        pygame.draw.rect(surface, (100, 100, 100), self.rect)
       
        hitBox = self.rect.copy()
        hitBox.topleft = v2(self.rect.topleft) + self.shop.getDefPos()

        if hitBox.collidepoint(self.app.mouse_pos):
            w = 3
            if not self.a:
                self.app.clicks[0].stop()
                self.app.clicks[0].play()
            self.a = True
        else:
            w = 1
            self.a = False

        pygame.draw.rect(surface, self.app.getTeamColor(self.team), self.rect, width=w)

        if self.outOfStock:
            label = font.render("OSTETTU", True, (255, 0, 0))
            surface.blit(label, label.get_rect(center=self.rect.center))
            return

        if self.weapon:
            text = self.weapon.name
            text += ":"
            if self.weapon.price[0]:
                text += f" {self.weapon.price[0]} kaljaa"
                if self.weapon.price[1]:
                    text += " ja"

            if self.weapon.price[1]:
                text += f" {self.weapon.price[1]} shottia"

            if not self.weapon.price[0] and not self.weapon.price[1]:
                text += " Ilmainen :)"

            if self.app.weaponButtonClicked == self:
                self.weaponPos = self.weaponPos * 0.9 + v2(self.app.mouse_pos) * 0.1
            else:
                self.weaponPos = v2(hitBox.center)
                surface.blit(self.weapon.shopIcon, v2(self.rect.center) - [self.weapon.shopIcon.get_width()/2, self.weapon.shopIcon.get_height()/2])
                

        if text and font:
            label = font.render(text, True, (255, 255, 255))
            surface.blit(label, label.get_rect(center=self.rect.center))

        if self.a and "mouse0" in self.app.keypress:
            self.app.clicks[1].stop()
            self.app.clicks[1].play()
            return True
        return False


class Shop:
    def __init__(self, app: "Game", team):
        self.app = app
        self.team = team
        self.hideI = 0.5

        self.totalPrice = [0, 0]

        self.surf = pygame.Surface((self.app.res[0], 500), pygame.SRCALPHA).convert_alpha()


        self.weapon_slots = []

        weapons = []
        rates = []
        for w in self.app.weapons:
            
            price = w.price[0] + w.price[1]
            if price == 0:
                continue
            rates.append(price)
            weapons.append(w)

        maxRate = max(rates) * 1.05
        for i in range(len(rates)):
            origRate = rates[i]
            rates[i] = (maxRate - origRate)
        
        for i in range(3):
            pos = (20, 80 + i * 120)
            w = weapons[self.app.randomWeighted(*rates)]
            size = w.shopIcon.get_size()
            size = (600, 110)
            self.weapon_slots.append(Button(app, self, pos, size, self.team, weapon = w))

        self.item_buttons = []
        for i in range(4):
            pos = (self.app.res[0] - 220, 20 + i * 60)
            size = (200, 40)
            self.item_buttons.append(Button(app, self, pos, size, self.team))

        self.readyButton = Button(app, self, [self.app.res[0]-310, 370], [300,120], self.team)

    def getDefPos(self):
        return (0, self.app.res[1] - 500 + 800*self.app.mapTime(self.hideI, 0.5, inverse=False)**2)

    def draw(self):
        self.surf.fill((30, 30, 30, 180))  # RGBA: translucent gray
        pygame.draw.line(self.surf, self.app.getTeamColor(self.team), (0,0), (self.surf.get_width(), 0), width=2)

        self.hideI -= self.app.deltaTime
        self.hideI = max(0, self.hideI)


        t = self.app.fontLarge.render("Weapon stock:", True, [255,255,255])
        self.surf.blit(t, (20, 4))


        for i, btn in enumerate(self.weapon_slots):
            if btn.draw(self.surf, f"Weapon {i+1}", self.app.font):
                if self.app.weaponButtonClicked == btn:
                    self.app.weaponButtonClicked = None
                else:
                    self.app.weaponButtonClicked = btn

        for i, btn in enumerate(self.item_buttons):
            btn.draw(self.surf, f"Item {i+1}", self.app.fontSmaller)


        price = f"Hinta:"
        if self.totalPrice[0]:
            price += f" {self.totalPrice[0]} kaljaa"

        if self.totalPrice[1]:
            price += f" {self.totalPrice[1]} shotti"

        if not self.totalPrice[0] and not self.totalPrice[1]:
            price += " Ei mitään :)"

        t = self.app.font.render(price, True, self.app.getTeamColor(self.team))

        self.surf.blit(t, [self.surf.get_width()/2 - t.get_width()/2, 5])


        a = self.readyButton.draw(self.surf, "READY!", self.app.fontLarge)

        self.app.screen.blit(self.surf, self.getDefPos(), special_flags=pygame.BLEND_PREMULTIPLIED)
        return a
    
    def autoBuyForTeam(self):
        pawns = [p for p in self.app.pawnHelpList if p.team == self.team and p.NPC]
        if not pawns:
            return

        available_weapons = [b.weapon for b in self.weapon_slots if not b.outOfStock]
        if not available_weapons:
            return

        weapon = random.choice(available_weapons)
        pawn = random.choice(pawns)

        weapon.give(pawn)


