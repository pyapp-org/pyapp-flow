###############
Getting Started
###############


Defining a step
===============

A *step* is a function that uses the ``step`` decorator to define the input and
output context variables along with metadata to provide more context to the end
user about what the step does.

.. code-block:: python

  @flow.step(name="Read books from file", output="books")
  def read_books(library_path: Path) -> Sequence[Tuple[str, str]]:
      """
      Read book titles and ISBN from data file
      """

This code defines a step called ``read_books``, it accepts a variable
``library_path`` and returns a sequence of title/isbn pairs to be stored into the
``books`` context variable.

Additionally the steps name is set to *'Read books from file'*. The body of the
function can now be completed to implement the expected behaviour.

Testing a step
==============

By breaking a process into a series of small steps testing is much easier to
arrange, act and assert. pyApp Flow includes a helper to simply testing of steps.

The following example is executed by `pytest`_.

.. _pytest: https://docs.pytest.org/

.. code-block:: python

  from pyapp_flow.testing import call_step

  def test_read_books():
      context = call_step(
          read_books,  # Step to call
          # Context variables required to run step
          library_path=Path("/path/to/library"),
      )

      # Assert that the output variable is what was expected
      assert context.state["books"] == [...]

The :py:func:`call_step <pyapp_flow.testing.call_step>` function handles setting
up the :py:class:`WorkflowContext <pyapp_flow.WorkflowContext>` with the supplied
variables, calling the step with the context before returning it to allow for
assertions to be defined.


Combining steps into a Workflow
===============================

Finally define a Workflow that combines multiple steps/:doc:`nodes <reference/nodes>`
into a complete flow.

A workflow can include branching nodes (:class:`If <pyapp_flow.Conditional>`,
:class:`Switch <pyapp_flow.Switch>`) and interation (:class:`ForEach <pyapp_flow.ForEach>`)
as well as descriptive metadata.

.. _nodes: :doc:reference/nodes

.. code-block:: python

  report_books_workflow = flow.Workflow(
      name="Read and print books",
      description="""
      Read books from the library path and print them out to the prompt.

      Requires the library_path to be set.
      """,
  ).nodes(
      read_books,
      flow.ForEach("book_title, book_isbn", in_var="books").loop(
          print_book,
      ),
  )

This workflow breaks this process into multiple stages, first reads all books from
a data file, before looping though each book and calling the ``print_book`` step for
each book defined to print out the title and isbn.


Execute a Workflow
==================

Workflow execution requires calling the :meth:`execute <pyapp_flow.Workflow.execute>`
method to start the flow, optionally initial context variables can be supplied that
are required for the workflow to operate.

.. code-block:: python

  report_books_workflow.execute(library_path=HERE)


Complete example
================

Bringing all of these items together produces the following script. While this
example is very basic, the ``read_books`` step could easily be integrated into a
different workflow. Each step can be highly tested allowing for flexible building
of workflows to meet changing or un-expected requirements.

.. note::
  See the GitHub repository samples folder for the code and associated data file.

.. code-block:: python

  import csv
  import logging
  from pathlib import Path
  from typing import Sequence, Tuple

  import pyapp_flow as flow


  # Define Steps

  @flow.step(name="Read books from file", output="books")
  def read_books(*, library_path: Path) -> Sequence[Tuple[str, str]]:
      """
      Read book titles and ISBN from data file
      """
      data_file = library_path / "data.txt"
      with data_file.open() as f:
          reader = csv.reader(f)
          return list(reader)


  @flow.step(name="Print books")
  def print_book(*, book_title: str, book_isbn: str):
      """
      Print book title and ISBN
      """
      print(f"Title: {book_title}\nISBN:  {book_isbn}\n")


  # Define Workflow

  report_books_workflow = flow.Workflow(
      name="Read and print books",
      description="""
      Read books from the library path and print them out to the prompt.

      Requires the library_path to be set.
      """,
  ).nodes(
      read_books,
      flow.ForEach("book_title, book_isbn", in_var="books").loop(
          print_book,
      ),
  )


  # Execute the Workflow

  if __name__ == "__main__":
      logging.basicConfig(level=logging.DEBUG)

      HERE = Path(__file__).parent
      report_books_workflow.execute(library_path=HERE)
