from fastapi import HTTPException, Request


def get_supervisor_agent(request: Request):
    supervisor_agent = getattr(request.app.state, "supervisor_agent", None)
    if supervisor_agent is None:
        raise HTTPException(
            status_code=503,
            detail="Supervisor agent is not initialized yet. Please try again shortly.",
        )
    return supervisor_agent


def get_db_pool(request: Request):
    db_pool = getattr(request.app.state, "db_pool", None)
    if db_pool is None:
        raise HTTPException(
            status_code=503,
            detail="Database is not initialized yet. Please try again shortly.",
        )
    return db_pool
