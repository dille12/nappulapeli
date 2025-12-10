

def getLyricTimes():
    everyFourBars = {
        
        2.5: "SEL",
        2.75: "SELLAI",
        3: "SELLAINEN",
        3.25: "SELLAINEN TÄÄ",
        3.5: "SELLAINEN TÄÄ MAA",
        4: "MAAA",
        4.25: "MAAAA",
        4.5: "MAAAAAAA",
        5: "MAAAAAAAA",
        5.25: "MAAAAAAAAA",
        5.5: "MAAAAAAAAAAAA",
        6: "MAAAAAAAAAAAAA",
        6.25: "MAAAAAAAAAAAAAA",
        6.5: "MAAAAAAAAAAAAAAAAA",
        7: "MAAAAAAAAAAAAAAAAAILMA",
        8: "ON",
        9: "",
    }

    first = {0: "AIKA",
             0.75: "HYVÄ",
             1.5: "MUTTA",
             2.5: "LEVO",
             4: "LEVOTON",
             5: ""
             }
    
    second = {0: "AINOASTAAN",
             1.5: "MINÄKÖ",
             2.5: "OON",
             2.75: "KOHTUU",
             4: "KOHTUUTON",
             5: ""
             }
    
    third = {0: "VÄLILLÄ",
             1: "TAIVAS",
             2: "ON",
             2.5: "SATEE",
             4: "SATEETON",
             5: ""}
    
    fourth = {
        0: "TAI",
        1: "TAIKA",
        1.5: "TAIKAKEI",
        2.5: "TAIKAKEINUI",
        3.9: "TAIKAKEINUILLA",
        5: ""
    }

    total = {}
    for i in range(4):
        for x in everyFourBars:
            total[convToTime(x + 16*i)] = everyFourBars[x]

    for x in first:
        total[convToTime(x + 3*4)] = first[x]

    for x in second:
        total[convToTime(x + 7*4)] = second[x]
    
    for x in third:
        total[convToTime(x + 11*4)] = third[x]

    for x in fourth:
        total[convToTime(x + 15*4)] = fourth[x]

    print(total)

    totalAsList = []
    for x in total:
        totalAsList.append([x, total[x]])
    
    totalAsList.sort(key=lambda x: x[0])

    print(totalAsList)
    return totalAsList


def convToTime(beat):
    t = beat * 60 / 125
    totalTime = 16*4*60 / 125
    t = t % totalTime
    return t

if __name__ == "__main__":
    getLyricTimes()