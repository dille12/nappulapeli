
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
        "Muhaha!",
        "Hahaa!",
        "Jipii!",
        f"Menisit sinäkin {killedName} töihin.",
        f"{ownName} on paras!",
        "Vie vittuun nuo entiset tuosta.",
        "Vittu mun teki mieli ampua sut, saatana.",
        "One tappi.",
        "Yykeri!",
        "Kaakeri!",
        "Kookeri!",
        "JumanTSUIKKELI ku osuu!",
        "Ja TOSTA!",
        "Ilmanen",
        "Yritätsä ees?",
        "War is hell, bozo."

        
    ])


def onCameraLock(ownName):
    return random.choice([
        f"{ownName} panee",
        "Oottekos tällästä nähny?",
        f"Kattokaas TÄTÄ",
        "Hei kaikki!",
        f"{ownName} tässä heippa!",
        f"Antakaas mää näytän.",
        f"Vittuun mun tieltäni.",
        f"Löylyä lissää!",
        "Welcome to my youtube tutorial",
        "Ultraviolettimöses",
        "Heipulivei!",
        "Moikkuuuu!",
        "Maksakaa mökki sit ajoissa.",
        "We stay winning.",
        "Aksulla on herpes.",
        ":)",
        "Kamala darra",
        "Ruvetaas semisekoilee",
        "Ripuliseksiäää",
        "Mä kuristan kohta jonkun"

    ])


def babloBreak():
    return random.choice([
        "Oho!",
        "Mitä vittua?",
        "Perse kutiaa",
        "Kuka siellä?",
        "Mä haluisin kyllä kihloihin sepän pojan kanssa.",
        "Vituttaa",
        "Pitäskö sitä mennä ihan pöytään istuu?",
        "Onks kellää heittää akuuttii nippii",
        "Tää mun ase on kyl ihan vitun paska",
        "Maken pöytä belike ku monsteri loppuu",
        "Mikäs läski sieltä tulee.",
        "Joko saa ruveta ryyppää?"
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
        f"Ei kyl kiinnosta {killedName} vittuakaan."

    ])

def onOwnDamage():
    return random.choice([
        "Vittu mä oon pässi",
        "Hups",
        "Vittu on vaikee vehje",
        "No voi helvetti",
        "Vitun paska peli",
        "No voi sun saatana"
    ])

def onTeamDamage(perpertator):
    return random.choice([
        "Älä mua!",
        f"Nyt loppu {perpertator}",
        f"Kato mihi sohit {perpertator}",
        "Kuka siellä omia sohii?",
        f"Opettele ampuu {perpertator}",
        f"Raportoikaa {perpertator}!",


    ])

def onTarget():
    return random.choice([
        "Nyt sää kuolet!",
        "Otas TOSTA.",
        "Tuu TÄNNE",
        "Täältä pesee",
        "Naissoot tykkää kun ompi aseita",
        "RÄYYYH",
        "Noni",
        "KÄÄK",
        "Gulp",
        "Kukas toi on?",
        "Mää oon tän mapin seksikkäin jäpä.",
        "Katos tätä.",
        "Hurjaa!",
        "Nyt sää jäät",
        "Kattokaa! Servun paskin pelaaja!",

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
        "Aissaatana",
        "Sattuu!",
        "Vituttaa.",
        "Mitä vittua?",
        "Interesting.",
        "Lopeta!",
        "Voi veljet!",
        "Sattuu pippeliin!",
        "Tää muistetaan",
        "Kamalaa! Minua ammutaan!",
        "Hyi vittu!"
    ])