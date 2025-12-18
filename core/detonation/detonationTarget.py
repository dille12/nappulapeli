from levelGen.numbaPathFinding import MovementType
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pawn.pawn import Pawn


def terroristSiteTarget(self: "Pawn"):

    hasBomb = self.carryingSkull()
    site = self.app.allTeams[-1].plan["site"]
    if hasBomb:
        self.getRouteTo(endPosGrid=site.plantingSite, movement_type=MovementType.GROUND)
    else:
        self.getRouteTo(endPosGrid=site.room.randomCell(), movement_type=MovementType.GROUND)




def detonationTarget(self: "Pawn"):

    # ======================
    # ROUND STATE (INPUTS)
    # ======================
    t = self.team.getGodTeam()
    site = self.app.allTeams[-1].plan["site"]
    action = t.plan.get("currentAction")

    skull = self.app.skull

    isCT = t.detonationTeam
    hasBomb = self.carryingSkull()
    bombPlanted = skull.planted
    bombDropped = self.app.objectiveCarriedBy is None and not bombPlanted

    terroristsHoldPlanSite = t.terroristsHoldPlanSite()
    bombDroppedAtEnemyTerritory = t.bombInEnemyTerritory()

    # ======================
    # GLOBAL OVERRIDES
    # ======================
    if bombPlanted:
        pass

    elif bombDropped:
        if self.isBombCarrier():
            self.getRouteTo(endPosGrid=skull.cell, movement_type=MovementType.GROUND)
            return


    # ======================
    # TEAM SPLIT
    # ======================
    if not isCT:
        # ==================
        # TERRORIST SIDE
        # ==================

        # ---------
        # DEFEND
        # ---------
        if action == "defend":
            if bombDroppedAtEnemyTerritory and not bombPlanted:
                self.getRouteTo(endPosGrid=skull.cell, movement_type=MovementType.GROUND) # Go to bomb
                return
            
            elif terroristsHoldPlanSite or bombPlanted:
                terroristSiteTarget(self)
                return

        # ---------
        # PREPARE
        # ---------
        elif action == "prepare":
            if not self.attackInPosition():
                pos = self.getAttackPosition()
                self.getRouteTo(endPosGrid=pos, movement_type=MovementType.TERRORIST)
                if not self.route:
                    self.getRouteTo(endPosGrid=pos, movement_type=MovementType.GROUND)
                return

        # ---------
        # EXECUTE
        # ---------
        elif action == "execute":
            if not hasBomb or (hasBomb and terroristsHoldPlanSite):  # Everyone except bomb carrier move, bomb carrier moves after site is held.
                terroristSiteTarget(self)
                return
            else:
                pos = self.getAttackPosition()
                self.getRouteTo(endPosGrid=pos, movement_type=MovementType.COUNTERTERRORIST)
                if not self.route:
                    self.getRouteTo(endPosGrid=pos, movement_type=MovementType.GROUND)
                return

        else:
            pass

    else:
        # ==================
        # COUNTER-TERRORIST SIDE
        # ==================

        # ---------
        # DEFEND
        # ---------
        if action == "defend":
            if bombDroppedAtEnemyTerritory and not bombPlanted:
                self.getRouteTo(endPosGrid=skull.cell, movement_type=MovementType.GROUND) # Go to bomb
                return
            
            elif bombPlanted and not terroristsHoldPlanSite: # CTs have retaken the site
                if not skull.defusedBy:
                    self.getRouteTo(endPosGrid=skull.cell, movement_type=MovementType.GROUND) # Go to bomb
                else:
                    self.getRouteTo(endPosGrid=skull.plantedAt.room.randomCell(), movement_type=MovementType.GROUND) # Go to bomb

            elif not terroristsHoldPlanSite:
                
                ownSite = self.team.getSite(self)
                if ownSite:
                    self.getRouteTo(endPosGrid=ownSite.room.randomCell(), movement_type=MovementType.GROUND)
                    return
                else:
                    self.app.log("No site ??")

        # ---------
        # PREPARE
        # ---------
        elif action == "prepare":
            if not self.attackInPosition():
                pos = self.getAttackPosition()
                self.getRouteTo(endPosGrid=pos, movement_type=MovementType.COUNTERTERRORIST)
                if not self.route:
                    self.getRouteTo(endPosGrid=pos, movement_type=MovementType.GROUND)
                return

        # ---------
        # EXECUTE
        # ---------
        elif action == "execute":
            self.getRouteTo(endPosGrid=site.room.randomCell(), movement_type=MovementType.GROUND)
            return

        else:
            pass


    
def detonationTargetArchive(self: "Pawn"):

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
            route(self.app.skull.plantedAt.room.randomCell(),
                  MovementType.GROUND)
            return

        if bombDropped and isCT:
            route(self.app.skull.cell, MovementType.COUNTERTERRORIST)
            return
        
        if not isCT:
            route(site.room.randomCell(), MovementType.GROUND)

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
