
from levelGen.numbaPathFinding import MovementType
from typing import TYPE_CHECKING
import random
if TYPE_CHECKING:
    from pawn.teamLogic import Team

def tickDetonationLogic(self: "Team"):

    SITES = self.app.allTeams[-1].plan["viableSites"]
    if not SITES:
        return

    self.refreshCarrier()
    self.tryToDefuse()

    if self.plan["site"] not in self.app.SITES:
        self.plan["site"] = None

    if not self.plan["site"]:
        self.plan["site"] = random.choice(SITES)

    if self.getDetI(): # CT
        currHolding = not any(x.controlledByT() for x in self.app.SITES)
        if currHolding != self.plan["ctHolding"]:
            print("Switching ct plan!")

            #if not currHolding:
            self.plan["site"] = self.app.allTeams[-1].plan["site"]  

            self.plan["ctHolding"] = currHolding
            if not currHolding:
                print("Attacking site", self.plan["site"])
                self.plan["currentAction"] = "prepare"
                self.planTimer = 45
        if not currHolding:
            self.planTimer -= self.app.deltaTime
            if self.plan["currentAction"] == "probe":
                self.plan["currentAction"] = "prepare"
                self.planTimer = 45

            if self.plan["currentAction"] == "prepare":
                p = self.getDetonationPawns()
                l = [x.attackInPosition() for x in p]
                #l2 = [x.target for x in p]
                if all(l):
                    self.planTimer = 0

        else:
            self.plan["currentAction"] = "probe"
            self.planTimer = 30
                        

    else: # T
        currHolding = any(x.controlledByT() for x in self.app.SITES)
        if not currHolding:
            self.planTimer -= self.app.deltaTime

            if self.plan["currentAction"] == "prepare":
                p = self.getDetonationPawns()
                l = [x.attackInPosition() or x.isBombCarrier() for x in p]
                #l2 = [x.target for x in p]
                if all(l):
                    self.planTimer = 0
            
        else:
            self.plan["currentAction"] = "probe"
            self.planTimer = 5
            for x in self.app.SITES:
                if x.controlledByT():
                    self.plan["site"] = x
                    break

    
    if self.planTimer <= 0:
        if self.plan["currentAction"] == "probe":
            self.plan["currentAction"] = "prepare"
            self.planTimer = 45
            self.plan["site"] = random.choice(SITES)

            

        elif self.plan["currentAction"] == "prepare":
            self.plan["currentAction"] = "execute"

            if self.plan["site"]:
                for i in range(5):
                    self.addNadePos(self.plan["site"].room.randomCell())

            print("Grenade positions", self.utilityPos["aggr"])

            self.planTimer = 30
        elif self.plan["currentAction"] == "execute":
            self.plan["currentAction"] = "probe"
            self.planTimer = 30

        for x in self.app.pawnHelpList:
            if x.team.detonationTeam == self.detonationTeam:
                x.pickWalkingTarget()