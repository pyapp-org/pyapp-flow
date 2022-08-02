##################
Sphinx Integration
##################

pyApp Flow includes integration with Sphinx for documenting steps and workflows.

Installation
============

The pyApp Flow integration requires autodoc to also be enabled. Add both entries
into the extensions variables of your Sphinx docs ``conf.py`` file:

.. code-block:: python

  # -- General configuration ---------------------------------------------------

  # Add any Sphinx extension module names here, as strings. They can be
  # extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
  # ones.
  extensions = [
      "sphinx.ext.autodoc",
      "pyapp_flow.ext.sphinx",
  ]


Usage
=====

.. note:: All of these examples can be found in the `samples folder`_ in source control.

.. _`samples folder`: https://github.com/pyapp-org/pyapp-flow/tree/develop/samples

Document a Step
---------------

Document the following step and the ``autoflow-step`` directive.

.. code-block:: python

    import pyapp_flow as flow

    @flow.step(name="Read books from file", output="books")
    def read_books(library_path: Path) -> Sequence[Tuple[str, str]]:
        """
        Read book titles and ISBN from data file
        """
        data_file = library_path / "data.txt"
        with data_file.open() as f:
            reader = csv.reader(f)
            return list(reader)

And the Sphinx/ReStructuredText required to generate documentation:

.. code-block:: rst

  .. autoflow-step:: docs_example.library.read_books

And the resulting documentation:

  .. autoflow-step:: docs_example.library.read_books

Options
~~~~~~~

The ``noname`` option prevents the step name from being included in documented output.


Document a Workflow
-------------------

Next document the workflow that utilises the step

.. code-block:: python

    import pyapp_flow as flow

    report_books_workflow = (
        flow.Workflow(
            name="Read and print books",
            description="""
            Read books from the library path and print them out to
            the prompt.

            Requires the ``library_path`` to be set.
            """,
        )
        .nodes(
            read_books,
            flow.ForEach("book_title, book_isbn", in_var="books")
            .loop(print_book),
        )
    )

And the Sphinx/ReStructuredText required to generate documentation:

.. code-block:: rst

  .. autoflow-workflow:: docs_example.library.report_books_workflow

And the resulting documentation:

  .. autoflow-workflow:: docs_example.library.report_books_workflow

Options
~~~~~~~

The ``noname`` option prevents the workflow name from being included in documented output.
