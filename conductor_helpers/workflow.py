from __future__ import print_function
from conductor.conductor import MetadataClient, WorkflowClient


class Workflow(object):
    def __init__(self, name, description=None):
        self.tasks = {}
        self.inputs = {}
        self.outputs = {}

        self.connections = {}

        self.name = name
        if description:
            self.description = description
        else:
            self.description = name

    def add_task(self, name, task):
        if 'name' in self.tasks:
            raise ValueError('A task with this name already exists')

        self.tasks[name] = task

    def add_input(self, name, default):
        self.inputs[name] = default

    def add_output(self, name, src):
        if '.' in src:
            # Src comes from another task
            src_split = src.split('.')
            source = '${{{}.output.{}}}'.format(src_split[0], src_split[1])
        else:
            # Src comes from a workflow input
            source = '${{workflow.input.{}}}'.format(src)

        self.outputs[name] = source

    def connect(self, src, dst):
        self.connections[dst] = src

    def _definition(self):
        # First, build tasks
        tasks = []
        for task_name in self.tasks.keys():
            task = self._task_definition(task_name)
            task['inputParameters'] = {}

            for dst, src in self.connections.items():
                # If the destination is within this task, we link to the input
                if dst.startswith(task_name + '.'):
                    input = dst.split('.')[1]

                    if '.' in src:
                        # Src comes from another task
                        src_split = src.split('.')
                        source = '${{{}.output.{}}}'.format(src_split[0], src_split[1])
                    else:
                        # Src comes from a workflow input
                        source = '${{workflow.input.{}}}'.format(src)

                    task['inputParameters'][input] = source

            tasks.append(task)

        return {
            'name': self.name,
            'description': self.description,
            'version': 1,
            'tasks': tasks,
            'outputParameters': self.outputs,
            'inputParameters': list(self.inputs.keys()),
            'failureWorkflow': 'cleanup_encode_resources',
            'restarteable': True,
            'workflowStatusListenerEnabled': True,
            'schemaVersion': 2,
        }

    def _task_definition(self, task_name):
        return {
            'name': self.tasks[task_name].name,
            'taskReferenceName': task_name,
            'type': 'SIMPLE',
        }

    def register(self, endpoint='http://localhost:8080/api'):
        mc = MetadataClient(endpoint)
        workflow_def = self._definition()

        # import json
        # print(json.dumps(workflow_def, indent=2))

        mc.updateWorkflowDefs([workflow_def])

    def start(self, start_tasks=False, wait=True):
        wc = WorkflowClient('http://localhost:8080/api')
        id = wc.startWorkflow(wfName=self.name,
                              inputjson=self.inputs)
        import json
        print(json.dumps(id, indent=2))

        if start_tasks:
            for idx, key in enumerate(self.tasks.keys(), start=1):
                if wait:
                    # We will poll the workflow, so no need to keep the last task running.
                    self.tasks[key].start(wait=False)
                else:
                    # We won't poll the workflow, so keep the last task running.
                    self.tasks[key].start(wait=idx == len(self.tasks.keys()))

        if wait:
            import time
            res = wc.getWorkflow(id)
            while res['status'] != 'COMPLETED':
                time.sleep(0.1)
                res = wc.getWorkflow(id)

            print(json.dumps(res['output'], indent=2))
            return res['output']
        
        else:
            return id

    def register_tasks(self):
        for k, v in self.tasks.items():
            v.register()


if __name__ == '__main__':
    from openmdao.examples.hohmann_transfer import VCircComp, TransferOrbitComp, DeltaVComp
    from openmdao_wrapper import OpenMdaoWrapper
    from sum_task import SumTask
    from json import dumps

    leo = OpenMdaoWrapper(VCircComp())
    geo = OpenMdaoWrapper(VCircComp())
    transfer = OpenMdaoWrapper(TransferOrbitComp())
    dv1 = OpenMdaoWrapper(DeltaVComp())
    dv2 = OpenMdaoWrapper(DeltaVComp())

    dv_total = SumTask('dv_total', num_inputs=2)
    dinc_total = SumTask('dinc_total', num_inputs=2)

    workflow = Workflow('Hohmann Transfer', 'A test for the Workflow class.')
    workflow.add_task('leo', leo)
    workflow.add_task('geo', geo)
    workflow.add_task('transfer', transfer)
    workflow.add_task('dv1', dv1)
    workflow.add_task('dv2', dv2)
    workflow.add_task('dv_total', dv_total)
    workflow.add_task('dinc_total', dinc_total)

    workflow.add_input('dinc1', 28.5 / 2)
    workflow.add_input('dinc2', 28.5 / 2)
    workflow.add_input('r1', 6778.137)
    workflow.add_input('r2', 42164.0)
    workflow.add_input('mu', 398600.4418)

    workflow.connect('r1', 'leo.r')
    workflow.connect('r1', 'transfer.rp')
    workflow.connect('r2', 'geo.r')
    workflow.connect('r2', 'transfer.ra')

    workflow.connect('mu', 'leo.mu')
    workflow.connect('mu', 'geo.mu')
    workflow.connect('mu', 'transfer.mu')

    workflow.connect('leo.vcirc', 'dv1.v1')
    workflow.connect('transfer.vp', 'dv1.v2')
    workflow.connect('dinc1', 'dv1.dinc')

    workflow.connect('transfer.va', 'dv2.v1')
    workflow.connect('geo.vcirc', 'dv2.v2')
    workflow.connect('dinc2', 'dv2.dinc')

    workflow.connect('dv1.delta_v', 'dv_total.i1')
    workflow.connect('dv2.delta_v', 'dv_total.i2')

    workflow.connect('dinc1', 'dinc_total.i1')
    workflow.connect('dinc2', 'dinc_total.i2')

    workflow.add_output('dv1_deltav', 'dv1.delta_v')
    workflow.add_output('dv2_deltav', 'dv2.delta_v')

    # print(dumps(workflow._definition(), indent=2))

    workflow.register_tasks()
    workflow.register()
    workflow.start(start_tasks=True)
