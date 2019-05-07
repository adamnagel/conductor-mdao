from task import Task
import json


class SumTask(Task):
    def __init__(self, name, description=None, use_defaults=False, num_inputs=2, *args, **kwargs):
        super(SumTask, self).__init__(use_defaults=use_defaults, *args, **kwargs)

        if name:
            self.name = name
        else:
            self.name = self.__class__.__name_

        if description:
            self.description = description
        else:
            self.description = self.name

        for i in range(0, num_inputs, 1):
            self.add_input('i{}'.format(i), 1.0)

        self.add_output('sum')

    def run(self, inputs, outputs):
        out = 0.0
        for k, v in inputs.items():
            out += v

        outputs['sum'] = out


if __name__ == '__main__':
    from conductor.conductor import MetadataClient, WorkflowClient

    t = SumTask('Sum  Task Test', 'Only a test.', num_inputs=3, use_defaults=True)
    t.register()

    # Make a workflow
    workflow = {
        'name': 'SimpleTask test workflow',
        'description': 'just a test',
        'version': 1,
        'tasks': [
            {
                'name': t.name,
                'taskReferenceName': t.name,
                'type': 'SIMPLE',
                'inputParameters': {k: t.inputs[k] for k in t.inputs.keys()},
            }
        ],
        'outputParameters': {k: '$({}.output.{}'.format(t.name, k) for k in t.outputs.keys()},
        "failureWorkflow": "cleanup_encode_resources",
        "restartable": True,
        "workflowStatusListenerEnabled": True,
        "schemaVersion": 2
    }

    print(json.dumps(workflow, indent=2))

    # Register it
    mc = MetadataClient('http://localhost:8080/api')
    mc.updateWorkflowDefs([workflow])

    # Start workflow
    wc = WorkflowClient('http://localhost:8080/api')
    wc.startWorkflow(wfName=workflow['name'],
                     inputjson=t.inputs)

    # Try it!
    t.start(wait=True)
