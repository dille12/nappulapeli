
class infoBar:
    def __init__(self, app, text):
        self.app = app
        self.app.infobars.append(self)
        self.text = text
        self.xOffset = 0
        self.killed = False
        
    def tick(self):

        t = self.app.fontSmaller.render(self.text, True, [255,255,255])

        if not self.killed:
            self.xOffset += self.app.deltaTime
            self.xOffset = min(0.5, self.xOffset)
        else:
            self.xOffset -= self.app.deltaTime
            if self.xOffset <= 0:
                self.app.infobars.remove(self)
                return

        i = self.app.infobars.index(self)
        o = (self.xOffset*2)**0.5
        pos = [-t.get_width() + o * (t.get_width()+5), 100 + 40*i]
        self.app.screen.blit(t, pos)

