import inspect
import pygame
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Game
import ast

def getCodeSuggestions(self: "Game"):
    self.object_methods = {
        name: str(inspect.signature(member))
        for name, member in inspect.getmembers(self, predicate=inspect.ismethod)
        if member.__self__.__class__ is self.__class__ and not name.startswith("__")
    }
    self.object_variables = {
        name: None
        for name in vars(self).keys()
        if not name.startswith("__") and not callable(getattr(self, name))
    }

    self.console_input = ""
    self.consoleOpen = False
    self.consoleSuggestionI = 0
    self.consoleLog = []
    self.lastCommands = []

def execute(self: "Game", command: str):


    command = "self." + command

    self.consoleLog.append(command)
    self.lastCommands.append(command)
    
    try:
        result = eval(command)
        if result is not None:
            self.consoleLog.append(str(result))
    except Exception as e:
        errorType = type(e).__name__
        print(command)
        t = f"{errorType}: {e}"
        self.consoleLog.append(t)
        print(t)


def handleConsoleEvent(self: "Game", event: pygame.event.Event):
    if not self.consoleOpen:
        return
    
    if event.type == pygame.KEYDOWN:

        if event.key in [pygame.K_TAB, pygame.K_LCTRL, pygame.K_RCTRL]:
            return

        if event.key == pygame.K_BACKSPACE:
            if "ctrl" in self.keypress_held_down:
                self.console_input = ""
            else:
                self.console_input = self.console_input[:-1]
        elif event.key == pygame.K_RETURN:
            if self.console_input.strip():
                execute(self, self.console_input)
                self.console_input = ""
        else:
            self.console_input += event.unicode


def runConsole(self: "Game"):
    if not self.consoleOpen:
        return
    
    rect = pygame.Rect(100, 100, 600, 400)
    panel = pygame.Surface(rect.size)
    font = pygame.font.SysFont("Consolas", 20)
    
    input_text = self.console_input
    
    inside_setValue = False
    partial_var = ""
    if input_text.startswith("setValue("):
        inside_setValue = True
        inner = input_text[9:]
        if '"' in inner:
            parts = inner.split('"')
            if len(parts) >= 2:
                partial_var = parts[1]
            else:
                partial_var = parts[0] if not inner.startswith('"') else ""
        else:
            partial_var = inner
    
    if inside_setValue:
        suggestions = [f'"{v}"' for v in self.object_variables.keys() if partial_var.lower() in v.lower()]
        suggestions = suggestions[:5]
    else:
        candidates = list(self.object_methods.keys()) + list(self.object_variables.keys())
        suggestions = [s for s in candidates if input_text.lower() in s.lower()] if input_text else []
        suggestions = suggestions[:5]
    
    panel.fill((20, 20, 20))
    text_surface = font.render("> " + input_text, True, (200, 200, 200))
    panel.blit(text_surface, (5, 5))

    for i, s in enumerate(self.consoleLog[-11:]):
        log_surface = font.render(s, True, (100, 100, 100) if s not in self.lastCommands else (150, 150, 255))
        panel.blit(log_surface, (5, 170 + i*20))

    if "up" in self.keypress:

        if not self.console_input and self.lastCommands:
            self.console_input = ".".join(self.lastCommands[-1].split(".")[1:])
        else:
            self.consoleSuggestionI -= 1
            if self.consoleSuggestionI < 0:
                self.consoleSuggestionI = len(suggestions) - 1

    elif "down" in self.keypress:
        self.consoleSuggestionI += 1
        if self.consoleSuggestionI >= len(suggestions):
            self.consoleSuggestionI = 0

    self.consoleSuggestionI = max(0, min(self.consoleSuggestionI, len(suggestions)-1))

    for i, s in enumerate(suggestions):
        if inside_setValue:
            sug_surface = font.render(s, True, (150, 255, 150), [40,40,40] if i != self.consoleSuggestionI else (80,80,80))
        else:
            f = s in self.object_methods
            sug_surface = font.render(s, True, (255,255,150) if f else (150, 150, 255), [40,40,40] if i != self.consoleSuggestionI else (80,80,80))
        panel.blit(sug_surface, (5, 30 + i*20))

    if "tab" in self.keypress and suggestions:
        suggestion = suggestions[self.consoleSuggestionI]
        if inside_setValue:
            self.console_input = "setValue(" + suggestion
        else:
            if suggestion in self.object_methods:
                if self.object_methods[suggestion] == "()":
                    self.console_input = suggestion + "()"
                else:
                    self.console_input = suggestion + "("
            else:
                self.console_input = suggestion

    funcName = input_text.split("(")[0]

    if funcName in self.object_methods:
        sig = self.object_methods[funcName]
        sig_surface = font.render(f"{funcName}{sig}", True, (200, 180, 100))
        panel.blit(sig_surface, (5, 150))
    
    self.screen.blit(panel, (100, 100))