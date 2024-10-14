from chiplet_actuary.module import Module, D2D
import chiplet_actuary.spec as spec
import math


class Chip():
    def __init__(self, name, node, modules: dict):
        self.name = name
        self.node = node
        self.modules: dict = modules
        self.area = 0
        for module, num in self.modules.items():
            self.area += module.area * num
        self.cost_factor = spec.Chip_NRE_Cost_Factor[self.node]
        self.fixed = spec.Chip_NRE_Cost_Fixed[self.node]
        self.knownNRE = 0

    def __hash__(self) -> int:
        return hash((self.name, self.node, self.area))

    def __eq__(self, other: object) -> bool:
        return isinstance(self, type(other)) and (self.name == other.name) and (
            self.node == other.node) and (self.area == other.area)

    def __str__(self):
        return '\n'.join(['%s:%s' % item for item in self.__dict__.items()])

    def setFactor(self, factor):
        self.cost_factor = factor

    def setFixed(self, fixed):
        self.cost_fixed = fixed

    def setNRE(self, n):
        self.knownNRE = n

    def NRE(self):
        '''
        Total NRE cost for chip design ()
        '''
        if (self.knownNRE != 0):
            return self.knownNRE
        else:
            return self.area * self.cost_factor + self.fixed

    def die_yield(self):
        return (1 + spec.Defect_Density_Die[self.node] / 100 * self.area / spec.critical_level)**(
            -spec.critical_level)

    def N_KGD(self):
        return self.N_die_total() * self.die_yield()

    def N_die_total(self):
        Area_chip = self.area + 2 * spec.scribe_lane * math.sqrt(self.area) + spec.scribe_lane**2
        N_total = math.pi * (spec.wafer_diameter / 2 - spec.edge_loss)**2 / Area_chip - math.pi * (
            spec.wafer_diameter - 2 * spec.edge_loss) / math.sqrt(2 * Area_chip)
        return N_total

    def cost_raw_die(self):
        return spec.Cost_Wafer_Die[self.node] / self.N_die_total()

    def cost_KGD(self):
        return spec.Cost_Wafer_Die[self.node] / self.N_KGD()

    def cost_defect(self):
        return self.cost_KGD() - self.cost_raw_die()

    def cost_RE(self):
        return (self.cost_raw_die(), self.cost_defect())


class Chiplet(Chip):
    def __init__(self, module: Module, D2DArea: float):
        self.D2DPHY = D2D('d2d_{}'.format(module.node), module.node)
        super().__init__(module.name + 'chiplet', module.node, {module: 1, self.D2DPHY: D2DArea})
        self.D2DArea = D2DArea


class dummy(Chip):
    def __init__(self, area: float):
        self.name = dummy
        self.area = area
        self.modules = {}

    def __hash__(self) -> int:
        return hash((self.name, self.area))

    def __eq__(self, other: object) -> bool:
        return isinstance(self, type(other)) and (self.name == other.name) and (self.area
                                                                                == other.area)

    def NRE(self):
        return 0

    def cost_raw_die(self):
        return 0

    def cost_KGD(self):
        return 0

    def cost_defect(self):
        return 0
