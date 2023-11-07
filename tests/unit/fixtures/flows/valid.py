import pyapp_flow as flow


my_flow = (
    flow.Workflow("my_flow")
    .require_vars(a=str)
    .nodes(
        flow.LogMessage("Hello World!"),
        flow.inline(lambda a: a * 2),
    )
)
