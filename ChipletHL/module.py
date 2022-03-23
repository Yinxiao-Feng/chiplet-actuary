from . import spec


class Module():
    def __init__(self, name, node, area):
        self.name = name
        self.node = node
        self.area = area
        self.cost_factor = spec.Module_NRE_Cost_Factor[self.node]
        self.knownNRE = 0

    def __hash__(self) -> int:
        return hash((self.name, self.node, self.area))

    def __eq__(self, other: object) -> bool:
        return isinstance(self, type(other)) and (self.name == other.name) and (
            self.node == other.node) and (self.area == other.area)

    def __str__(self):
        return '\n'.join(['%s:%s' % item for item in self.__dict__.items()])

    def setNRE(self, n):
        self.knownNRE = n

    def setFactor(self, factor):
        self.cost_factor = factor

    def NRE(self):
        if (self.knownNRE != 0):
            return self.knownNRE
        else:
            return self.cost_factor * self.area


class D2D(Module):
    def __init__(self, name, node):
        super().__init__(name, node, 1)

    def NRE(self):
        if (self.knownNRE != 0):
            return self.knownNRE
        else:
            return self.cost_factor * 20  # default assumed as a 20 mm2 module
