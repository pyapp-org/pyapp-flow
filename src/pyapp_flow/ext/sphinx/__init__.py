"""
Sphinx documentation generation for Steps
"""
from typing import cast, Any, Optional, List, Iterable, Tuple, Type, Sequence

from sphinx.ext.autodoc import ModuleLevelDocumenter, bool_option
from sphinx.util.docstrings import prepare_docstring
from sphinx.util.inspect import getdoc
from sphinx.util.typing import OptionSpec

import pyapp_flow as flow
from pyapp_flow import Navigable


class StepDocumenter(ModuleLevelDocumenter):
    """
    Extension to ``sphinx.ext.autodoc`` to support documenting Steps.

    Usage::

        .. autoflow-step:: namespace.path.to.your.step

    """

    objtype = "flow-step"

    option_spec: OptionSpec = dict(
        noname=bool_option,
        **ModuleLevelDocumenter.option_spec,
    )

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

        self.add_line(f".. {domain}:{directive}:: {self.name}", source_name)
        if self.options.noname is not True:
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

        if step.inputs:
            self.add_line(f"**Input Variable(s)**", source_name)
            self._add_variable_lines(step.inputs.items(), source_name)

        if step.outputs:
            self.add_line(
                f"**Output Variable{'s' if len(step.outputs) > 1 else ''}**",
                source_name,
            )
            self._add_variable_lines(step.outputs, source_name)


class WorkflowDocumenter(ModuleLevelDocumenter):
    """
    Extension to ``sphinx.ext.autodoc`` to support documenting Workflows.

    Usage::

        .. autoflow-workflow:: namespace.path.to.your.workflow

    """

    objtype = "flow-workflow"
    option_spec: OptionSpec = dict(
        noname=bool_option,
        nodes=bool_option,
        **ModuleLevelDocumenter.option_spec,
    )

    @classmethod
    def can_document_member(cls, member: Any, *_) -> bool:
        """
        Called to see if a member can be documented by this Documenter.
        """
        return isinstance(member, flow.Workflow)

    def add_directive_header(self, sig: str) -> None:
        """
        Add the directive header and options to the generated content.
        """
        workflow = cast(flow.Workflow, self.object)
        domain = getattr(self, "domain", "py")
        directive = getattr(self, "directivetype", "function")
        source_name = self.get_sourcename()

        self.add_line(f".. {domain}:{directive}:: {self.name}", source_name)
        if self.options.noname is not True:
            self.add_line("", source_name)
            self.add_line(f"{self.indent}**{workflow.name}**", source_name)

    def get_doc(self) -> Optional[List[List[str]]]:
        """
        Decode and return lines of the docstring(s) for the object.

        When it returns None, autodoc-process-docstring will not be called for this
        object.
        """
        workflow = cast(flow.Workflow, self.object)

        docstring = workflow.description
        doc = []
        if docstring:
            tab_width = self.directive.state.document.settings.tab_width
            doc.append(prepare_docstring(docstring, tab_width))
        return doc

    def _add_nodes(self, nodes: Sequence[Navigable], source_name: str, indent: int):
        for node in nodes:
            self.add_line("", source_name)
            if isinstance(node, Navigable):
                self.add_line(f"{'  ' * indent}- {node.name}", source_name)
                self._node_tree(node, source_name, indent + 1)
            else:
                self.add_line(f"{'  ' * indent}- *Unknown node*", source_name)

    def _node_tree(self, node: Navigable, source_name: str, indent: int = 0):
        branches = node.branches()
        if branches:
            (key, nodes), *_ = branches.items()
            if len(branches) == 1 and not key:
                # Single only branch
                self._add_nodes(nodes, source_name, indent)

            else:
                for key, nodes in branches.items():
                    self.add_line("", source_name)
                    self.add_line(f"{'  ' * indent}- **{key}**", source_name)
                    self._add_nodes(nodes, source_name, indent + 1)

    def document_members(self, all_members: bool = False) -> None:
        """Generate reST for member documentation.

        If *all_members* is True, document all members, else those given by
        *self.options.members*.
        """
        workflow = cast(flow.Workflow, self.object)
        source_name = self.get_sourcename()

        if self.options.nodes:
            self._node_tree(workflow, source_name)


def setup(app):  # pragma: no cover
    app.add_autodocumenter(StepDocumenter)
    app.add_autodocumenter(WorkflowDocumenter)
