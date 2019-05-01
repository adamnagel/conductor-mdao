from __future__ import print_function
from conductor.ConductorWorker import ConductorWorker
from conductor.conductor import MetadataClient, WorkflowClient
import json
import requests
import math
from time import sleep
from openmdao.api import Component

from om_hover_power import HoverPower


class TestThing(Component):
    def __init__(self):
        super(TestThing, self).__init__()

        self.add_param('Param1', val=0.5, units='m')
        self.add_param('a_string', val='default', pass_by_obj=True)
        self.add_output('Output1', val=0.0)
        self.add_output('a_string_twice', val='', pass_by_obj=True)

    def solve_nonlinear(self, params, unknowns, resids):
        sleep(0.5)
        unknowns['Output1'] = params['Param1'] + 2
        unknowns['a_string_twice'] = params['a_string'] * 2


components = dict()
interface_descriptions = dict()


def Add(component, component_id):
    ipd = component._init_params_dict
    iud = component._init_unknowns_dict
    interface_description = {'Parameters': dict(), 'Unknowns': dict()}
    for k, v in ipd.items():
        interface_description['Parameters'][k] = v

    for k, v in iud.items():
        interface_description['Unknowns'][k] = v

    interface_descriptions[component_id] = interface_description
    components[component_id] = component
    print(json.dumps(interface_descriptions, indent=2))


def define_as_task(component):
    ipd = component._init_params_dict
    iud = component._init_unknowns_dict
    interface_description = {'Parameters': dict(), 'Unknowns': dict()}
    for k, v in ipd.items():
        interface_description['Parameters'][k] = v

    for k, v in iud.items():
        interface_description['Unknowns'][k] = v

    task = {
        'name': component.__class__.__name__,
        'description': 'wrapped OpenMDAO Component ' + component.__class__.__name__,
        'inputKeys': list(interface_description['Parameters'].keys()),
        'inputTemplate': {
            k: interface_description['Parameters'][k]['val']
            for k in interface_description['Parameters'].keys()
        },
        'outputKeys': list(interface_description['Unknowns'].keys()),
    }

    print(json.dumps(task, indent=2))
    return task


def run(task):
    params = task['inputData']
    unknowns = {}

    return {
        'status': 'COMPLETED',
        'output': unknowns,
    }


if __name__ == '__main__':
    # Add(TestThing(), 'one')
    define_as_task(HoverPower())
