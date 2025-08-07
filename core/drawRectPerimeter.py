import pygame

def draw_rect_perimeter(surface, rect: pygame.Rect, elapsed_time: float, speed: float, amountOfLines = 10, color = (255, 0, 0), width=2):

    perimeter = 2 * (rect.width + rect.height)

    for LINE in range(amountOfLines):

        startpos = (elapsed_time * speed + perimeter*LINE/amountOfLines) % perimeter
        length = min(perimeter / (amountOfLines*2), rect.width, rect.height)
        endpos = (startpos + length) % perimeter
        points = []
        sides = [0, 0]
        x, y = rect.topleft

        for i, p in enumerate((startpos, endpos)):

            # Calculate the position along the perimeter
            # Corners must be also included

            if 0 <= p < rect.width:
                points.append((x + p, y))
                sides[i] = 0  

            if rect.width <= p < rect.width + rect.height:
                points.append((x + rect.width, y + (p - rect.width)))
                sides[i] = 1


            if rect.width + rect.height <= p < 2 * rect.width + rect.height:
                points.append((x + rect.width - (p - (rect.width + rect.height)), y + rect.height))
                sides[i] = 2

            if 2 * rect.width + rect.height <= p < 2 * (rect.width + rect.height):
                points.append((x, y + rect.height - (p - (2 * rect.width + rect.height))))
                sides[i] = 3 
            
        if sides[0] != sides[1]:
            pointsToAppend = [rect.topleft, rect.topright, rect.bottomright, rect.bottomleft]
            points.insert(1, pointsToAppend[sides[1]])


        if len(points) >= 2:
            pygame.draw.lines(surface, color, False, points, width)
