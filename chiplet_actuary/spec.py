from configparser import ConfigParser

parameter_path = "parameter.ini"

param = ConfigParser()
param.read(parameter_path)

__nodes = ['3', '5', '7', '10', '14', '20', '28', '40', '55']

NRE_scale_factor_module = param.getfloat('NRE', 'module')
NRE_scale_factor_chip = param.getfloat('NRE', 'chip')

Cost_NRE: dict = {}
for node in __nodes:
    Cost_NRE[node] = param.getfloat(node, 'NRE')

Module_NRE_Cost_Factor: dict = {}
for node in __nodes:
    Module_NRE_Cost_Factor[node] = NRE_scale_factor_module * Cost_NRE[node] / 300

Chip_NRE_Cost_Factor: dict = {}
for node in __nodes:
    Chip_NRE_Cost_Factor[node] = NRE_scale_factor_chip * Cost_NRE[node] / 300

Chip_NRE_Cost_Fixed: dict = {}
for node in __nodes:
    Chip_NRE_Cost_Fixed[node] = (1 - NRE_scale_factor_module -
                                 NRE_scale_factor_chip) * Cost_NRE[node]

os_NRE_cost_factor = param.getfloat('OS', 'NRE_cost_factor')
os_NRE_cost_fixed = param.getfloat('OS', 'NRE_cost_fixed')

fo_NRE_cost_factor = 0.5 * param.getfloat('FO', 'NRE') / 300
fo_NRE_cost_fixed = 0.5 * param.getfloat('FO', 'NRE') / 300

si_NRE_cost_factor = Chip_NRE_Cost_Factor['55'] * 1.2
si_NRE_cost_fixed = Chip_NRE_Cost_Fixed['55'] * 1.2

wafer_diameter = param.getfloat('Manufacture', 'wafer_diameter')
scribe_lane = param.getfloat('Manufacture', 'scribe_lane')
edge_loss = param.getfloat('Manufacture', 'edge_loss')
critical_level = param.getfloat('Manufacture', 'critical_level')

Defect_Density_Die: dict = {}
for node in __nodes:
    Defect_Density_Die[node] = param.getfloat(node, 'defect_density')

defect_density_rdl = param.getfloat('FO', 'defect_density')
defect_density_si = param.getfloat('SI', 'defect_density')

Cost_Wafer_Die = {}
for node in __nodes:
    Cost_Wafer_Die[node] = param.getfloat(node, 'wafer_cost')

cost_factor_os = param.getfloat('OS', 'RE_cost_factor')
cost_wafer_rdl = param.getfloat('FO', 'wafer_cost')
cost_wafer_si = Cost_Wafer_Die['55']

c4_bump_cost_factor = param.getfloat('OS', 'bump_cost_factor')
u_bump_cost_factor = param.getfloat('SI', 'bump_cost_factor')

os_area_scale_factor = param.getfloat('OS', 'area_scale_factor')
rdl_area_scale_factor = param.getfloat('FO', 'area_scale_factor')
si_area_scale_factor = param.getfloat('SI', 'area_scale_factor')

critical_level_rdl = param.getfloat('FO', 'critical_level')
critical_level_si = param.getfloat('SI', 'critical_level')

bonding_yield_os = param.getfloat('OS', 'bonding_yield')
bonding_yield_rdl = param.getfloat('FO', 'bonding_yield')
bonding_yield_si = param.getfloat('SI', 'bonding_yield')
