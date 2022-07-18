"""
Sphinx documentation generation for Steps
"""
from typing import cast, Any, Optional, List, Iterable, Tuple, Type

from sphinx.ext.autodoc import ModuleLevelDocumenter
from sphinx.util.docstrings import prepare_docstring
from sphinx.util.inspect import getdoc

import pyapp_flow as flow


class StepDocumenter(ModuleLevelDocumenter):
    """
    Extension to ``sphinx.ext.autodoc`` to support documenting Steps.

    Usage::

        .. autoflow-step:: namespace.path.to.your.step

    """

    objtype = "flow-step"

    @classmethod
    def can_document_member(cls, member: Any, *_) -> bool:
        """
        Called to see if a member can be documented by this Documenter.
        """
        return isinstance(member, flow.Step)

    def add_directive_header(self, sig: str) -> None:
        """
        Add the directive header and options to the generated content.
        """
        step = cast(flow.Step, self.object)
        domain = getattr(self, "domain", "py")
        directive = getattr(self, "directivetype", "function")
        source_name = self.get_sourcename()
        name = f"{step.func.__module__}.{step.func.__name__}"

        self.add_line(f".. {domain}:{directive}:: {name}", source_name)
        self.add_line("", source_name)
        self.add_line(f"{self.indent}**{step.name}**", source_name)

    def get_doc(self) -> Optional[List[List[str]]]:
        """
        Decode and return lines of the docstring(s) for the object.

        When it returns None, autodoc-process-docstring will not be called for this
        object.
        """
        # Replace self.object with self.object.func
        docstring = getdoc(
            self.object.func, self.get_attr, False, self.parent, self.object_name
        )
        doc = []
        if docstring:
            tab_width = self.directive.state.document.settings.tab_width
            doc.append(prepare_docstring(docstring, tab_width))
        return doc

    def _add_variable_lines(
        self, variables: Iterable[Tuple[str, Optional[Type]]], source_name: str
    ):
        self.add_line("", source_name)  # Ensure blank line
        for context_var, var_type in variables:
            if var_type:
                type_name = getattr(var_type, "__name__", str(var_type))
                self.add_line(f"* *{context_var}*: *{type_name}*", source_name)
            else:
                self.add_line(f"* *{context_var}*", source_name)
        self.add_line("", source_name)  # Trailing blank line after bullets

    def document_members(self, all_members: bool = False) -> None:
        """Generate reST for member documentation.

        If *all_members* is True, document all members, else those given by
        *self.options.members*.
        """
        step = cast(flow.Step, self.object)
        source_name = self.get_sourcename()

        self.add_line("", source_name)  # Ensure blank line

        self.add_line("**Input Variable(s)**", source_name)
        self.add_line(
            "These variables are resolved from the :py:class:`pyapp_flow.datastructures.WorkflowContext` at runtime",
            source_name,
        )
        self._add_variable_lines(step.inputs.items(), source_name)

        self.add_line("**Output Variable(s)**", source_name)
        self.add_line(
            "These variables are added to the :py:class:`pyapp_flow.datastructures.WorkflowContext` at runtime",
            source_name,
        )
        self._add_variable_lines(step.outputs, source_name)


def setup(app):  # pragma: no cover
    app.add_autodocumenter(StepDocumenter)
