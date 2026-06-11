from fastapi import Request


def get_supervisor_agent(request: Request):
    return request.app.state.supervisor_agent
