"""
Checks to run over pipelines
"""
from typing import Mapping, Sequence

from pyapp_flow import Workflow, DescribeContext


def validate_workflow(workflow: Workflow, context: DescribeContext = None):
    context = context or DescribeContext()

    for step, branches in workflow.describe(context):
        if branches is None:
            description = "leaf"
        elif isinstance(branches, Mapping):
            description = "multi-branch"
        elif isinstance(branches, Sequence):
            description = "collection"
        else:
            description = "Unknown"

        print(f"{context.depth * ' '}{step} - {description}")
