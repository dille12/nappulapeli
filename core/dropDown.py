import pygame
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game
class Dropdown:
    def __init__(self, app: "Game", title, choices, pos=(100, 100), width=200, height=45, initialValue=0):
        self.app = app
        self.choices = choices
        self.pos = (pos[0] * self.app.RENDER_SCALE, pos[1] * self.app.RENDER_SCALE)
        self.width = width * self.app.RENDER_SCALE
        self.height = height * self.app.RENDER_SCALE    
        self.selected_index = initialValue
        self.expanded = False
        self.font = self.app.fontSmaller
        self.bg_color = (60, 60, 60)
        self.hover_color = (80, 80, 80)
        self.text_color = (255, 255, 255)
        self.border_color = (255, 255, 255)
        self.title = title

    def tick(self):
        self.handle_event()
        self.draw()
    
    def draw(self):
        screen = self.app.screen
        x, y = self.pos

        
        # Draw main box
        pygame.draw.rect(screen, self.bg_color, (x, y, self.width, self.height))
        pygame.draw.rect(screen, self.border_color, (x, y, self.width, self.height), 2)
        text = self.font.render(self.choices[self.selected_index], True, self.text_color)
        screen.blit(text, (x + 5, y + 5))

        text = self.font.render(self.title, True, self.text_color)
        screen.blit(text, (x, y - self.height))

        
        # Draw dropdown choices
        if self.expanded:
            for i, choice in enumerate(self.choices):
                item_rect = pygame.Rect(x, y + (i+1)*self.height, self.width, self.height)
                mouse_pos = pygame.mouse.get_pos()
                is_hover = item_rect.collidepoint(mouse_pos)
                pygame.draw.rect(screen, self.hover_color if is_hover else self.bg_color, item_rect)
                pygame.draw.rect(screen, self.border_color, item_rect, 1)
                item_text = self.font.render(choice, True, self.text_color)
                screen.blit(item_text, (x + 5, y + 5 + (i+1)*self.height))

    def handle_event(self):
        x, y = self.pos
        mouse_x, mouse_y = self.app.mouse_pos

        if "mouse0" in self.app.keypress:
            main_rect = pygame.Rect(x, y, self.width, self.height)
            if main_rect.collidepoint((mouse_x, mouse_y)):
                self.expanded = not self.expanded
                self.app.clicks[1].stop()
                self.app.clicks[1].play()
            elif self.expanded:
                for i in range(len(self.choices)):
                    item_rect = pygame.Rect(x, y + (i+1)*self.height, self.width, self.height)
                    if item_rect.collidepoint((mouse_x, mouse_y)):
                        self.selected_index = i
                        self.expanded = False
                        self.app.clicks[1].stop()
                        self.app.clicks[1].play()
                        break
                else:
                    if self.expanded:
                        self.app.clicks[1].stop()
                        self.app.clicks[1].play()
                    self.expanded = False  # Clicked outside

    def get_selected(self):
        return self.choices[self.selected_index]
