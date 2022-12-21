from ChipletHL.chip import Chip
from ChipletHL.module import Module
from typing import Tuple, Dict
from . import spec
import math


class Package():
    def __init__(self, name, chips: dict):
        self.name = name
        self.chips: dict = chips

    def __hash__(self) -> int:
        return hash((self.name, self.area(), type(self)))

    def __eq__(self, other: object) -> bool:
        return isinstance(self, type(other)) and (self.name == other.name) and (self.area()
                                                                                == other.area())

    def __str__(self):
        return '\n'.join(['%s:%s' % item for item in self.__dict__.items()])

    def chip_num(self):
        num = 0
        for n in self.chips.values():
            num += n
        return num

    def total_module_area(self):
        '''
        Total area of all modules
        '''
        area = 0
        for chip, num in self.chips.items():
            area += chip.area * num
        return area

    def interposer_area(self):
        '''
        Interposer area:
        OS: None
        FO: RDL Layer
        SI: Silicon Interposer
        '''
        pass

    def area(self):
        '''
        Total area of the package (Organic Substrate)
        '''
        pass

    def NRE(self):
        '''
        NRE cost of Package other than chips and modules
        '''
        pass

    def module_count(self, module: Module):
        '''
        Count the total number of modules that are included
        '''
        count = 0
        for chip, num in self.chips.items():
            if module in chip.modules:
                count += chip.modules[module] * num
        return count

    def cost_raw_package(self):
        '''
        Cost of package without considering yield
        '''
        pass

    def cost_chips(self):
        pass

    def cost_package(self):
        pass

    def cost_RE(self) -> Tuple[float, float, float, float, float]:
        '''
        (RE_raw_chips, RE_defect_chips, RE_raw_package, RE_defect_pacakge, RE_wasted_KGD)
        '''
        pass

    def cost_total_system(self):
        return self.cost_chips() + self.cost_package()


class OS(Package):
    def __init__(self, name, chips):
        super().__init__(name, chips)

    def interposer_area(self):
        raise AttributeError("there is no interposer in organic substrate package")

    def area(self):
        return self.total_module_area() * spec.os_area_scale_factor

    def NRE(self):
        if sum(self.chips.values()) == 1:
            factor = 1
        # more layer substrates are used for interconnection
        elif self.area() > 30 * 30:  # Large package
            factor = 2
        elif self.area() > 17 * 17:
            factor = 1.75
        else:
            factor = 1.5
        return self.area() * spec.os_NRE_cost_factor * factor + spec.os_NRE_cost_fixed

    def cost_raw_package(self):
        if sum(self.chips.values()) == 1:
            factor = 1
        # more layer substrates are used for interconnection
        elif self.area() > 30 * 30:  # Large package
            factor = 2
        elif self.area() > 17 * 17:
            factor = 1.75
        else:
            factor = 1.5
        return self.area() * spec.cost_factor_os * factor

    def cost_RE(self):
        cost_raw_chips = 0
        cost_defect_chips = 0
        for chip, num in self.chips.items():
            cost_raw_chips += (chip.cost_raw_die() + chip.area * spec.c4_bump_cost_factor) * num
            cost_defect_chips += chip.cost_defect() * num
        cost_defect_package = self.cost_raw_package() * (1 /
                                                         (spec.bonding_yield_os**self.chip_num()) -
                                                         1)
        cost_wasted_chips = (cost_raw_chips +
                             cost_defect_chips) * (1 / (spec.bonding_yield_os**self.chip_num()) - 1)
        return (cost_raw_chips, cost_defect_chips, self.cost_raw_package(), cost_defect_package,
                cost_wasted_chips)

    def cost_chips(self):
        return sum(self.cost_RE()[0:2])

    def cost_package(self):
        return sum(self.cost_RE()[2:5])

    def cost_total_system(self):
        return sum(self.cost_RE())


class Advanced(Package):
    def __init__(self,
                 name: str,
                 chips: Dict[Chip, int],
                 NRE_cost_factor: float,
                 NRE_cost_fixed: float,
                 wafer_cost: float,
                 defect_density: float,
                 critical_level: int,
                 bonding_yield: float,
                 area_scale_factor: float,
                 chip_last=1):
        super().__init__(name, chips)
        self.NRE_cost_factor = NRE_cost_factor
        self.NRE_cost_fixed = NRE_cost_fixed
        self.wafer_cost = wafer_cost
        self.defect_density = defect_density
        self.critical_level = critical_level
        self.bonding_yield = bonding_yield
        self.area_scale_factor = area_scale_factor
        self.chip_last = chip_last

    def interposer_area(self):
        return self.total_module_area() * self.area_scale_factor

    def area(self):
        return self.interposer_area() * spec.os_area_scale_factor

    def NRE(self):
        return self.interposer_area() * self.NRE_cost_factor + self.NRE_cost_fixed + self.area(
        ) * spec.cost_factor_os

    def package_yield(self):
        return (1 + self.defect_density / 100 * self.interposer_area() / self.critical_level)**(
            -self.critical_level)

    def N_package_total(self):
        area = self.interposer_area() + 2 * spec.scribe_lane * math.sqrt(
            self.interposer_area()) + spec.scribe_lane**2
        N_total_package = math.pi * (
            spec.wafer_diameter / 2 - spec.edge_loss)**2 / area - math.pi * (
                spec.wafer_diameter - 2 * spec.edge_loss) / math.sqrt(2 * area)
        return N_total_package

    def cost_interposer(self):
        return self.wafer_cost / self.N_package_total() + self.interposer_area(
        ) * spec.c4_bump_cost_factor

    def cost_substrate(self):
        return self.area() * spec.cost_factor_os

    def cost_raw_package(self):
        return self.cost_interposer() + self.cost_substrate()

    def cost_RE(self):
        cost_raw_chips = 0
        cost_defect_chips = 0
        for chip, num in self.chips.items():
            cost_raw_chips += chip.cost_raw_die() * num + chip.area * spec.u_bump_cost_factor
            cost_defect_chips += chip.cost_defect() * num
        y1 = self.package_yield()
        y2 = self.bonding_yield**self.chip_num()
        y3 = spec.bonding_yield_os
        if self.chip_last == 1:
            cost_defect_package = self.cost_interposer() * (1 / (y1 * y2 * y3) - 1) \
                + self.cost_substrate() * (1 / y3 - 1)
            cost_wasted_chips = (cost_raw_chips + cost_defect_chips) * (1 / (y2 * y3) - 1)

        elif self.chip_last == 0:
            cost_defect_package = self.cost_interposer() * (1 / (y1 * y3) - 1) \
                + self.cost_substrate() * (1 / y3 - 1)
            cost_wasted_chips = (cost_raw_chips + cost_defect_chips) * (1 / (y1 * y3) - 1)

        return (cost_raw_chips, cost_defect_chips, self.cost_raw_package(), cost_defect_package,
                cost_wasted_chips)

    def cost_chips(self):
        return sum(self.cost_RE()[0:2])

    def cost_package(self):
        return sum(self.cost_RE()[2:5])


class FO(Advanced):
    def __init__(self, name, chips, chip_last=1):
        super().__init__(name, chips, spec.fo_NRE_cost_factor, spec.fo_NRE_cost_fixed,
                         spec.cost_wafer_rdl, spec.defect_density_rdl, spec.critical_level_rdl,
                         spec.bonding_yield_rdl, spec.rdl_area_scale_factor, chip_last)


class SI(Advanced):
    def __init__(self, name, chips):
        super().__init__(name, chips, spec.si_NRE_cost_factor, spec.si_NRE_cost_fixed,
                         spec.cost_wafer_si, spec.defect_density_si, spec.critical_level_si,
                         spec.bonding_yield_si, spec.si_area_scale_factor, 1)


def SoC(name, node, modules: dict, package='OS'):
    chip = Chip(name, node, modules)
    if package == 'OS':
        system = OS(name, {chip: 1})
    elif package == 'FO':
        system = FO(name, {chip: 1}, chip_last=1)
    elif package == 'SI':
        system = SI(name, {chip: 1})
    return system
