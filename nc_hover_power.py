from __future__ import print_function
from conductor.ConductorWorker import ConductorWorker
from conductor.conductor import MetadataClient, WorkflowClient
import json
import requests
import math
from time import sleep


def define_task():
    return {
        'name': 'hover_power',
        'description': 'Estimate hover performance',
        'retryCount': 1,
        'timeoutSeconds': 10,
        'inputKeys': [
            'Vehicle',
            'rProp',
            'W',
            'cruisePower_omega',
        ],
        'inputTemplate': {
            'Vehicle': 'tiltwing',
            'rProp': 1.4,
            'W': 2000.0,
            'cruisePower_omega': 122.0,
        },
        'outputKeys': [
            'hoverPower_PBattery',
            'hoverPower_PMax',
            'hoverPower_VAutoRotation',
            'hoverPower_Vtip',
            'TMax',
            'hoverPower_PMaxBattery',
            'QMax',
        ],
        'timeoutPolicy': 'TIME_OUT_WF',
        'retryLogic': 'FIXED',
        'retryDelaySeconds': 5,
        'responseTimeoutSeconds': 5,
    }


def hover_power(task):
    # print(json.dumps(task, indent=2))
    params = task['inputData']

    unknowns = {}

    # Altitude, compute atmospheric properties
    rho = 1.225

    # Blade parameters
    Cd0 = 0.012  # Blade airfoil profile drag coefficient
    sigma = 0.1  # Solidity (could estimate from Ct assuming some average blade CL)

    # Different assumptions per vehicle
    if params["Vehicle"].lower() == "tiltwing":

        nProp = 8  # Number of props / motors
        ToverW = 1.7  # Max required T/W to handle rotor out w/ manuever margin
        k = 1.15  # Effective disk area factor (see "Helicopter Theory" Section 2-6.2)
        etaMotor = 0.85  # Assumed electric motor efficiency

        # Tip Mach number constraint for noise reasons at max thrust condition
        MTip = 0.65

        # Tip speed limit
        unknowns['hoverPower_Vtip'] = 340.2940 * MTip / math.sqrt(
            ToverW)  # Limit tip speed at max thrust, not hover
        omega = unknowns['hoverPower_Vtip'] / params['rProp']

        # Thrust per prop / rotor at hover
        THover = params['W'] / nProp

        # Compute thrust coefficient
        Ct = THover / (rho * math.pi * params['rProp'] ** 2 * unknowns['hoverPower_Vtip'] ** 2)

        # Average blade CL (see "Helicopter Theory" section 2-6.3)
        AvgCL = 6.0 * Ct / sigma

        # Hover Power
        PHover = nProp * THover * \
                 (k * math.sqrt(THover / (2 * rho * math.pi * params['rProp'] ** 2)) + \
                  sigma * Cd0 / 8 * (unknowns['hoverPower_Vtip']) ** 3 / (
                          THover / (rho * math.pi * params['rProp'] ** 2)))
        FOM = nProp * THover * math.sqrt(THover / (2 * rho * math.pi * params['rProp'] ** 2)) / PHover

        # Battery power
        unknowns['hoverPower_PBattery'] = PHover / etaMotor

        # Maximum thrust per motor
        unknowns['TMax'] = THover * ToverW

        # Maximum shaft power required (for motor sizing)
        # Note: Tilt-wing multirotor increases thrust by increasing RPM at constant collective
        unknowns['hoverPower_PMax'] = nProp * unknowns['TMax'] * \
                                      (k * math.sqrt(
                                          unknowns['TMax'] / (2 * rho * math.pi * params['rProp'] ** 2)) + \
                                       sigma * Cd0 / 8 * (unknowns['hoverPower_Vtip'] * math.sqrt(ToverW)) ** 3 / (
                                               unknowns['TMax'] / (rho * math.pi * params['rProp'] ** 2)))

        # Max battery power
        unknowns['hoverPower_PMaxBattery'] = unknowns['hoverPower_PMax'] / etaMotor

        # Maximum torque per motor
        QMax = unknowns['hoverPower_PMax'] / (omega * math.sqrt(ToverW))

    elif params['Vehicle'].lower() == "helicopter":

        nProp = 1.0  # Number of rotors
        ToverW = 1.1  # Max required T/W for climb and operating at higher altitudes
        k = 1.15  # Effective disk area factor (see "Helicopter Theory" Section 2-6.2)
        etaMotor = 0.85 * 0.98  # Assumed motor and gearbox efficiencies (85% and 98% respectively)

        omega = params['cruisePower_omega']
        unknowns['hoverPower_Vtip'] = omega * params['rProp']

        # Thrust per prop / rotor at hover
        THover = params['W'] / nProp

        # Compute thrust coefficient
        Ct = THover / (rho * math.pi * params['rProp'] ** 2.0 * unknowns['hoverPower_Vtip'] ** 2.0)

        # Average blade CL (see "Helicopter Theory" Section 2-6.4)
        AvgCL = 6.0 * Ct / sigma

        # Auto-rotation descent rate (see "Helicopter Theory" Section 3-2)
        unknowns['hoverPower_VAutoRotation'] = 1.16 * math.sqrt(THover / (math.pi * params['rProp'] ** 2.0))

        # Hover Power
        PHover = nProp * THover * \
                 (k * math.sqrt(THover / (2.0 * rho * math.pi * params['rProp'] ** 2.0)) + \
                  sigma * Cd0 / 8.0 * (unknowns['hoverPower_Vtip'] ** 3.0) / (
                          THover / (rho * math.pi * params['rProp'] ** 2.0)))
        FOM = nProp * THover * math.sqrt(THover / (2.0 * rho * math.pi * params['rProp'] ** 2.0)) / PHover

        # Battery power
        # ~10% power to tail rotor (see "Princples of Helicopter Aerodynamics" by Leishman)
        PTailRotor = 0.1 * PHover
        unknowns['hoverPower_PBattery'] = (PHover + PTailRotor) / etaMotor

        # Maximum thrust per motor
        unknowns['TMax'] = THover * ToverW

        # Maximum shaft power required (for motor sizing)
        # Note: Helicopter increases thrust by increasing collective with constant RPM
        unknowns['hoverPower_PMax'] = nProp * unknowns['TMax'] * \
                                      (k * math.sqrt(
                                          unknowns['TMax'] / (2.0 * rho * math.pi * params['rProp'] ** 2.0)) + \
                                       sigma * Cd0 / 8.0 * (unknowns['hoverPower_Vtip'] ** 3.0) / (
                                               unknowns['TMax'] / (rho * math.pi * params['rProp'] ** 2.0)))

        # ~15% power to tail rotor for sizing (see "Princples of Helicopter Aerodynamics" by Leishman)
        unknowns['hoverPower_PMax'] = 1.15 * unknowns['hoverPower_PMax']

        # Max battery power
        unknowns['hoverPower_PMaxBattery'] = unknowns['hoverPower_PMax'] / etaMotor

        # Maximum torque per motor
        unknowns['QMax'] = unknowns['hoverPower_PMax'] / omega

    print(unknowns)

    return {
        'status': 'COMPLETED',
        'output': unknowns,
        'logs': ['one', 'two']
    }


def define_workflow():
    return {
        "name": "hover_power_workflow",
        "description": "Tests the hover_power task",
        "version": 1,
        "tasks": [
            {
                "name": "hover_power",
                "taskReferenceName": "hp",
                "type": "SIMPLE",
                "inputParameters": {
                    "Vehicle": "${workflow.input.Vehicle}",
                    "rProp": "${workflow.input.rProp}",
                    "W": "${workflow.input.W}",
                    "cruisePower_omega": "${workflow.input.cruisepower_Omega}",
                }
            },
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


def main():
    task_def = define_task()
    with open('hover_power.json', 'w') as j:
        json.dump(task_def, j, indent=2)

    # Try to run function as a test
    hover_power({'inputData': task_def['inputTemplate']})

    # Register this task
    mc = MetadataClient('http://localhost:8080/api')
    # unregister_default_tasks(mc)
    mc.registerTaskDefs([task_def])

    # Start worker
    cw = ConductorWorker('http://localhost:8080/api', 1, 0.1)
    cw.start(taskType=task_def['name'],
             exec_function=hover_power,
             wait=False)

    # Create workflow
    wf_def = define_workflow()
    mc.updateWorkflowDefs([wf_def])

    # Start workflow
    wc = WorkflowClient('http://localhost:8080/api')
    wc.startWorkflow(wfName=wf_def['name'],
                     inputjson=task_def['inputTemplate'])
    # sleep(200)

    # Start worker
    cw = ConductorWorker('http://localhost:8080/api', 1, 0.1)
    cw.start(taskType=task_def['name'],
             exec_function=hover_power,
             wait=True)


def unregister_default_tasks(mc):
    l_td = mc.getAllTaskDefs()
    print(l_td)
    for td in l_td:
        if td['name'].startswith('task_'):
            mc.unRegisterTaskDef(td['name'])


if __name__ == '__main__':
    main()
