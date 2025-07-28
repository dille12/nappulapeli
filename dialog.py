
import random

def onKill(ownName, killedName):
    return random.choice([
        f"Haista {killedName} vittu.",
        "Homo.",
        "Tiäksää kuka sun isäntä on?",
        "Oo iha hiljaa vaan.",
        f"Turpa kiinni muhammatti. Mikä saatanan {killedName} painu nyt vittuun siitä.",
        f"Vituttais olla {killedName}.",
        f"{ownName} tuli taloon.",
        "Ja jää!",
        "Sweet dreams, perkeleen mulkku.",
    ])


def onDeath():
    return random.choice([
        "AI VITTU",
        "AAAAAAAAAAAAA",
        "Älä ny nappaa!",
        "Kitti ny vitusti",
        "RIP",
    ])

def onTarget():
    return random.choice([
        "Nyt sää kuolet!",
        "Otas TOSTA.",
        "Tuu TÄNNE",
        "Täältä pesee",
        "Naissoot tykkää kun ompi aseita",
        "Ookko pillua saana?",
        "Noni",

    ])
def onTakeDamage():
    return random.choice([
        "au!",
        "auts!",
        "AI",
        "OU",
        "VITTU",
        "Älä ny ammu!",
        "Hei, älä sylje!",
        "Aissaatana"
    ])