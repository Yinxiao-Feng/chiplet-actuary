from chiplet_actuary.package import Package, OS, FO, SI
from chiplet_actuary.chip import Chip
from chiplet_actuary.module import Module
import math


def PHYarea(numberpin, pitch=0.055, depth=1) -> float:
    '''
    compute PHY area according to PIN number and pitch
    '''
    num_pad_depth = math.floor(depth / (pitch * math.sqrt(3) / 2))
    num_pad_width = math.ceil(numberpin / num_pad_depth)
    width = (num_pad_width + 1) * pitch
    return width * depth


def get_all_packages(Packages: set) -> set[Package]:
    package_set = set()
    for p in Packages:
        package_set.add(p)
    return package_set


def get_all_modules(Packages: set) -> set[Module]:
    '''
    return a set of all modules contained in all systems
    '''
    module_set: set = set()
    for p in Packages:
        for c in p.chips.keys():
            for m in c.modules.keys():
                module_set.add(m)
    return module_set


def get_all_chips(Packages: set) -> set[Chip]:
    '''
    return a set of all chips contained in all systems
    '''
    chip_set: set = set()
    for p in Packages:
        for c in p.chips.keys():
            chip_set.add(c)
    return chip_set


def total_module_NRE(Packages: set) -> float:
    '''
    return the total NRE cost of all systems for module design
    '''
    module_set: set[Module] = get_all_modules(Packages)
    Total_NRE = 0
    for m in module_set:
        Total_NRE += m.NRE()
    return Total_NRE


def total_chip_NRE(Packages: set) -> float:
    '''
    return the total NRE cost of all systems for chip design (except module design)
    '''
    chip_set: set[Chip] = get_all_chips(Packages)
    Total_NRE = 0
    for c in chip_set:
        Total_NRE += c.NRE()
    return Total_NRE


def total_package_NRE(Packages: set) -> float:
    '''
    return the total NRE cost of all systems for package design (except module and chip design)
    '''
    package_set = get_all_packages(Packages)
    Total_NRE = 0
    for p in package_set:
        Total_NRE += p.NRE()
    return Total_NRE


def total_NRE(Packages: set):
    '''
    return the total NRE cost of all systems
    '''
    return total_module_NRE(Packages) + total_chip_NRE(Packages) + total_package_NRE(Packages)


def module_amortized_unit_cost(m: Module, Packages: dict[Package, int]) -> float:
    '''
    return the amortized NRE cost of moudle m
    '''
    total_volume = 0
    for p, volume in Packages.items():
        total_volume += p.module_count(m) * volume
    return m.NRE() / total_volume


def chip_amortized_unit_cost(c: Chip, Packages: dict[Package, int]) -> float:
    '''
    return the amortized NRE cost of chip c
    '''
    total_volume = 0
    for p, volume in Packages.items():
        if c in p.chips:
            total_volume += p.chips[c] * volume
    return c.NRE() / total_volume


def package_amortized_unit_cost(p: Package, Packages: dict[Package, int]) -> float:
    '''
    return the amortized NRE cost of package p
    '''
    total_volume = 0
    for pp, volume in Packages.items():
        if p.area() == pp.area():
            total_volume += volume
    return p.NRE() / total_volume


def module_amortized_cost(Packages: dict[Package, int]) -> dict[Package, float]:
    '''
    return the amortized module NRE cost for each package
    '''
    cost: dict = {}
    for p in Packages.keys():
        cost[p] = 0
        for c, num in p.chips.keys():
            for m, num2 in c.modules.items():
                cost[p] += module_amortized_unit_cost(m, Packages) * num2 * num
    return cost


def chip_amortized_cost(Packages: dict[Package, int]) -> dict[Package, float]:
    '''
    return the amortized chip NRE cost for each package
    '''
    cost: dict = {}
    for p in Packages.keys():
        cost[p] = 0
        for c, num in p.chips.items():
            cost[p] += chip_amortized_unit_cost(c, Packages) * num
    return cost


def package_amortized_cost(Packages: dict[Package, int]) -> dict[Package, float]:
    '''
    return the amortized package NRE cost for each package
    '''
    cost: dict = {}
    for p in Packages.keys():
        cost[p] = package_amortized_unit_cost(p, Packages)
    return cost


def system_total_apporitioned_NRE_cost(Packages: dict[Package, int]) -> dict[Package, tuple[float]]:
    '''
    return the amortized total NRE cost for each package
    '''
    NRE_cost: dict = {}
    for p, sale_volume in Packages.items():
        package_NRE = package_amortized_unit_cost(p, Packages)
        chip_NRE = 0
        module_NRE = 0
        for c, num in p.chips.items():
            chip_NRE += chip_amortized_unit_cost(c, Packages) * num
            for m, num2 in c.modules.items():
                module_NRE += module_amortized_unit_cost(m, Packages) * num2 * num
        NRE_cost[p] = (module_NRE, chip_NRE, package_NRE)
    return NRE_cost


def info(p):
    if len(p.chips) > 1:
        system_type = "2.5D Intergration"
        print("Name: {}\n  Type: {}".format(p.name, system_type))

        i = 0
        for c, num in p.chips.items():
            print(
                "  chiplet_{:0>2d}: {:<10} node:{:>2}nm  area:{:>5.1f}mm2  Die cost: {:>5.1f}$ num: {}"
                .format(i, c.name, c.node, c.area, c.cost_KGD(), num))
            i += 1
    elif len(p.chips) == 1:  # len(package.chips) == 1
        system_type = "SoC"
        print("Name: {}\n Type: {}".format(p.name, system_type))
        i = 0
        for m, num in sorted(p.chips.keys())[0].modules.items():
            print("  module_{:0>2d}: {:<10}  node: {:>2}nm  area:{:>5.1f}mm2 num: {}".format(
                i, m.name, m.node, m.area, num))
            i += 1
        print("  Die Cost: {:.1f}$".format(sorted(p.chips.keys())[0].cost_KGD()))
    if type(p) == OS:
        print("  Organic Substrate Packaging (Chip-Last)")
    elif (type(p) == FO) & (p.chip_last == 1):
        print("  Integrated Fanout Packaging (Chip-Last)")
    elif (type(p) == FO) & (p.chip_last == 0):
        print("  Integrated Fanout Packaging (Chip-First)")
    elif type(p) == SI:
        print("  Silicon Interposer Packaging (Chip-First)")
    print("  Package Area: {:.1f}mm2".format(p.area()))
    print("  Cost of Raw package: {:.1f}$".format(p.cost_raw_package()))
    print("  Total Manufacturing Cost: {:.1f}$".format(p.cost_total_system()))
