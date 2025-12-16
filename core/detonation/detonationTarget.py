from levelGen.numbaPathFinding import MovementType
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pawn.pawn import Pawn

    
def detonationTarget(self: "Pawn"):

    t = self.team.getGodTeam()
    site = t.plan.get("site")
    action = t.plan.get("currentAction")

    x, y = self.app.skull.cell
    grid = self.app.map.grid

    def route(pos, mtype):
        self.getRouteTo(endPosGrid=pos, movement_type=mtype)
        if not self.route:
            self.getRouteTo(endPosGrid=pos, movement_type=MovementType.GROUND)

    isCT = t.detonationTeam
    hasBomb = self.carryingSkull()
    bombPlanted = self.app.skull.planted
    bombDropped = self.app.objectiveCarriedBy is None and not bombPlanted

    # ======================
    # DEFEND
    # ======================
    if action == "defend":

        if bombPlanted:
            route(self.app.skull.cell,
                  MovementType.COUNTERTERRORIST if isCT else MovementType.TERRORIST)
            return

        if bombDropped and isCT:
            route(self.app.skull.cell, MovementType.COUNTERTERRORIST)
            return

        t.plan["currentAction"] = "prepare"
        return

    # ======================
    # PREPARE
    # ======================
    if action == "prepare":

        if not isCT and hasBomb:
            route(self.getAttackPosition(), MovementType.TERRORIST)
            return

        route(self.getAttackPosition(),
              MovementType.COUNTERTERRORIST if isCT else MovementType.TERRORIST)
        return

    # ======================
    # EXECUTE
    # ======================
    if action == "execute":

        if not site:
            return

        if not isCT:
            if hasBomb:
                if site.controlledByT():
                    route(site.plantingSite, MovementType.TERRORIST)
                else:
                    route(self.getAttackPosition(), MovementType.TERRORIST)
            else:
                route(site.room.randomCell(), MovementType.TERRORIST)

        else:
            route(site.room.randomCell(), MovementType.COUNTERTERRORIST)

        return
