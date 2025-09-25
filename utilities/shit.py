from pygame.math import Vector2

class Shit:
    def __init__(self, app, cell, owner):
        self.app = app
        self.cell = cell
        self.pos = self.app.cell2Pos(cell)
        self.owner = owner

        self.app.shitGrid[cell[1], cell[0]] = 1

        self.image = self.app.shit
        self.app.shitDict[self.cell[0] * 200 + self.cell[1]] = self
        if self.app.onScreen(self.pos):
            self.app.shitSound.play()
    
    def tick(self):
        pass

    def render(self):
        self.app.DRAWTO.blit(self.image, self.pos - Vector2(self.image.get_size())/2 - self.app.cameraPosDelta)

    def kill(self):
        self.app.shitGrid[self.cell[1], self.cell[0]] = 0
        del self.app.shitDict[self.cell[0] * 200 + self.cell[1]]