
import random

def onKill(ownName, killedName: str):
    return random.choice([
        f"Haista {killedName} vittu.",
        "Homo.",
        f"Homo{killedName.lower()}",
        "Tiäksää kuka sun isäntä on?",
        "Oo iha hiljaa vaan.",
        f"Turpa kiinni muhammatti. Mikä saatanan {killedName} painu nyt vittuun siitä.",
        f"Vituttais olla {killedName}.",
        f"{ownName} tuli taloon.",
        "Ja jää!",
        "Sweet dreams, perkeleen mulkku.",
        "Hurraa!",
    ])


def onDeath():
    return random.choice([
        "AI VITTU",
        "AAAAAAAAAAAAA",
        "Älä nappaa!",
        "Kitti ny vitusti",
        "RIP",
    ])


def onTeamKill(killedName):
    return random.choice([
        "Oho.",
        f"Sori {killedName}",
        f"VÄISTÄ SAATANA {killedName}",
        f"Mun moka {killedName}",

    ])

def onOwnDamage():
    return random.choice([
        "Vittu mä oon pässi",
        "Hups",
        "Vittu on vaikee vehje",
        "No voi helvetti",
        "Vitun paska peli"
    ])

def onTeamDamage(perpertator):
    return random.choice([
        "Älä mua!",
        f"Nyt loppu {perpertator}",
        f"Kato mihi sohit {perpertator}",

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
        "KÄÄK",
        "Gulp",

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