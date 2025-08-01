class Item:
    def __init__(self, name, desc, **kwargs):
        # kwargs: key = effect name, value = (operation, amount)
        self.operations = []
        self.name = name
        self.desc = desc

        for attr, (op, amount) in kwargs.items():
            if op == "add":
                self.operations.append(lambda obj, a=attr, amt=amount: obj.itemEffects.__setitem__(a, obj.itemEffects[a] + amt))
            elif op == "mult":
                self.operations.append(lambda obj, a=attr, amt=amount: obj.itemEffects.__setitem__(a, obj.itemEffects[a] * amt))
            elif op == "set":
                self.operations.append(lambda obj, a=attr, amt=amount: obj.itemEffects.__setitem__(a, amt))

    def apply(self, to):
        for op in self.operations:
            op(to)

        to.pastItems.append(self.name)