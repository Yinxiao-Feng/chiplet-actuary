from typing import Tuple
import math
import pandas as pd
from chiplet_actuary import module
from chiplet_actuary import chip
from chiplet_actuary import package
from chiplet_actuary import utils
from chiplet_actuary import spec


def yield_area() -> pd.DataFrame:
    '''
    Yield-Area relation under different technology
    '''
    def square(x):
        return x**2

    def die_yield(area, defect_density, critical_level):
        return (1 + defect_density / 100 * area / critical_level)**(-critical_level)

    Areas = list(map(square, range(1, 31)))

    yield_sheet = pd.DataFrame({'Area': Areas})

    for i in spec.__nodes:
        y = list(
            map(die_yield, Areas, [spec.Defect_Density_Die[i]] * len(Areas),
                [spec.critical_level] * len(Areas)))
        yield_sheet['{:.2f}({}nm)'.format(spec.Defect_Density_Die[i], i)] = y

    y = list(
        map(die_yield, Areas, [spec.defect_density_rdl] * len(Areas),
            [spec.critical_level_rdl] * len(Areas)))
    yield_sheet['RDL'] = y
    y = list(
        map(die_yield, Areas, [spec.defect_density_si] * len(Areas),
            [spec.critical_level_si] * len(Areas)))
    yield_sheet['SI'] = y

    return yield_sheet.round(3)


def cost_per_area() -> pd.DataFrame:
    '''
    cost per area under different technology
    '''
    def square(x):
        return x**2

    def cost_per_area(area, defect_density, critical_level):
        die_yield = (1 + defect_density / 100 * area / critical_level)**(-critical_level)
        Area_chip = area + 2 * spec.scribe_lane * math.sqrt(area) + spec.scribe_lane**2
        N_total = math.pi * (spec.wafer_diameter / 2 - spec.edge_loss)**2 / Area_chip - math.pi * (
            spec.wafer_diameter - 2 * spec.edge_loss) / math.sqrt(2 * Area_chip)
        return math.pi * (spec.wafer_diameter / 2)**2 / (N_total * area) / die_yield

    Areas = list(map(square, range(1, 31)))

    cost_sheet = pd.DataFrame({'Area': Areas})

    for i in spec.__nodes:
        c = list(
            map(cost_per_area, Areas, [spec.Defect_Density_Die[i]] * len(Areas),
                [spec.critical_level] * len(Areas)))
        cost_sheet['{:.2f}({}nm)'.format(spec.Defect_Density_Die[i], i)] = c

    c = list(
        map(cost_per_area, Areas, [spec.defect_density_rdl] * len(Areas),
            [spec.critical_level_rdl] * len(Areas)))
    cost_sheet['RDL'] = c
    c = list(
        map(cost_per_area, Areas, [spec.defect_density_si] * len(Areas),
            [spec.critical_level_si] * len(Areas)))
    cost_sheet['SI'] = c

    return cost_sheet.round(3)


def single_system_NRE(num_chip: int, node: str, volume: int) -> pd.DataFrame:
    Areas = range(100, 1000, 100)

    nodes = [node] * len(Areas)

    def SoC_NRE_cost(node, area, packaging='OS'):
        if packaging == 'OS':
            soc = package.SoC('soc', node,
                              {module.Module('module', node, area / num_chip): num_chip}, 'OS')
        elif packaging == 'FO':
            soc = package.SoC('soc', node,
                              {module.Module('module', node, area / num_chip): num_chip}, 'FO')
        # return soc.total_NRE()
        return (utils.total_module_NRE({soc}) / volume, utils.total_chip_NRE({soc}) / volume,
                utils.total_package_NRE({soc}) / volume)

    def integration_NRE_cost(node, area, packaging='OS'):
        chips = {}
        m = module.Module('module', node, area / num_chip)
        c = chip.Chiplet(m, m.area / 10)
        chips[c] = num_chip
        if packaging == 'OS':
            integration = package.OS('intgration', chips)
        elif packaging == 'FO':
            integration = package.FO('intgration', chips)
        return (utils.total_module_NRE({integration}) / volume,
                utils.total_chip_NRE({integration}) / volume,
                utils.total_package_NRE({integration}) / volume)

    SoC_module_NRE, SoC_chip_NRE, SoC_package_NRE = zip(*list(map(SoC_NRE_cost, nodes, Areas)))
    integration_module_NRE, integration_chip_NRE, integration_package_NRE = zip(
        *list(map(integration_NRE_cost, nodes, Areas)))

    NRE_sheet = pd.DataFrame({'Area': Areas})
    NRE_sheet['SoC Module NRE'] = SoC_module_NRE
    NRE_sheet['SoC Chip NRE'] = SoC_chip_NRE
    NRE_sheet['SoC Package NRE'] = SoC_package_NRE
    NRE_sheet['2.5D Module NRE'] = integration_module_NRE
    NRE_sheet['2.5D Chip NRE'] = integration_chip_NRE
    NRE_sheet['2.5D Package NRE'] = integration_package_NRE

    return NRE_sheet.round(1)


def single_system_RE_cost(num_chip: int, node: str) -> pd.DataFrame:
    '''
    for single system, the RE(manufacturing) cost of SoC and 2.5D integration
    '''
    Areas = range(100, 1000, 100)

    nodes = [node] * len(Areas)

    def SoC_RE_cost(node, area) -> Tuple[float, float, float, float, float]:
        soc = package.SoC('soc', node, {module.Module('module', node, area): 1}, 'OS')
        return soc.cost_RE()

    def integration_RE_cost(node, area):
        chips = {}
        for i in range(num_chip):
            m = module.Module('module{}'.format(i), node, area / num_chip)
            c = chip.Chiplet(m, m.area * 0.1)
            chips[c] = 1
        os = package.OS('intgration', chips)
        fo = package.FO('intgration', chips, chip_last=1)
        si = package.SI('intgration', chips)
        return os.cost_RE() + fo.cost_RE() + si.cost_RE()

    src = list(map(SoC_RE_cost, nodes, Areas))
    irc = list(map(integration_RE_cost, nodes, Areas))

    soc0 = sum(src[0])

    RE_sheet = pd.DataFrame()
    for i in range(len(Areas)):
        RE_sheet = RE_sheet._append(
            pd.DataFrame.from_records([src[i], irc[i][0:5], irc[i][5:10], irc[i][10:15], ()],
                                      index=[[Areas[i]] * 5,
                                             ['SoC OS', '2.5D OS', '2.5D FO', '2.5D SI', '']],
                                      columns=[
                                          'raw chips', 'defect chips', 'raw package',
                                          'defect pacakge', 'wasted chips'
                                      ]).div(soc0 * Areas[i] / Areas[0]))
    return RE_sheet.round(3)


def single_system_total_cost(num_chip: int, node: str) -> pd.DataFrame:
    volumes = [500000, 2000000, 10000000]

    def total_cost(volume):
        m_soc = module.Module('module_soc', node, 800)
        c_soc = chip.Chip('chip_soc', node, {m_soc: 1})
        soc = package.OS('soc', {c_soc: 1})
        chips = {}
        for i in range(num_chip):
            m = module.Module('module{}'.format(i), node, 800 / num_chip)
            c = chip.Chiplet(m, m.area * 0.1)
            chips[c] = 1
        os = package.OS('integration', chips)
        fo = package.FO('integration', chips, chip_last=1)
        si = package.SI('integration', chips)
        soc_cost = (soc.cost_total_system(), m_soc.NRE() / volume, c_soc.NRE() / volume,
                    soc.NRE() / volume)
        os_cost = (os.cost_total_system(), ) + ((m.NRE() / volume, c.NRE() / volume) * num_chip) + (
            c.D2DPHY.NRE() / volume, os.NRE() / volume)
        fo_cost = (fo.cost_total_system(), ) + (m.NRE() / volume, c.NRE() / volume) * num_chip + (
            c.D2DPHY.NRE() / volume, fo.NRE() / volume)
        si_cost = (si.cost_total_system(), ) + (m.NRE() / volume, c.NRE() / volume) * num_chip + (
            c.D2DPHY.NRE() / volume, si.NRE() / volume)
        return soc_cost + os_cost + fo_cost + si_cost

    cost = list(map(total_cost, volumes))

    soc_cost_0 = cost[0][0]
    cost_sheet = pd.DataFrame()
    col = ['SoC_RE', 'SoC_module_NRE', 'SoC_chip_NRE', 'SoC_package_NRE'] \
        + ['OS_RE'] + ['MCM_module_NRE', 'MCM_chip_NRE']*num_chip + ['D2DPHY_NRE',
                                          'OS NRE']\
        + ['FO_RE'] + ['MCM_module_NRE', 'MCM_chip_NRE']*num_chip + ['D2DPHY_NRE',
                                          'FO NRE']\
        + ['SI_RE'] + ['MCM_module_NRE', 'MCM_chip_NRE']*num_chip + ['D2DPHY_NRE',
                                          'SI NRE']
    for i in range(len(volumes)):
        cost_sheet = cost_sheet._append(
            pd.DataFrame.from_records([cost[i]], index=[volumes[i]], columns=col).div(soc_cost_0))

    return cost_sheet.round(3)


def AMD_cost() -> pd.DataFrame:
    module_ccx_7 = module.Module('ccx', '7', 67)
    module_io_14 = module.Module('io_10', '14', 360)
    module_io_7 = module.Module('io_7', '7', 360)
    D2DIF_7 = module.D2D('link', '7')
    D2DIF_14 = module.D2D('link', '14')

    soc_chip_0 = chip.Chip('16core', '7', {module_ccx_7: 2, module_io_7: 1})
    soc_chip_1 = chip.Chip('24core', '7', {module_ccx_7: 3, module_io_7: 1})
    soc_chip_2 = chip.Chip('32core', '7', {module_ccx_7: 4, module_io_7: 1})
    soc_chip_3 = chip.Chip('48core', '7', {module_ccx_7: 6, module_io_7: 1})
    soc_chip_4 = chip.Chip('64core', '7', {module_ccx_7: 8, module_io_7: 1})

    chiplet_ccd = chip.Chip('ccd', '7', {module_ccx_7: 1, D2DIF_7: 7})
    chiplet_iod = chip.Chip('iod', '14', {module_io_14: 1, D2DIF_14: 56})
    dummmy = chip.dummy(67)

    SoC_0 = package.OS('16core', {soc_chip_0: 1})
    SoC_1 = package.OS('24core', {soc_chip_1: 1})
    SoC_2 = package.OS('32core', {soc_chip_2: 1})
    SoC_3 = package.OS('48core', {soc_chip_3: 1})
    SoC_4 = package.OS('64core', {soc_chip_4: 1})

    integration_0 = package.OS('16core', {chiplet_ccd: 2, chiplet_iod: 1, dummmy: 6})
    integration_1 = package.OS('24core', {chiplet_ccd: 3, chiplet_iod: 1, dummmy: 5})
    integration_2 = package.OS('32core', {chiplet_ccd: 4, chiplet_iod: 1, dummmy: 4})
    integration_3 = package.OS('48core', {chiplet_ccd: 6, chiplet_iod: 1, dummmy: 2})
    integration_4 = package.OS('64core', {chiplet_ccd: 8, chiplet_iod: 1})

    socs = [SoC_0, SoC_1, SoC_2, SoC_3, SoC_4]
    mcms = [integration_0, integration_1, integration_2, integration_3, integration_4]

    cost = []
    for i in range(len(socs)):
        soc = socs[i]
        mcm = mcms[i]
        cost.append(mcm.cost_RE()[0:2] + (mcm.cost_package(), ) + soc.cost_RE()[0:2] +
                    (soc.cost_package(), ))
    sum_mcm_dies_64 = sum(cost[4][0:2])

    cost_sheet = pd.DataFrame()

    cost_sheet = cost_sheet._append(pd.DataFrame().from_records(cost,
                                                               index=['16', '24', '32', '48', '64'],
                                                               columns=[
                                                                   'mcm raw chips',
                                                                   'mcm defect chips',
                                                                   'mcm packaging', 'soc raw chips',
                                                                   'soc defect chips',
                                                                   'soc packaging'
                                                               ]).div(sum_mcm_dies_64))
    return cost_sheet


def single_chiplet_multiple_systems(volume: int) -> pd.DataFrame:
    m = module.Module('module', '7', 200)
    chiplet = chip.Chiplet(m, m.area * 0.1)
    dummmy = chip.dummy(220)
    soc1 = package.SoC('soc1', '7', {m: 1})
    soc2 = package.SoC('soc2', '7', {m: 2})
    soc4 = package.SoC('soc4', '7', {m: 4})
    MCM1 = package.OS('integration1', {chiplet: 1})
    MCM2 = package.OS('integration2', {chiplet: 2})
    MCM4 = package.OS('integration4', {chiplet: 4})
    MCM_reuse1 = package.OS('reuse1', {chiplet: 1, dummmy: 3})
    MCM_reuse2 = package.OS('reuse2', {chiplet: 2, dummmy: 2})
    MCM_reuse4 = package.OS('reuse4', {chiplet: 4})
    si1 = package.SI('integration1', {chiplet: 1})
    si2 = package.SI('integration2', {chiplet: 2})
    si4 = package.SI('integration4', {chiplet: 4})
    si_reuse1 = package.SI('reuse1', {chiplet: 1, dummmy: 3})
    si_reuse2 = package.SI('reuse2', {chiplet: 2, dummmy: 2})
    si_reuse4 = package.SI('reuse4', {chiplet: 4})

    socs = [soc1, soc2, soc4]
    mcms = [MCM1, MCM2, MCM4]
    mcm_reuses = [MCM_reuse1, MCM_reuse2, MCM_reuse4]
    sis = [si1, si2, si4]
    si_reuses = [si_reuse1, si_reuse2, si_reuse4]

    volumes = [volume] * len(socs)
    soc_NRE = utils.system_total_apporitioned_NRE_cost(dict(zip(socs, volumes)))
    mcm_NRE = utils.system_total_apporitioned_NRE_cost(dict(zip(mcms, volumes)))
    mcm_reuse_NRE = utils.system_total_apporitioned_NRE_cost(dict(zip(mcm_reuses, volumes)))
    si_NRE = utils.system_total_apporitioned_NRE_cost(dict(zip(sis, volumes)))
    si_reuse_NRE = utils.system_total_apporitioned_NRE_cost(dict(zip(si_reuses, volumes)))

    cost = []
    for i in range(len(socs)):
        soc = socs[i]
        mcm = mcms[i]
        mcm_reuse = mcm_reuses[i]
        si = sis[i]
        si_reuse = si_reuses[i]

        cost.append(soc.cost_RE()[0:2] + (soc.cost_package(), ) + soc_NRE[soc] +
                    mcm.cost_RE()[0:2] + (mcm.cost_package(), ) + mcm_NRE[mcm] +
                    mcm_reuse.cost_RE()[0:2] + (mcm_reuse.cost_package(), ) +
                    mcm_reuse_NRE[mcm_reuse] + si.cost_RE()[0:2] + (si.cost_package(), ) +
                    si_NRE[si] + si_reuse.cost_RE()[0:2] + (si_reuse.cost_package(), ) +
                    si_reuse_NRE[si_reuse])

    sum_mcm = sum(cost[2][6:9])

    cost_sheet = pd.DataFrame()

    cost_sheet = cost_sheet._append(pd.DataFrame().from_records(
        cost,
        index=['1', '2', '4'],
        columns=[
            'soc raw chips', 'soc defect chips', 'soc packaging', 'soc module NRE', 'soc chip NRE',
            'soc package NRE', 'mc raw chips', 'mc defect chips', 'mc packaging', 'mc module NRE',
            'mc chip NRE', 'mc package NRE', 'reuse raw chips', 'reuse defect chips',
            'reuse packaging', 'reuse module NRE', 'reuse chip NRE', 'reuse package NRE',
            'si raw chips', 'si defect chips', 'si packaging', 'si module NRE', 'si chip NRE',
            'si package NRE', 'reuse raw chips', 'reuse defect chips', 'reuse packaging',
            'reuse module NRE', 'reuse chip NRE', 'reuse package NRE'
        ]).div(sum_mcm))
    return cost_sheet


def one_center_multiple_extensions(volume: int) -> pd.DataFrame:
    m1 = module.Module('module1', '7', 180)
    m2 = module.Module('module2', '7', 180)
    center = module.Module('center', '7', 180)
    center_14 = module.Module('center', '14', 180)
    chiplet_center = chip.Chiplet(center, center.area * 0.1)
    chiplet_center_14 = chip.Chiplet(center_14, center.area * 0.1)
    chiplet1 = chip.Chiplet(m1, m1.area * 0.1)
    chiplet2 = chip.Chiplet(m2, m2.area * 0.1)
    dummmy = chip.dummy(198)
    soc0 = package.SoC('soc0', '7', {center: 1})
    soc1 = package.SoC('soc1', '7', {center: 1, m1: 1})
    soc2 = package.SoC('soc2', '7', {center: 1, m1: 1, m2: 1})
    soc4 = package.SoC('soc4', '7', {center: 1, m1: 2, m2: 2})
    mcm0 = package.OS('integration0', {chiplet_center: 1})
    mcm1 = package.OS('integration1', {chiplet_center: 1, chiplet1: 1})
    mcm2 = package.OS('integration2', {chiplet_center: 1, chiplet1: 1, chiplet2: 1})
    mcm4 = package.OS('integration4', {chiplet_center: 1, chiplet1: 2, chiplet2: 2})
    reuse0 = package.OS('reuse0', {chiplet_center: 1, dummmy: 4})
    reuse1 = package.OS('reuse1', {chiplet_center: 1, chiplet1: 1, dummmy: 3})
    reuse2 = package.OS('reuse2', {chiplet_center: 1, chiplet1: 1, chiplet2: 1, dummmy: 2})
    reuse4 = package.OS('reuse4', {chiplet_center: 1, chiplet1: 2, chiplet2: 2})
    reuse_hete0 = package.OS('reuse0', {chiplet_center_14: 1, dummmy: 4})
    reuse_hete1 = package.OS('reuse1', {chiplet_center_14: 1, chiplet1: 1, dummmy: 3})
    reuse_hete2 = package.OS('reuse2', {chiplet_center_14: 1, chiplet1: 1, chiplet2: 1, dummmy: 2})
    reuse_hete4 = package.OS('reuse4', {chiplet_center_14: 1, chiplet1: 2, chiplet2: 2})

    socs = [soc0, soc1, soc2, soc4]
    mcms = [mcm0, mcm1, mcm2, mcm4]
    reuses = [reuse0, reuse1, reuse2, reuse4]
    reuse_hetes = [reuse_hete0, reuse_hete1, reuse_hete2, reuse_hete4]

    volumes = [volume] * len(socs)
    soc_NRE = utils.system_total_apporitioned_NRE_cost(dict(zip(socs, volumes)))
    mcm_NRE = utils.system_total_apporitioned_NRE_cost(dict(zip(mcms, volumes)))
    reuse_NRE = utils.system_total_apporitioned_NRE_cost(dict(zip(reuses, volumes)))
    reuse_hete_NRE = utils.system_total_apporitioned_NRE_cost(dict(zip(reuse_hetes, volumes)))

    cost = []
    for i in range(len(socs)):
        soc = socs[i]
        mcm = mcms[i]
        reuse = reuses[i]
        reuse_hete = reuse_hetes[i]

        cost.append(soc.cost_RE()[0:2] + (soc.cost_package(), ) + soc_NRE[soc] +
                    mcm.cost_RE()[0:2] + (mcm.cost_package(), ) + mcm_NRE[mcm] +
                    reuse.cost_RE()[0:2] + (reuse.cost_package(), ) + reuse_NRE[reuse] +
                    reuse_hete.cost_RE()[0:2] + (reuse.cost_package(), ) +
                    reuse_hete_NRE[reuse_hete])

    sum_mcm = sum(cost[3][6:9])

    cost_sheet = pd.DataFrame()

    cost_sheet = cost_sheet._append(pd.DataFrame().from_records(
        cost,
        index=['0', '1', '2', '4'],
        columns=[
            'soc raw chips', 'soc defect chips', 'soc packaging', 'soc module NRE', 'soc chip NRE',
            'soc package NRE', 'mc raw chips', 'mc defect chips', 'mc packaging', 'mc module NRE',
            'mc chip NRE', 'mc package NRE', 'reuse raw chips', 'reuse defect chips',
            'reuse packaging', 'reuse module NRE', 'reuse chip NRE', 'reuse package NRE',
            'hete raw chips', 'hete defect chips', 'hete packaging', 'hete module NRE',
            'hete chip NRE', 'hete package NRE'
        ]).div(sum_mcm))
    return cost_sheet


def a_few_sockets_multiple_collocations(volume: int) -> pd.DataFrame:
    m = module.Module('module', '7', 200)
    d2d = module.D2D('D2D', '7')
    c = chip.Chiplet(m, m.area * 0.1)

    soc_2 = chip.Chip('soc2', '7', {m: 2})
    soc_3 = chip.Chip('soc3', '7', {m: 3})
    soc_4 = chip.Chip('soc4', '7', {m: 4})

    p_OS_2 = package.OS('package_2', {c: 2})
    p_OS_3 = package.OS('package_3', {c: 3})
    p_OS_4 = package.OS('package_4', {c: 4})

    p_SI_2 = package.SI('package_2', {c: 2})
    p_SI_3 = package.SI('package_3', {c: 3})
    p_SI_4 = package.SI('package_4', {c: 4})

    SoC_2 = package.SoC('SOC', '7', {m: 2})
    SoC_3 = package.SoC('SOC', '7', {m: 3})
    SoC_4 = package.SoC('SOC', '7', {m: 4})
    '''
    (k,n)
    (2,2)
    (2,4)
    (3,4)
    (4,4)
    (4,6)
    '''

    sys_num = [3, 5, 20, 35, 126]
    module_reuse = [3, 5, 15, 35, 84]
    k = [2, 2, 3, 4, 4]
    n = [2, 4, 4, 4, 6]

    soc_NRE = [soc_2.NRE(), soc_2.NRE(), soc_3.NRE(), soc_4.NRE(), soc_4.NRE()]
    SoC_RE = [
        SoC_2.cost_total_system(),
        SoC_2.cost_total_system(),
        SoC_3.cost_total_system(),
        SoC_4.cost_total_system(),
        SoC_4.cost_total_system()
    ]
    SoC_NRE = [SoC_2.NRE(), SoC_2.NRE(), SoC_3.NRE(), SoC_4.NRE(), SoC_4.NRE()]

    OS_RE = [
        p_OS_2.cost_total_system(),
        p_OS_2.cost_total_system(),
        p_OS_3.cost_total_system(),
        p_OS_4.cost_total_system(),
        p_OS_4.cost_total_system()
    ]
    OS_NRE = [p_OS_2.NRE(), p_OS_2.NRE(), p_OS_3.NRE(), p_OS_4.NRE(), p_OS_4.NRE()]

    SI_RE = [
        p_SI_2.cost_total_system(),
        p_SI_2.cost_total_system(),
        p_SI_3.cost_total_system(),
        p_SI_4.cost_total_system(),
        p_SI_4.cost_total_system()
    ]
    SI_NRE = [p_SI_2.NRE(), p_SI_2.NRE(), p_SI_3.NRE(), p_SI_4.NRE(), p_SI_4.NRE()]

    cost = []
    for i in range(5):
        cost_soc = (SoC_RE[i], m.NRE() * k[i] / module_reuse[i] / volume, soc_NRE[i] / volume,
                    SoC_NRE[i] / volume)
        cost_os = (OS_RE[i], (m.NRE() * k[i] / module_reuse[i] + d2d.NRE() / sys_num[i]) / volume,
                   c.NRE() * k[i] / module_reuse[i] / volume, OS_NRE[i] / sys_num[i] / volume)
        cost_si = (SI_RE[i], (m.NRE() * k[i] / module_reuse[i] + d2d.NRE() / sys_num[i]) / volume,
                   c.NRE() * k[i] / module_reuse[i] / volume, SI_NRE[i] / sys_num[i] / volume)
        cost.append(cost_soc + cost_os + cost_si)

    sum_mcm = cost[4][4]

    cost_sheet = pd.DataFrame()

    cost_sheet = cost_sheet._append(pd.DataFrame().from_records(
        cost,
        index=['1', '2', '3', '4', '5'],
        columns=[
            'soc RE', 'soc module NRE', 'soc chip NRE', 'soc package NRE', 'OS RE', 'OS module NRE',
            'OS chip NRE', 'OS package NRE', 'SI RE', 'SI module NRE', 'SI chip NRE',
            'SI package NRE'
        ]).div(sum_mcm))
    return cost_sheet
