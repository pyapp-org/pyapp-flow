from nox_poetry import session


@session(python=["3.10", "3.9", "3.8"])
def tests(session):
    session.install("pytest", ".")
    session.run("pytest")
