import pyapp_flow as flow


my_flow = flow.Workflow("my_flow").nodes(
    flow.LogMessage("Hello World!"),
    flow.inline(lambda a: a * 2),
)
