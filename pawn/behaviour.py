from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game
    from pawn.pawn import Pawn
import random
import math
from pygame.math import Vector2 as v2
from levelGen.mapGen import CellType
from utilities.shit import Shit
from utilities.building import Building

import pygame

class PawnBehaviour:
    def __init__(self: "Pawn"):
        super().__init__()
        pass

    def think(self):
        self.thinkI += self.app.deltaTime

        self.thinkEvery = 0.1 if self.ULT else 0.5

        if self.thinkI >= self.thinkEvery:
            self.thinkI = 0
            # Do some thinking logic here, e.g., print a message or change state

            c = self.app.randomWeighted(0.2, 0.2, 0)
            if c == 0:
                if not self.target:
                    if not self.weapon.isReloading() and self.weapon.magazine < self.getMaxCapacity()/2 and not self.carryingSkull():
                        self.weapon.reload()

            if c == 1:
                if self.walkTo is None:
                    self.pickWalkingTarget()

            if c == 2:
                self.baseBuilding()
                if self.buildingTarget:
                    if self.pos.distance_to(self.buildingTarget.pos) > 150:
                        self.walkTo = self.buildingTarget.pos


    def baseBuilding(self):
        if self.app.PEACEFUL: return
        if self.buildingTarget: return
            
        t = self.getVisibility()
        tr = random.choice(t)
        b = Building(self.app, "TEST", self.team, "texture/energywell.png", tr, [1,1])
        self.buildingTarget = b



    def oddballWalkingTarget(self):
        if not self.app.objectiveCarriedBy:
            self.getRouteTo(endPosGrid=self.app.skull.cell) # RUN TOWARDS DROPPED SKULL
        else:
            if self.carryingSkull(): # CARRYING SKULL
                if not self.route: # Else go to spawn
                    self.getRouteTo(endPosGrid=self.getCellInSpawnRoom())
                #if len(self.route) > 6:
                #    self.route = self.route[0:5] # WALKS TOWARDS OWN SPAWN
            else:
                c = self.app.randomWeighted(0.5, 0.2)
                if c == 1 and self.skullCarriedByOwnTeam():
                    self.getRouteTo(endPosGrid=self.app.spawn_points[(self.team.i+1)%self.app.teams])
                    print("Attacking!")
                else:
                    
                    cells = self.app.objectiveCarriedBy.getVisibility() # ELSE WALK TOWARDS SKULL CARRIER VICINITY
                    self.getRouteTo(endPosGrid=random.choice(cells))

    def turfWarWalkingTarget(self):

        if self.app.teamSpawnRooms[self.team.i].turfWarTeam != self.team.i:
            self.getRouteTo(endPosGrid=self.app.teamSpawnRooms[self.team.i].randomCell())
            return
        
        if self.currentRoom:
            if self.currentRoom.turfWarTeam != self.team.i:
                self.getRouteTo(endPosGrid=self.currentRoom.randomCell())
                return
        
        preferableChoices = []
        choices = []
        for x in self.app.map.rooms:
            if x.turfWarTeam == self.team.i:
                for y in x.connections:
                    if y.turfWarTeam != self.team.i:
                        choices.append(y)
                        if x == self.currentRoom:
                            preferableChoices.append(y)
        
        if preferableChoices:
            g = random.choice(preferableChoices).randomCell()
            self.getRouteTo(endPosGrid=g)
            return
        
        if choices:
            g = random.choice(choices).randomCell()
            self.getRouteTo(endPosGrid=g)
            return

    def deathMatchWalkingTarget(self):
        self.getRouteTo(endPosGrid=self.app.commonRoom.randomCell()) # Just go to a random spawn point

    def shopWalkPos(self):
        if self.app.teamInspectIndex != -1:
            inspect_team = [p for p in self.app.pawnHelpList.copy() if p.team.i == self.app.teamInspectIndex]
            other_team = [p for p in self.app.pawnHelpList.copy() if p.team.i != self.app.teamInspectIndex]
            inspect_team.sort(key=lambda p: id(p))
            other_team.sort(key=lambda p: id(p))
            spacing = 250
            spacing2 = 100
            base_x = self.app.res[0]/2 + spacing/2
            base_x2 = self.app.res[0]/2 + spacing2/2
            base_y = 300
            offset_y = 600  # vertical gap between top and bottom lines
            if self.team.i == self.app.teamInspectIndex:
                index = inspect_team.index(self)
                total = len(inspect_team)
                x = base_x + (index - total / 2) * spacing
                y = base_y
            else:
                index = other_team.index(self)
                total = len(other_team)
                x = base_x2 + (index - total / 2) * spacing2
                y = base_y + offset_y + 70*(index%2)

            self.walkTo = [x, y]

    def judgeWalkPos(self):
        inspect_team = [p for p in self.app.pawnHelpList.copy() if p == self.app.podiumPawn]
        other_team = [p for p in self.app.pawnHelpList.copy() if p not in inspect_team]
        inspect_team.sort(key=lambda p: id(p))
        other_team.sort(key=lambda p: id(p))
        spacing = 250
        spacing2 = 100
        base_x = self.app.res[0]/2 + spacing/2
        base_x2 = self.app.res[0]/2 + spacing2/2
        base_y = 700
        offset_y = 200  # vertical gap between top and bottom lines
        if self not in other_team:
            index = inspect_team.index(self)
            total = len(inspect_team)
            x = base_x + (index - total / 2) * spacing
            y = base_y
        else:
            index = other_team.index(self)
            total = len(other_team)
            x = base_x2 + (index - total / 2) * spacing2
            y = base_y + offset_y + 70*(index%2)

        self.walkTo = [x, y]


    def pickWalkingTarget(self):

        if self.app.PEACEFUL:
            if self.app.pregametick == "shop" and self.app.teamInspectIndex != -1:
                self.shopWalkPos()
            elif self.app.pregametick == "judgement":
                self.judgeWalkPos()
            else:
                self.walkTo = v2(random.randint(0, 1920), random.randint(0, 1080))
            return

        if not self.target:
        #self.walkTo = v2(random.randint(0, 1920), random.randint(0, 1080))
            if self.revengeHunt():
                self.getRouteTo(endPosGrid=self.lastKiller.getOwnCell())
                self.say(f"Tuu tänne {self.lastKiller.name}!")
            else:
                if self.app.skull:
                    self.oddballWalkingTarget()
                elif self.app.GAMEMODE == "TURF WARS":
                    self.turfWarWalkingTarget()
                elif self.app.GAMEMODE == "TEAM DEATHMATCH":
                    self.deathMatchWalkingTarget()
                elif self.app.GAMEMODE == "1v1":
                    i = self.app.duelPawns.index(self)
                    endPos = self.app.duelPawns[(i+1)%2].getOwnCell()
                    self.getRouteTo(endPosGrid=endPos)
                else: # Random attack
                    self.getRouteTo(endPosGrid=self.app.spawn_points[(self.team.i+1)%self.app.teams])
        else:
            if self.carryingSkull(): # Go melee target
                self.getRouteTo(endPosGrid=self.target.getOwnCell())

            elif self.itemEffects["coward"] and self.health <= 0.5 * self.getHealthCap():
                self.say("APUA")
                self.getRouteTo(endPosGrid=self.app.spawn_points[self.team.i])

            else:
                CELLS = self.getVisibility()

                if self.app.skull and self.app.skull.cell in CELLS and not self.app.objectiveCarriedBy:
                    self.getRouteTo(endPosGrid=self.app.skull.cell)
                else:
                    CELLS_TARGET = self.target.getVisibility()
                    crossSection = list(set(CELLS) & set(CELLS_TARGET))
                    if crossSection:
                        self.getRouteTo(endPosGrid=random.choice(crossSection))
                    else:
                        self.getRouteTo(endPosGrid=random.choice(CELLS))

    def visualizeVis(self):
        CELLS = self.getVisibility()
        for x,y in CELLS:
            r = [x*self.app.tileSize - self.app.cameraPosDelta.x, y*self.app.tileSize - self.app.cameraPosDelta.y,
                self.app.tileSize, self.app.tileSize]
            print(r)
            pygame.draw.rect(self.app.DRAWTO, self.teamColor, r)

    def walkAcc(self):
        if self.walkTo is not None:
            if not self.target:
                self.facingRight = self.walkTo[0] <= self.pos[0]

            speed = self.getSpeed()

            # Component-wise acceleration
            diff = self.walkTo - self.pos
            gain = v2(
                self.app.smoothRotationFactor(self.vel.x, speed, diff.x),
                self.app.smoothRotationFactor(self.vel.y, speed, diff.y)
            )

            self.vel += gain * self.app.deltaTime

            # Cap velocity magnitude to avoid faster diagonals
            if self.vel.length_squared() > speed ** 2:
                self.vel.scale_to_length(speed)

            self.pos += self.vel * self.app.deltaTime

            # Step sound logic
            self.stepI += self.vel.length() * self.app.deltaTime / 300
            if self.lastStep != self.stepI // self.takeStepEvery:
                self.lastStep = self.stepI // self.takeStepEvery
                #if self.onScreen():
                self.app.playPositionalAudio(self.app.waddle, self.pos)

            # Arrival check
            if diff.length() < 1.5 and self.vel.length() < 5:
                if self.route:
                    self.advanceRoute()
                else:
                    self.walkTo = None
                    self.stepI = 0
                    self.vel *= 0

            # Path smoothing
            if self.route and len(self.route) > 5:
                c = self.getOwnCell()
                r1x, r1y = self.route[0]
                r2x, r2y = self.route[1]
                if self.app.map.can_see(c[0], c[1], r1x, r1y) and self.app.map.can_see(c[0], c[1], r2x, r2y):
                    self.advanceRoute()

        elif self.route:
            self.advanceRoute()

    def trip(self):
        self.tripped = True
        self.tripI = 0.0
        self.getUpI = 0
        self.tripRot = random.choice([-90, 90])
        self.say("Vittu kaaduin", 0.1)

        self.app.playPositionalAudio("audio/trip.wav", self.pos)

        #if self.onScreen():
        #    self.app.tripSound.stop()
        #    self.app.tripSound.play()
        self.target = None
        self.walkTo = None
        self.route = None


    def walk(self):
        if self.walkTo is not None:
            
            if not self.target:
                self.facingRight = self.walkTo[0] <= self.pos[0]

            direction = self.walkTo - self.pos
            if direction.length() > self.getSpeed() * self.app.deltaTime:
                direction = direction.normalize()
                #newPosX = self.pos[0] + direction.x * self.getSpeed() * self.app.deltaTime
                #newPosY = self.pos[1] + direction.y * self.getSpeed() * self.app.deltaTime

                ## Check if the new position causes collisions in both directions
                #c = self.getCell(v2(newPosX, self.pos[1]))
                #if not hasattr(self.app, "map") or self.app.map.grid[c[1], c[0]] != CellType.WALL.value:
                #    self.pos.x = newPosX

                #c = self.getCell(v2(self.pos[0], newPosY))
                #if not hasattr(self.app, "map") or self.app.map.grid[c[1], c[0]] != CellType.WALL.value:
                #    self.pos.y = newPosY

                self.pos += direction * self.getSpeed() * self.app.deltaTime
                self.stepI += self.app.deltaTime * self.getSpeed() / 300

                if self.lastStep != self.stepI // self.takeStepEvery:
                    self.lastStep = self.stepI // self.takeStepEvery
                    #if self.onScreen():
                    self.app.playPositionalAudio(self.app.waddle, self.pos)

                    if not self.app.PEACEFUL and random.uniform(0, 1) < self.itemEffects["shitChance"]:
                        self.say("Nyt tuli paskat housuun", 0.1)
                        cell = self.getOwnCell()
                        Shit(self.app, cell, self)

                    if random.uniform(0, 1) < self.itemEffects["tripChance"]:
                        self.trip()
                        
                
            else:
                if self.route:
                    self.advanceRoute()
                else:
                    self.walkTo = None
                    self.stepI = 0  # Reset step index when reaching the target

            if self.route and len(self.route) > 5:
                c = self.getOwnCell()
                r1x, r1y = self.route[0]
                r2x, r2y = self.route[1]

                if self.app.map.can_see(c[0], c[1], r1x, r1y) and self.app.map.can_see(c[0], c[1], r2x, r2y):
                    self.advanceRoute()

        elif self.route:
            self.advanceRoute()


    def shoot(self):

        if self.loseTargetI <= 0:
            if self.target:
                self.say("Karkas saatana", 0.1)
            self.target = None
            self.loseTargetI = 1

        
        if not self.target:
            self.searchEnemies()
        if not self.target:
            return
        
        if self.target.killed:
            self.target = None
            return
        dist = self.pos.distance_to(self.target.pos)
        if dist > self.getRange():
            self.loseTargetI -= self.app.deltaTime
            self.searchEnemies()
            return
        
        if not self.sees(self.target):
            self.loseTargetI -= self.app.deltaTime
            self.searchEnemies()
            return
        
        self.facingRight = self.target.pos[0] <= self.pos[0]
        if dist < 250:
            if self.carryingSkull():
                self.skullWeapon.tryToMelee()
            else:
                self.weapon.tryToMelee()
        elif self.carryingSkull(): # Cannot shoot with the skull!
            pass
        else:
            if self.itemEffects["magDump"]:
                for _ in range(self.weapon.magazine):
                    self.weapon.fireFunction(self.weapon)

            else:
                self.weapon.fireFunction(self.weapon)
        self.loseTargetI = 1