from item import Item
def getItems():
    return [
        Item("Timberlands", speedMod=["mult", 1.5]),
        Item("Health potion", healthCapMult=["mult", 1.35]),
        Item("Overclock", weaponFireRate=["add", 1.0]),
        Item("Weapons expert", weaponDamage=["add", 1.4], weaponHandling=["add", 1.4], weaponReload=["mult", 3]),
        Item("Berserker", berserker=["set", True]),
        Item("God is king", saveChance=["add", 0.05]),
        Item("Trigger discipline", allyProtection=["set", True]),
        Item("Shitpants", coward=["set", True]),
        Item("Kevlar", defenceNormal=["mult", 0.5], defenceExplosion=["mult", 0.75]),
        # New Items
        Item("Adrenal Injector", instaHeal=["set", True]),
        Item("Martyrdom", martyrdom=["set", True]),
        Item("Masochism", thorns=["add", 0.25], weaponFireRate=["add", 0.5], healthCapMult=["mult", 1.25]),
        Item("Replicator", duplicator=["set", True]),
        Item("Rage", fireRateIncrease=["add", 5]),
        Item("Scrap Armor", defenceNormal=["mult", 0.7], speedMod=["mult", 0.85]),
        Item("Cryo Suit", defenceEnergy=["mult", 0.5], speedMod=["mult", 0.8]),
        Item("V is for Vendetta", revenge=["set", True]),
        Item("Neuro-Sync", weaponHandling=["mult", 1.6], weaponReload=["mult", 0.6]),
        Item("Overfed Battery", weaponAmmoCap=["mult", 2.0], weaponFireRate=["mult", 0.8]),
        # batch 3
        Item("Adderall", weaponHandling=["mult", 2], speedMod=["mult", 1.25], weaponReload=["mult", 0.75], healthCapMult = ["mult", 0.5]),
        Item("Dodgeball Shoes", dodgeChance=["add", 0.15], speedMod=["mult", 1.2]),
        Item("Adrenal Mutagen", healOnKill=["add", 25], healthCapMult=["mult", 0.8]),
        Item("War Trophy", xpMult=["mult", 2.0]),
        Item("Motion Scanner", weaponRange=["add", 0.25]),
        Item("Rusty Suppressor", accuracy=["mult", 3], weaponDamage=["mult", 1.25]),
        Item("Nanofoam Padding", knockbackMult=["mult", 0.5], speedMod=["mult", 0.9]),
        Item("Hemostim", healthRegenMult=["mult", 2.0], instaHeal=["set", True]),
        Item("Glitched Mirror", duplicator=["set", True], weaponFireRate=["mult", 1.5], healthCapMult=["mult", 0.5]),
        Item("Bloodthirst Processor", healOnKill=["add", 40], berserker=["set", True]),
        Item("Ammo Compactifier", weaponAmmoCap=["mult", 3.0], weaponReload=["mult", 0.7]),
        Item("Overhead Satellite", weaponRange=["add", 0.2], defenceNormal=["mult", 1.2]),
        Item("Kickstarter Backer", xpMult=["mult", 3.0], weaponHandling=["mult", 0.5], speedMod=["mult", 0.6]),
        Item("Glass Cannon", weaponDamage=["mult", 2], healthCapMult=["mult", 0.5])
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