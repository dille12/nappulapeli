from utilities.item import Item
from renderObjects.pawn.getStat import effect_labels_fi

def getItems():
   

    def format_effects(effects):
        labels = []
        for attr, (op, amount) in effects.items():
            label = effect_labels_fi.get(attr, attr)
            prefix = None

            if op == "add":
                prefix = "+" if amount > 0 else "-" if amount < 0 else ""
            elif op == "mult":
                prefix = "+" if amount > 1 else "-" if amount < 1 else ""
            elif op == "set":
                if isinstance(amount, bool):
                    prefix = "+" if amount else "-"
                else:
                    prefix = "+"

            if prefix:
                labels.append(f"{prefix}{label}")
            else:
                labels.append(label)

        return " ".join(labels)

    def create_item(name, **effects):
        return Item(name, format_effects(effects), **effects)

    return [
        create_item("Timbsit", speedMod=["mult", 1.2]),
        create_item("Terveysjuoma", healthCapMult=["mult", 1.35]),
        create_item("Ylikellotus", weaponFireRate=["mult", 1.5]),
        create_item("Ase-ekspertti", weaponDamage=["mult", 1.4], weaponHandling=["mult", 1.25], weaponReload=["add", -0.25]),
        create_item("Berserker", berserker=["set", True]),
        create_item("God is king", saveChance=["add", 0.05]),
        create_item("Lasersääntö", allyProtection=["set", True]),
        #create_item("Pelkuri", coward=["set", True]),
        create_item("Kevut", defenceNormal=["mult", 2], defenceExplosion=["mult", 1.5]),
        create_item("Adrenaliiniruiske", instaHeal=["set", True]),
        create_item("Martyrdom", martyrdom=["set", True]),
        create_item("Masokismi", thorns=["add", 0.25], weaponFireRate=["add", 0.5], healthCapMult=["mult", 1.25]),
        create_item("Sadismi", lifeSteal=["add", 0.1], weaponDamage=["mult", 1.1], healthCapMult=["mult", 1.15]),
        create_item("Rage", fireRateIncrease=["add", 5]),
        create_item("Romupanssari", defenceNormal=["mult", 1.5], speedMod=["mult", 0.9]),
        create_item("Cryo-puku", defenceEnergy=["mult", 2], speedMod=["mult", 0.9]),
        #create_item("Kosto elää", revenge=["set", True]),
        create_item("Neurosynkronointi", weaponHandling=["mult", 1.6], weaponReload=["mult", 0.75]),
        create_item("Rumpulipas", weaponAmmoCap=["mult", 2.0], weaponFireRate=["mult", 0.8]),
        create_item("Adderall", weaponHandling=["mult", 2], speedMod=["mult", 1.1], weaponReload=["mult", 0.75], healthCapMult=["mult", 0.5]),
        create_item("Dodge Charger", dodgeChance=["add", 0.2], speedMod=["mult", 1.15]),
        create_item("Adrenaalimutageeni", healOnKill=["add", 25], healthCapMult=["mult", 0.8]),
        create_item("Sotasaalis", xpMult=["add", 0.5]),
        create_item("Liiketunnistin", weaponRange=["add", 0.5]),
        create_item("Ruostevaimennin", accuracy=["add", 0.25], weaponDamage=["mult", 1.25]),
        #create_item("Nanopehmuste", knockbackMult=["mult", 2], speedMod=["mult", 0.9]),
        create_item("Hemostim", healthRegenMult=["add", 0.25], instaHeal=["set", True]),
        create_item("Tukituli", weaponFireRate=["mult", 1.5], healthCapMult=["mult", 0.75]),
        create_item("Verenhimoprosessori", healOnKill=["add", 40], berserker=["set", True]),
        create_item("Ammuskompaktori", weaponAmmoCap=["mult", 3.0], weaponReload=["mult", 0.7]),
        create_item("Satelliittivalvonta", weaponRange=["add", 0.2], defenceNormal=["mult", 1.1]),
        create_item("Kelan työttömyysturva", xpMult=["mult", 2], weaponHandling=["mult", 0.5], speedMod=["mult", 0.85]),
        create_item("Lasikanuuna", weaponDamage=["mult", 2], healthCapMult=["mult", 0.5]),
        create_item("Tuplatusautus", multiShot=["add", 1]),
        create_item("Sleight of hand", weaponReload=["mult", 2]),
        create_item("Tulkutus", talking=["set", True], weaponReload=["mult", 1.25]),
        #create_item("Petturi", turnCoat=["set", True]),
        create_item("Sahattu Piippu", weaponDamage=["mult", 2], accuracy=["add", -0.25]),
        create_item("Silmälasit", accuracy=["add", 0.25], weaponHandling=["mult", 0.75]),
        create_item("Paholaisien munat", saveChance=["add", -0.1], healthCapMult=["mult", 0.8], speedMod=["add", 0.1], weaponDamage=["add", 0.25]),
        create_item("Virkalakki", hat=["set", True], defenceEnergy=["mult", 1.5], defenceNormal=["mult", 1.5], defenceExplosion=["mult", 1.5]),
        create_item("360", noscoping=["set", True], weaponDamage=["mult", 1.5], weaponHandling=["mult", 1.2]),
        create_item("Latexpuku", defenceEnergy=["mult", 1.4], speedMod=["mult", 0.9]),
        create_item("Pistin", meleeDamage=["add", 0.25], weaponHandling=["mult", 0.9]),
        create_item("Compressor", recoilMult=["mult", 2]),
        create_item("Flash hider", recoilMult=["mult", 1.5], weaponDamage=["add", 0.2]),
        create_item("Suppressori", recoilMult=["mult", 2], weaponDamage=["add", -0.1]),
        create_item("AP-Luodit", piercing=["set", True]),
        create_item("Litra mälliä", healthCapMult=["add", 0.5]),
        create_item("Rauhan uskonto", detonation=["set", True], defenceExplosion=["mult", 5]),
        create_item("Tankki", speedMod=["mult", 0.85], healthCapMult=["mult", 2]),
        create_item("Kivimies", tripChance=["add", 0.01], defenceNormal=["mult", 3], defenceEnergy=["mult", 3], defenceExplosion=["mult", 3]),
        create_item("Niken Nyssykkä", extraItem=["set", True]),
        create_item("Magneetti", homing=["set", True], weaponDamage=["mult", 0.75]),
        create_item("Paskahousu", shitChance=["add", 0.025], speedMod=["mult", 0.95], healthCapMult=["mult", 1.1]),
        create_item("Tuplaruuti", recoilMult=["mult", 0.75], weaponDamage=["mult", 1.5]),
        create_item("Mankka", playMusic=["set", True], dodgeChance=["add", 0.3]),
        create_item("Mersun merkki", speedMod=["mult", 1.25]),
        create_item("Taktinen juoksu", tacticalSprintSpeed=["mult", 1.3]),
        create_item("VAC", bossKiller=["set", True]),
        create_item("Joku bugi", timeScale=["add", 0.05]),
        create_item("Piri", timeScale=["add", 0.10]),
        create_item("Valoshow", utilityUsage=["add", 1]),
        create_item("Ransuexprertti", utilityUsage=["add", 1]),
        create_item("Keinosnipu", weaponDamage=["mult",1.5], weaponFireRate=["mult", 0.5], recoilMult=["mult", 0.75]),
        create_item("Dualwield", dualWield=["set", True]),
        create_item("Säästöpossu", currencyGain=["mult", 2.0]),
        create_item("Kelan eväät", currencyGain=["mult", 1.5]),
        create_item("Laaseri", lazer=["set", True], recoilMult=["mult", 1.25], accuracy=["add", 0.25]),
        #create_item("Mag dump", magDump=["set", True]),
    ]




itemEffects = {
    "speedMod": 1.0, # Done
    "healthRegenMult": 1.0,
    "thorns": 0.0,
    "healthCapMult": 1.0,
    "berserker" : False,
    "martyrdom" : False,

    "weaponHandling" : 1.0,
    "weaponDamage" : 1.0,
    "weaponReload" : 1.0,
    "weaponFireRate" : 1.0,
    "weaponAmmoCap" : 1.0,
    "weaponRange":1.0,
    "accuracy":1.0,

    "instaHeal" : False,
    "saveChance" : 0.0,
    "fireRateIncrease" : 0,
    "allyProtection" : False,
    "coward" : False,
    "revenge" : False,
    "duplicator" : False,

    "defenceNormal" : 1.0,
    "defenceEnergy" : 1.0,
    "defenceExplosion" : 1.0,

    "dodgeChance": 0.0,
    "xpMult":1.0,
    "healOnKill":0.0,
    "knockBackMult":1.0,
    "healAllies":0.0

}