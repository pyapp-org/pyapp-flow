#########
Workflows
#########


Workflow
========

At the basic level a workflow is an object that holds a series of nodes to be
called in sequence. The workflow object also includes helper methods to generate
and append the nodes defined in the *Builtin Nodes* section of the documentation.

Just like every node in pyApp Flow a workflow is called with an
:class:`pyapp_flow.WorkflowContext` object, this means workflows can be nested
in workflows, or called from a :class:`pyapp_flow.ForEach` node.

The one key aspect with a workflow object is related to context variable scope.
When a workflow is triggered the context scope is copied and any changes made
to the variables are discarded when the workflow ends. However, just like Python
scoping only the reference to the variable is copied meaning mutable objects can
be modified (eg list/dicts).

.. code-block:: python

  workflow = (
      Workflow(name="My Workflow")
      .nodes(...)
  )


.. autoclass:: pyapp_flow.Workflow
   :members:


WorkflowContext
===============

The workflow context object holds the state of the workflow including handling
variable scoping and helper methods for logging progress.

.. autoclass:: pyapp_flow.WorkflowContext
   :members:
   :inherited-members:
