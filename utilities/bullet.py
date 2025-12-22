import pygame
import math
from pygame.math import Vector2 as v2
import random
from numba import njit
from particles.blood import BloodParticle
from levelGen.mapGen import CellType
from utilities.explosion import Explosion

@njit
def line_intersect(x1, y1, x2, y2, x3, y3, x4, y4):
        denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
        if denom == 0:
            return False
        ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / denom
        ub = ((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)) / denom
        return 0 <= ua <= 1 and 0 <= ub <= 1

@njit
def line_intersects_rect(x1, y1, x2, y2, rx, ry, rw, rh):
    # rectangle edges
    left   = (rx, ry, rx, ry + rh)
    right  = (rx + rw, ry, rx + rw, ry + rh)
    top    = (rx, ry, rx + rw, ry)
    bottom = (rx, ry + rh, rx + rw, ry + rh)

    return (
        line_intersect(x1, y1, x2, y2, *left) or
        line_intersect(x1, y1, x2, y2, *right) or
        line_intersect(x1, y1, x2, y2, *top) or
        line_intersect(x1, y1, x2, y2, *bottom)
    )


class Bullet:
    def __init__(self, weapon, pos, angle, spread = 0.1, damage = 10, rocket = False, type = "normal", piercing = False, homing = False, critChance = 0):
        self.weapon = weapon
        self.owner = weapon.owner
        self.app = self.owner.app
        self.pos = pos
        self.angle = angle + random.uniform(-spread, spread)
        self.speed = 6000
        self.damage = damage
        self.vel = v2(math.cos(self.angle), math.sin(self.angle))
        self.pastPos = []
        self.dodged = []
        self.app.ENTITIES.append(self)
        self.lifetime = 2
        if type == "normal":
            self.bOrig = self.app.bulletSprite.copy()
        else:
            self.bOrig = self.app.energySprite.copy()
        self.b = pygame.transform.rotate(self.bOrig, -math.degrees(self.angle))
        self.rocket = rocket
        self.type = type
        self.pos += self.vel * random.uniform(19,25)
        self.piercing = piercing
        self.homing = homing
        self.target = None
        
        self.turnRate = 3.0  # radians per second
        self.targetRefreshTimer = 0
        self.targetRefreshRate = 0.05  # seconds
        self.crit = random.uniform(0,1) < critChance
        if self.crit:
            self.damage *= 4

        self.app.roundInfo["bulletsFired"] += 1

    def getOwnCell(self):
        return self.v2ToTuple((self.pos + [0, self.app.tileSize/2]) / self.app.tileSize)
    
    def v2ToTuple(self, p):
        return (int(p[0]), int(p[1]))
    
    def findHomingTarget(self):
        if not self.homing:
            return None
        
        enemies = [x for x in self.app.pawnHelpList
                  if x != self.owner and self.owner.team.hostile(self.owner, x) and not x.killed]
        
        if not enemies:
            return None
            
        # Find closest enemy within reasonable range
        bestTarget = None
        minDistance = float('inf')
        maxRange = 2000
        
        for enemy in enemies:
            distance = self.pos.distance_to(enemy.pos)
            if distance < maxRange and distance < minDistance:
                # Check if we can reasonably turn towards this target
                toTarget = (enemy.pos - self.pos).normalize()
                dotProduct = self.vel.dot(toTarget)
                if dotProduct > -0.5:  # Don't target enemies too far behind
                    bestTarget = enemy
                    minDistance = distance
                    
        return bestTarget

    def tick(self):
        # Homing behavior

        self.ONSCREEN = self.app.onScreen(self.pos)

        if self.homing:
            self.targetRefreshTimer -= self.app.deltaTime
            if self.targetRefreshTimer <= 0 or (self.target and self.target.killed):
                self.target = self.findHomingTarget()
                self.targetRefreshTimer = self.targetRefreshRate
                
            if self.target and not self.target.killed:
                toTarget = (self.target.pos - self.pos)
                if toTarget.length() > 0:
                    toTarget = toTarget.normalize()
                    
                    # Calculate angle between current velocity and target direction
                    currentAngle = math.atan2(self.vel.y, self.vel.x)
                    targetAngle = math.atan2(toTarget.y, toTarget.x)
                    
                    # Calculate shortest rotation direction
                    angleDiff = targetAngle - currentAngle
                    while angleDiff > math.pi:
                        angleDiff -= 2 * math.pi
                    while angleDiff < -math.pi:
                        angleDiff += 2 * math.pi
                    
                    # Apply turning
                    maxTurn = self.turnRate * self.app.deltaTime
                    turnAmount = max(-maxTurn, min(maxTurn, angleDiff))
                    
                    newAngle = currentAngle + turnAmount
                    self.vel = v2(math.cos(newAngle), math.sin(newAngle))
                    self.angle = newAngle
                    if self.ONSCREEN:
                        self.b = pygame.transform.rotate(self.bOrig, -math.degrees(self.angle))

        self.pastPos.append(self.pos.copy())
        if len(self.pastPos) > 3:
            self.pastPos.pop(0)
        #self.pos += self.vel * self.app.deltaTime * self.speed
        nextPos = self.pos + self.vel * self.app.deltaTime * self.speed
        
        line = [list(self.pos), list(nextPos)]
        x,y = self.getOwnCell()

        direction = self.vel.normalize()
        move_dist = self.speed * self.app.deltaTime
        hit, normal = raycast_grid(
            nextPos,
            direction,
            move_dist / self.app.tileSize,
            self.app.map.grid,
            self.app.tileSize
        )

        if hit is not None:
            self.pos = hit

            # reflect direction
            reflected = direction - 2 * direction.dot(normal) * normal
            reflected_angle = math.atan2(-reflected.y, reflected.x)

            self.app.particle_system.create_wall_sparks(
                hit.x,
                hit.y,
                normal_angle=reflected_angle
            )

            if self.rocket:
                Explosion(self.app, self.pos, firer = self.weapon, damage = self.damage, doFire=True)

            self.app.ENTITIES.remove(self)
            return

        self.pos += self.vel * move_dist
        
        for x in self.app.pawnHelpList:
            if x == self:
                continue

            if x == self.owner:
                continue

            if x in self.dodged:
                continue

            if self.owner.itemEffects["allyProtection"] and self.owner.team == x.team:
                continue

            if x.killed:
                continue

            collides = line_intersects_rect(
                line[0][0], line[0][1],
                line[1][0], line[1][1],
                x.hitBox.x, x.hitBox.y, x.hitBox.width, x.hitBox.height
            )
            if collides:

                self.dodged.append(x)

                if random.uniform(0, 1) < x.itemEffects["dodgeChance"]:
                    x.say("Läheltä liippas!", 0.1)
                    continue

                if not self.piercing:
                    if self in self.app.ENTITIES:
                        self.app.ENTITIES.remove(self)

                self.app.bloodSplatters.append(BloodParticle(x.pos.copy(), 0.7, app = self.app))

                damage = self.damage 

                if self.rocket:
                    Explosion(self.app, self.pos, firer = self.weapon, damage = self.damage, doFire=True)
                else:
                    x.takeDamage(damage, fromActor = self.weapon, typeD = self.type, bloodAngle = self.angle) # TEST 
                
                #if x.onScreen():
                if self.crit:
                    self.app.playPositionalAudio("audio/crit.wav", self.pos)
                else:
                    self.app.playPositionalAudio(self.app.hitSounds, self.pos)
                    
                if not self.piercing:
                    return

        self.lifetime -= self.app.deltaTime
        if self.lifetime < 0:
            if self in self.app.ENTITIES:
                self.app.ENTITIES.remove(self)

    def render(self):
        if self.ONSCREEN:
            POS = self.app.convertPos(self.pos)
            self.app.DRAWTO.blit(self.b, POS - v2(self.b.get_size())/2)

def raycast_grid(pos, direction, max_dist, grid, tile_size):
    x0, y0 = pos.x / tile_size, pos.y / tile_size
    dx, dy = direction.x, direction.y

    map_x = int(x0)
    map_y = int(y0)

    step_x = 1 if dx > 0 else -1
    step_y = 1 if dy > 0 else -1

    t_delta_x = abs(1 / dx) if dx != 0 else float("inf")
    t_delta_y = abs(1 / dy) if dy != 0 else float("inf")

    next_x = map_x + (1 if dx > 0 else 0)
    next_y = map_y + (1 if dy > 0 else 0)

    t_max_x = (next_x - x0) / dx if dx != 0 else float("inf")
    t_max_y = (next_y - y0) / dy if dy != 0 else float("inf")

    t = 0.0
    hit_axis = None

    while t <= max_dist:
        if 0 <= map_x < grid.shape[1] and 0 <= map_y < grid.shape[0]:
            if grid[map_y, map_x] == CellType.WALL.value:
                hit_pos = pos + direction * (t * tile_size)
                hit_pos -= direction * 1.0

                if hit_axis == 'x':
                    normal = pygame.Vector2(-step_x, 0)
                else:
                    normal = pygame.Vector2(0, -step_y)

                return hit_pos, normal
        else:
            return None, None

        if t_max_x < t_max_y:
            map_x += step_x
            t = t_max_x
            t_max_x += t_delta_x
            hit_axis = 'x'
        else:
            map_y += step_y
            t = t_max_y
            t_max_y += t_delta_y
            hit_axis = 'y'

    return None, None

