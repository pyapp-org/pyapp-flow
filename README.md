# pyapp-flow
A simple application level workflow library.

Allows complex processes to be broken into smaller specific steps, greatly 
simplifying testing and re-use.

[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=pyapp-org_pyapp-flow&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=pyapp-org_pyapp-flow)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=pyapp-org_pyapp-flow&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=pyapp-org_pyapp-flow)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=pyapp-org_pyapp-flow&metric=coverage)](https://sonarcloud.io/summary/new_code?id=pyapp-org_pyapp-flow)
[![Once you go Black...](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)


## Installation

```shell
pip install pyapp-flow
```


## Usage

```python
from pathlib import Path
from typing import Sequence
import pyapp_flow as flow

# Define steps:

@flow.step(name="Load Names", output="names")
def load_names(root_path: Path) -> Sequence[str]:
    """
    Read a sequence of names from a file
    """
    with (root_path / "names.txt").open() as f_in:
        return [name.strip() for name in f_in.readlines()]

@flow.step(name="Say hello")
def say_hi(name: str):
    print(f"Hello {name}")

# Define a workflow:

great_everybody = (
    flow.Workflow(name="Great everybody in names file")
    .nodes(
      load_names,
      flow.ForEach("name", in_var="names").loop(say_hi)
    )
)

# Execute workflow:

context = flow.WorkflowContext(root_path=Path())
great_everybody(context)
```

All nodes within the workflow follow a simple interface of:
```python
def node_function(context: flow.WorkflowContext):
    ...
```
or using typing
```python
NodeFunction = Callable[[flow.WorkflowContext], Any]
```

The `step` decorator simplifies definition of a step by handling loading and saving 
of state variables from the `WorkflowContext`.


## Reference

### Workflow

At the basic level a workflow is an object that holds a series of nodes to be called 
in sequence. The workflow object also includes helper methods to generate and append
the nodes defined in the *Builtin Nodes* section of the documentation. 

Just like every node in pyApp-Flow a workflow is called with an `WorkflowContext` 
object, this means workflows can be nested in workflows, or called from a for-each 
node.

The one key aspect with a workflow object is related to context variable scope. 
When a workflow is triggered the context scope is copied and any changes made 
to the variables are discarded when the workflow ends. However, just like Python 
scoping only the reference to the variable is copied meaning mutable objects can 
be modified (eg list/dicts).

```python
workflow = (
    flow.Workflow(name="My Workflow")
    .nodes(...)
)
```

### WorkflowContext

The workflow context object holds the state of the workflow including handling 
variable scoping and helper methods for logging progress.

**Properties**

- `state` 

  Direct access to state variables in the current scope.

- `depth` 
 
  Current scope depth

- `indent` 

  Helper that returns a string indent for use formatting messages

**Methods**

- `format`

  Format a string using values from the context state. Most *name*
  values for nodes/workflows use this method to allow values to be included
  from scope eg:

  ```python
  context.format("Current path {working_path}")
  ```

- `push_state`/`pop_state`

  Used to step into or out of a lower state scope. Typically these methods are
  not called directly but are called via using a with block eg:
  
  ```python
  with context:
      pass  # Separate variable scope 
  ```

- Logging wrappers

  Wrappers around an internal workflow logger that handle indentation to make
  reading the log easier.
  
  - log
  - debug
  - info
  - warning
  - error
  - exception



### Builtin Nodes

**Modify context variables**

- `SetVar`
  
    Set one or more variables into the context

    ```python
    SetVar(my_var="foo")
    ```

- `Append`

    Append a value to a list in the context object (will create the list if it 
    does not exist).

    ```python
    Append("messages", "Operation failed to add {my_var}")
    ```
  
- `CaptureErrors`

    Capture and store any errors raised by node(s) within the capture block to a 
    variable within the context.

    ```python
    CaptureErrors("errors").nodes(my_flaky_step)
    ```
  
    This node also has a `try_all` argument that controls the behaviour when an  
    error is captured, if `True` every node is called even if they all raise errors,
    this is useful for running a number of separate tests that may fail.

    ```python
    CaptureErrors(
        "errors", 
        try_all=True
    ).nodes(
        my_first_check, 
        my_second_check, 
    )
    ```

**Provide feedback**

- `LogMessage`
    
    Insert a message within optional values from the context into the runtime 
    log with an optional level.
    
    ```python
    LogMessage("State of my_var is {my_var}", level=logging.INFO)
    ```


**Branching**

Branching nodes utilise a fluent interface for defining the nodes within each 
branch. 

- `Conditional` / `If`
    
    Analogous with an `if` statement, it can accept either a context variable 
    that can be interpreted as a `bool` or a function/lamba that accepts a 
    `WorkflowContext` object and returns a `bool`.

    ```python 
    # With context variable
    (
        If("is_successful")
        .true(log_message("Process successful :)"))
        .false(log_message("Process failed :("))
    )
  
    # With Lambda
    (
        If(lambda context: len(context.state.errors) == 0)
        .true(log_message("Process successful :)"))
        .false(log_message("Process failed :("))
    )
    ```
  
- `Switch`

    Analogous with a `switch` statement found in many languages or with Python 
    a `dict` lookup with a default fallback.

    Like the conditional node switch can accept a context variable or a 
    function/lambda that accepts a `WorkflowContext`, except returns any *hashable*
    object.

    ```python
    # With context variable
    (
        Switch("my_var")
        .case("foo", log_message("Found foo!"))
        .case("bar", log_message("Found bar!"))
        .default(log_message("Found neither."))
    )
  
    # With Lambda
    (
        Switch(lambda context: context.state["my_var"])
        .case("foo", log_message("Found foo!"))
        .case("bar", log_message("Found bar!"))
    )
    ```
  

**Iteration**

- `ForEach`
    
    Analogous with a `for` loop this node will iterate through a sequence and 
    call each of the child nodes.

    All nodes within a for-each loop are in a nested context scope.
    
    ```python
    # With a single target variable
    (
        ForEach("message", in_var="messages")
        .loop(log_message("- {message}"))
    )
  
    # With multiple target variables
    (
        ForEach("name, age", in_var="students")
        .loop(log_message("- {name} is {age} years old."))
    )
    ```
