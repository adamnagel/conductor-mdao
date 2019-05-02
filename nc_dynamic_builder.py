from __future__ import print_function
from conductor.ConductorWorker import ConductorWorker
from conductor.conductor import MetadataClient, WorkflowClient
import json
import requests
import math
from time import sleep
from openmdao.api import Component

from vahana_scripts.hover_power import HoverPower
from vahana_scripts.cruise_power import CruisePower


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

    # print(json.dumps(task, indent=2))
    return task


def run(task):
    params = task['inputData']
    unknowns = {}

    return {
        'status': 'COMPLETED',
        'output': unknowns,
    }


def unregister_default_tasks(mc):
    l_td = mc.getAllTaskDefs()
    print(l_td)
    for td in l_td:
        if td['name'].startswith('task_'):
            mc.unRegisterTaskDef(td['name'])


def define_workflow():
    return {
        "name": "vahana_workflow",
        "description": "Tests the Vahana tasks",
        "version": 1,
        "tasks": [
            {
                "name": "CruisePower",
                "taskReferenceName": "cp",
                "type": "SIMPLE",
                "inputParameters": {
                    "Vehicle": "${workflow.input.Vehicle}",
                    "rProp": "${workflow.input.rProp}",
                    "W": "${workflow.input.W}",
                    "V": "${workflow.input.V}",
                }
            },
            {
                "name": "HoverPower",
                "taskReferenceName": "hp",
                "type": "SIMPLE",
                "inputParameters": {
                    "Vehicle": "${workflow.input.Vehicle}",
                    "rProp": "${workflow.input.rProp}",
                    "W": "${workflow.input.W}",
                    "cruisePower_omega": "${cp.output.omega}",
                }
            }
        ],
        "outputParameters": {
            "hoverPower_PBattery": "${hp.output.hoverPower_PBattery}",
            "hoverPower_PMax": "${hp.output.hoverPower_PMax}",
            "hoverPower_VAutoRotation": "${hp.output.hoverPower_VAutoRotation}",
            "hoverPower_Vtip": "${hp.output.hoverPower_Vtip}",
            "TMax": "${hp.output.TMax}",
            "hoverPower_PMaxBattery": "${hp.output.hoverPower_PMaxBattery}",
            "QMax": "${hp.output.QMax}",
        },
        "failureWorkflow": "cleanup_encode_resources",
        "restartable": True,
        "workflowStatusListenerEnabled": True,
        "schemaVersion": 2
    }


hp = HoverPower()


def run_hoverpower_component(task):
    params = task['inputData']
    unknowns = {}

    hp.solve_nonlinear(params, unknowns, {})

    return {
        'status': 'COMPLETED',
        'output': unknowns,
        'logs': ['one', 'two']
    }


cp = CruisePower()


def run_cruisepower_component(task):
    params = task['inputData']
    unknowns = {}

    cp.solve_nonlinear(params, unknowns, {})

    return {
        'status': 'COMPLETED',
        'output': unknowns,
        'logs': ['one', 'two']
    }


if __name__ == '__main__':
    # Add(TestThing(), 'one')
    mc = MetadataClient('http://localhost:8080/api')

    unregister_default_tasks(mc)

    # Let's do this one.
    hp_task_def = define_as_task(HoverPower())
    mc.registerTaskDefs([hp_task_def])

    cp_task_def = define_as_task(CruisePower())
    mc.registerTaskDefs([cp_task_def])

    # Create workflow
    wf_def = define_workflow()
    mc.updateWorkflowDefs([wf_def])

    # Start workflow
    wc = WorkflowClient('http://localhost:8080/api')
    defaults = hp_task_def['inputTemplate']
    defaults.update(cp_task_def['inputTemplate'])
    wc.startWorkflow(wfName=wf_def['name'],
                     inputjson=defaults)

    # Start workers
    cw = ConductorWorker('http://localhost:8080/api', 1, 0.1)
    cw.start(taskType=hp_task_def['name'],
             exec_function=run_hoverpower_component,
             wait=False)
    cw.start(taskType=cp_task_def['name'],
             exec_function=run_cruisepower_component,
             wait=True)
