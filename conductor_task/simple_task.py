from conductor_task import ConductorTask


class SimpleTask(ConductorTask):
    def __init__(self, name=None, description=None):
        super(SimpleTask, self).__init__()

        if name:
            self.name = name
        else:
            self.name = self.__class__.__name_

        if description:
            self.description = description
        else:
            self.description = self.name

        self.add_input('value1', 2.3)
        self.add_input('value2', 4.6)
        self.add_output('output')

    def run(self, inputs, outputs):
        outputs['output'] = inputs['value1'] * inputs['value2']


if __name__ == '__main__':
    from conductor.conductor import MetadataClient, WorkflowClient

    t = SimpleTask('Simple  Task Test', 'Only a test.')
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

    # Register it
    mc = MetadataClient('http://localhost:8080/api')
    mc.updateWorkflowDefs([workflow])

    # Start workflow
    wc = WorkflowClient('http://localhost:8080/api')
    wc.startWorkflow(wfName=workflow['name'],
                     inputjson=t.inputs)

    # Try it!
    t.start(wait=True)
