from levelGen.mapGen import Room
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game
import random
from levelGen.numbaPathFinding import MovementType
class Site:
    def __init__(self, app: "Game", room: Room):
        self.room = room
        self.app = app
        self.inhabited = [0,0]
        self.alive = True

        self.plantingSite = self.room.randomCell()

    def processSite(self):

        ctStartPos = self.app.allTeams[0].getDetonationSpawnRoom().randomCell()
        tStartPos = self.app.allTeams[-1].getDetonationSpawnRoom().randomCell()

        self.visibilityCT = self.getVis(ctStartPos)
        self.visibilityT = self.getVis(tStartPos)
        #print("Site visibility:", self.visibilityCT)

        for x,y in self.visibilityCT:

            if self.app.map.grid[y,x] == 4:
                continue

            if self.app.map.grid[y,x] == 3:
                self.app.map.grid[y,x] = 4
            else:
                self.app.map.grid[y,x] = 2

        for x,y in self.visibilityT:

            if self.app.map.grid[y,x] == 4:
                continue

            if self.app.map.grid[y,x] == 2:
                self.app.map.grid[y,x] = 4
            else:
                self.app.map.grid[y,x] = 3

    
    def makePositions(self):

        ctStartPos = self.app.allTeams[0].getDetonationSpawnRoom().randomCell()
        tStartPos = self.app.allTeams[-1].getDetonationSpawnRoom().randomCell()

        self.attackPositionsT = self.getAttackPositions(self.visibilityCT, tStartPos, num_cells=15, movementType = MovementType.TERRORIST)
        self.attackPositionsCT = self.getAttackPositions(self.visibilityT, ctStartPos, num_cells=15, movementType= MovementType.COUNTERTERRORIST)
        print("CT:", len(self.attackPositionsCT), "T", len(self.attackPositionsT))

    def getVis(self, routeFrom):
        cells = self.room.allCells()
        vis = set()
        get_vis = self.app.map.get_visible_cells


        #ctStartPos = self.app.allTeams[0].getDetonationSpawnRoom().center()
        route = self.app.arena.pathfinder.find_path(routeFrom, self.room.randomCell())

        cells += route

        for x, y in cells:
            for cx, cy in get_vis(x, y, 15):
                vis.add((int(cx), int(cy)))

        return list(vis)
    
    def getInflatedCells(self, vis, inflation=6):
        inflated_cells = set()

        for x, y in self.room.allCells():
            for dx in range(-inflation, inflation + 1):
                for dy in range(-inflation, inflation + 1):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.app.map.grid.shape[1] and 0 <= ny < self.app.map.grid.shape[0]:
                        if (nx, ny) not in vis:
                            inflated_cells.add((nx, ny))

        return list(inflated_cells)
    
    def get_two_hop_connected_cells(self):
        visited = set()
        cells = []

        # 1-hop rooms
        first = self.room.connections

        # 2-hop rooms
        second = set()
        for r in first:
            for rr in r.connections:
                if rr is not self.room:
                    second.add(rr)

        # collect cells
        for r in list(first) + list(second):
            for c in r.allCells():
                if c not in visited:
                    visited.add(c)
                    cells.append(c)

        return cells

    
    def getAttackPositions(self, vis, routeFrom, num_cells=50, movementType = MovementType.GROUND):
        all_cells = self.get_two_hop_connected_cells()

        #if len(all_cells) <= num_cells:
        #    return all_cells
        random.shuffle(all_cells)
        possible = []
        for pos in all_cells:

            forbidden = [0, 4]
            if movementType == MovementType.COUNTERTERRORIST:
                forbidden += [3]
            elif movementType == MovementType.TERRORIST:
                forbidden += [2]

            if self.app.map.grid[pos[1], pos[0]] in forbidden:
                continue
            
            #print("Checking route with movement type", movementType)
            route = self.app.arena.pathfinder.find_path(routeFrom, pos, movement_type=movementType, verbose= False)
            if route:
                #print("Route added.", route)
                possible.append(pos)
                if len(possible) > num_cells:
                    break

        return possible

    def tickSite(self):
        inhabited = [0,0]
        for x in self.app.pawnHelpList:
            dx, dy = x.getOwnCell()
            if self.room.contains(dx, dy):
                inhabited[x.team.getDetI()] += 1

        if inhabited[0] or inhabited[1]:
            self.inhabited = inhabited

    def controlledByT(self):
        return self.inhabited[0] > self.inhabited[1]
