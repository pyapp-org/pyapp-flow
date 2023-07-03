import pyapp_flow as flow


@flow.step
def esplode():
    raise ValueError("Boom!")


my_flow = flow.Workflow("my_flow").nodes(
    flow.LogMessage("Hello World!"),
    esplode,
)
