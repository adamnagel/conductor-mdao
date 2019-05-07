from __future__ import print_function
from conductor.conductor import MetadataClient
from conductor.ConductorWorker import ConductorWorker


class Task(object):
    def __init__(self, use_defaults=False):  # name=None, description=None):
        self.inputs = {}
        self.outputs = {}
        self.use_defaults = use_defaults

        # if name:
        #     self.name = name
        # else:
        #     self.name = self.__class__.__name_
        #
        # if description:
        #     self.description = description
        # else:
        #     self.description = self.name

    def add_input(self, name=None, default=None):
        self.inputs[name] = default

    def add_output(self, name=None):
        self.outputs[name] = None

    def register(self, endpoint='http://localhost:8080/api'):
        mc = MetadataClient(endpoint)

        task_def = {
            'name': self.name,
            'description': self.description,
            'inputKeys': list(self.inputs.keys()),
            'outputKeys': list(self.outputs.keys()),
        }

        # Only create inputTemplate if we plan to use defaults
        if self.use_defaults:
            task_def['inputTemplate'] = self.inputs
        else:
            pass

        import json
        json.dumps(task_def)

        mc.registerTaskDefs([task_def])

    def start(self, endpoint='http://localhost:8080/api', wait=False):
        cw = ConductorWorker(endpoint, 1, 0.1)
        cw.start(taskType=self.name,
                 exec_function=self._run_task,
                 wait=wait)

    def _run_task(self, task):
        inputs = task['inputData']
        outputs = {k: None for k in self.outputs.keys()}

        self.run(inputs, outputs)

        return {
            'status': 'COMPLETED',
            'output': outputs,
            'logs': ['one', 'two']
        }

    def run(self, inputs, outputs):
        pass


if __name__ == '__main__':
    t = Task()  # 'TestCase', 'Only a test.')
    t.register()
