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
        pass

    def add_output(self, name):
        pass

    def connect(self, src, dst):
        self.connections[dst] = src

    def _definition(self):
        # First, build tasks
        tasks = []
        for task_name in self.tasks.keys():
            task = self._task_definition(task_name)
            task['inputParameters'] = {}

            for dst, src in self.connections.items():
                if dst.startswith(task_name + '.'):
                    input = dst.split('.')[1]

                    src_split = src.split('.')
                    source = '${{{}.output.{}}}'.format(src_split[0], src_split[1])

                    task['inputParameters'][input] = source

            tasks.append(task)

        return {
            'name': self.name,
            'description': self.description,
            'version': 1,
            'tasks': tasks,
            'outputParameters': {},
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
        mc.updateWorkflowDefs([workflow_def])

    def start(self):
        wc = WorkflowClient('http://localhost:8080/api')
        wc.startWorkflow(wfName=self.name,
                         inputjson={})


if __name__ == '__main__':
    from openmdao.examples.hohmann_transfer import VCircComp, TransferOrbitComp, DeltaVComp
    from openmdao_wrapper import OpenMdaoWrapper
    from json import dumps

    leo = OpenMdaoWrapper(VCircComp())
    geo = OpenMdaoWrapper(VCircComp())
    transfer = OpenMdaoWrapper(TransferOrbitComp())
    dv1 = OpenMdaoWrapper(DeltaVComp())
    dv2 = OpenMdaoWrapper(DeltaVComp())
    tasks = [leo, geo, transfer, dv1, dv2]

    workflow = Workflow('Hohmann Transfer', 'A test for the Workflow class.')
    workflow.add_task('leo', leo)
    workflow.add_task('geo', geo)
    workflow.add_task('transfer', transfer)
    workflow.add_task('dv1', dv1)
    workflow.add_task('dv2', dv2)

    workflow.connect('leo.vcirc', 'dv1.v1')
    workflow.connect('transfer.vp', 'dv1.v2')

    workflow.connect('transfer.va', 'dv2.v1')
    workflow.connect('geo.vcirc', 'dv2.v2')
    # workflow.connect('dinc2', 'dv2.dinc')

    print(dumps(workflow._definition(), indent=2))

    for task in tasks:
        task.register()

    workflow.register()
    workflow.start()

    for idx, task in enumerate(tasks, start=1):
        task.start(wait=idx == len(tasks))
