from task import Task


class OpenMdaoWrapper(Task):
    def __init__(self, component, *args, **kwargs):
        super(OpenMdaoWrapper, self).__init__(*args, **kwargs)

        self.name = component.__class__.__name__
        self.description = 'wrapped OpenMDAO Component ' + component.__class__.__name__

        for k, v in component._init_params_dict.items():
            self.add_input(k, v['val'])

        for k, v in component._init_unknowns_dict.items():
            self.add_output(k)

        self.component = component

    def run(self, inputs, outputs):
        self.component.solve_nonlinear(inputs, outputs, {})

        return {
            'status': 'COMPLETED',
            'output': outputs,
            'logs': ['one', 'two']
        }


if __name__ == '__main__':
    from conductor.conductor import MetadataClient, WorkflowClient
    from openmdao.examples.hohmann_transfer import VCircComp

    comp = VCircComp()
    t = OpenMdaoWrapper(comp)
    t.register()

    # Make a workflow
    workflow = {
        'name': 'VCircComp test workflow',
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
        'outputParameters': {k: '${{{}.output.{}}}'.format(t.name, k) for k in t.outputs.keys()},
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
