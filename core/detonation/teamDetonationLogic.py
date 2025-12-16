
from levelGen.numbaPathFinding import MovementType
from typing import TYPE_CHECKING
import random
if TYPE_CHECKING:
    from pawn.teamLogic import Team


def resetTeamRoutes(self: "Team"):
    self.app.log("Resetting team routes")
    for x in self.getPawns():
        x.pickWalkingTarget()


def tickDetonationLogic(self: "Team"):

    # ======================
    # ROUND STATE (INPUTS)
    # ======================
    SITES = self.app.allTeams[-1].plan["viableSites"]
    if not SITES:
        return

    self.refreshCarrier()
    self.tryToDefuse()

    dt = self.app.deltaTime
    plan = self.plan
    skull = self.app.skull

    isCT = self.getDetI()
    bombPlanted = skull.planted
    bombPlantedAt = skull.plantedAt
    bombDropped = self.app.objectiveCarriedBy is None and not bombPlanted

    terroristsHoldPlanSite = self.terroristsHoldPlanSite()
    bombDroppedAtEnemyTerritory = self.bombInEnemyTerritory()

    # ======================
    # READY SIGNALS
    # ======================

    pawns = self.getDetonationPawns()

    if not isCT:
        # Terrorists:
        # everyone ready except bomb carrier (or dead)
        ready = all(
            p.attackInPosition() or p.isBombCarrier() or p.killed
            for p in pawns
        )
    else:
        # Counter-terrorists:
        # everyone ready (or dead)
        ready = all(
            p.attackInPosition() or p.killed
            for p in pawns
        )



    # ======================
    # SANITY
    # ======================
    if plan["site"] not in self.app.SITES:
        plan["site"] = None

    if not plan["site"] and not isCT:
        plan["site"] = self.getClosestSite()

    # ======================
    # GLOBAL OVERRIDES
    # ======================
    #if bombPlanted:
    #    if isCT and terroristsHoldPlanSite:
    #        if plan["currentAction"] == "defend":
    #            plan["currentAction"] = "prepare" # Terrorist will only defend when bomb is down.
    #            plan["planTimer"] = 30
    #    else:
    #        plan["currentAction"] = "defend"
    #        plan["planTimer"] = 5



    if bombDropped:
        if bombDroppedAtEnemyTerritory:
            plan["currentAction"] = "defend"  # CTS try to defend dropped bomb in enemy territory and T:s attack it.
            return

    # ======================
    # TEAM SPLIT
    # ======================
    if not isCT:
        # ==================
        # TERRORIST SIDE
        # ==================

        if terroristsHoldPlanSite:
            plan["currentAction"] = "defend" # Terrorist will only defend when bomb is down.

        # ---------
        # DEFEND
        # ---------
        if plan["currentAction"] == "defend":
            if not bombPlanted and not terroristsHoldPlanSite:
                plan["currentAction"] = "prepare" # Terrorist will only defend when bomb is down.
                plan["planTimer"] = 30
                resetTeamRoutes(self)


        # ---------
        # PREPARE
        # ---------
        elif plan["currentAction"] == "prepare":
            plan["planTimer"] -= dt
            if plan["planTimer"] <= 0 or ready:
                plan["currentAction"] = "execute"
                plan["planTimer"] = 30
                resetTeamRoutes(self)

                if plan["site"]: 
                    for _ in range(5): 
                        self.addNadePos(plan["site"].room.randomCell())

        # ---------
        # EXECUTE
        # ---------
        elif plan["currentAction"] == "execute":
            plan["planTimer"] -= dt
            if terroristsHoldPlanSite:
                plan["currentAction"] = "defend" # Extra check. Make the terrorist hold the site.
                resetTeamRoutes(self)

            if plan["planTimer"] <= 0:
                plan["currentAction"] = "prepare" # Do another attack if fail to hold the site.
                plan["planTimer"] = 30
                resetTeamRoutes(self)

        else:
            pass

    else:
        # ==================
        # COUNTER-TERRORIST SIDE
        # ==================

        if not terroristsHoldPlanSite:
            plan["currentAction"] = "defend" # Terrorist will only defend when bomb is down.

        # ---------
        # DEFEND
        # ---------
        if plan["currentAction"] == "defend":
            
            if terroristsHoldPlanSite:
                plan["site"] = self.app.allTeams[-1].plan["site"]
                plan["currentAction"] = "prepare" # Do another attack if fail to hold the site.
                plan["planTimer"] = 30

        # ---------
        # PREPARE
        # ---------
        elif plan["currentAction"] == "prepare":
            plan["planTimer"] -= dt
            if plan["planTimer"] <= 0 or ready:
                plan["currentAction"] = "execute"
                plan["planTimer"] = 30

                if plan["site"]: 
                    for _ in range(5): 
                        self.addNadePos(plan["site"].room.randomCell())

        # ---------
        # EXECUTE
        # ---------
        elif plan["currentAction"] == "execute":
            plan["planTimer"] -= dt
            if not terroristsHoldPlanSite:
                plan["currentAction"] = "defend" # Extra check. Make the counterterrorist hold the site.

            if plan["planTimer"] <= 0:
                plan["currentAction"] = "prepare" # Do another attack if fail to hold the site.
                plan["planTimer"] = 30

        else:
            pass
