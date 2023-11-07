###
CLI
###

A CLI is provided to trigger workflows that are defined in a ``flowfile.py`` file.

The primary CLI commands are ``list`` and ``run``.

A `flowfile` is simply a Python file in which a set of workflows are defined or imported.
The `flowfile` is loaded by the CLI and the workflows are made available for execution.


Listing available workflows
---------------------------

.. code-block:: bash

    $ flow list --help
    usage: flow list [-h] [-f FLOW_FILE]

    options:
      -h, --help            show this help message and exit
      -f FLOW_FILE, --flow-file FLOW_FILE
                            Location of flow file; default is ./flowfile.py

Running a workflow
------------------

.. code-block:: bash

    $ flow run --help
    usage: flow run [-h] [-f FLOW_FILE] [--dry-run] [--full-trace] NAME [KEY=VALUE ...]

    positional arguments:
      NAME                  Name of workflow
      KEY=VALUE             Key/Value arguments added to flow context

    options:
      -h, --help            show this help message and exit
      -f FLOW_FILE, --flow-file FLOW_FILE
                            Location of flow file; default is ./flowfile.py
      --dry-run             Dry run; do not execute actions
      --full-trace          Show full trace on error.


The ``run`` command takes a workflow name and a set of key/value pairs that are
added to the flow context.

The run command also includes tracing to report aid in the identification of
errors within a flow and where they occurred.
