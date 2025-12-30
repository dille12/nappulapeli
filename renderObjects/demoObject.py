import random
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game
class DemoObject:

    _next_id = 0

    def __init__(self, *, demo_keys, id=None, **kwargs):
        super().__init__(**kwargs)
        if self.app.DO_DEMO:
            
            self.extractKeys = demo_keys
            self.lastState = {}
            self.log = {}
            if id:
                self.id = int(id)
            else:
                self.id = DemoObject._next_id
            self.app: Game
            DemoObject._next_id += 1

            self.app.demoObjectLookUp[self.id] = self

        #if not hasattr(self, "handleSprite"):

            
    def handleSprite(self):
        return
        

    def _playBackTick(self):
        if not self.app.DO_DEMO: return
        tick = self.app.demoTick
        ticks = self.app.DEMO["ticks"]

        if tick not in ticks:
            return

        obj = ticks[tick].get(self.id)
        if obj is None:
            return

        for key, value in obj.items():
            setattr(self, key, value)


    def _kill(self):
        if not self.app.DO_DEMO: return
        self.app.logDeletion(self.id)
        if self in self.app.demoObjects:
            self.app.demoObjects.remove(self)

        


    def logCreation(self, obj, args, kwargs):

        if not self.app.DO_DEMO: return

        if self.app.RECORDDEMO:
            self.app.logParticleEffect(obj, args, kwargs)



    def saveState(self):
        if not self.app.DO_DEMO: return
        if not self.app.RECORDDEMO: return

        tick = self.app.demoTick

        if tick in self.app.DEMO["ticks"] and self.id in self.app.DEMO["ticks"][tick]:
            return

        delta = {}

        for key in self.extractKeys:
            value = getattr(self, key)

            # snapshot mutable data

            if key not in self.lastState or self.lastState[key] != value:

                if hasattr(value, "copy"):
                    value = value.copy()

                delta[key] = value
                self.lastState[key] = value

        if delta:

            if tick not in self.app.DEMO["ticks"]:
                self.app.DEMO["ticks"][tick] = {}

            self.app.DEMO["ticks"][tick][self.id] = delta


            

