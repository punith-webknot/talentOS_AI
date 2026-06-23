import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from Source.app.api.dependencies import get_db_pool
from Source.app.db.gmail_token_repository import (
    has_valid_gmail_token,
    pop_oauth_pending,
    save_oauth_pending,
    upsert_gmail_credentials,
)
from Source.app.utils.gmail_credentials import (
    build_gmail_authorization_url,
    create_gmail_oauth_flow,
    exchange_authorization_code,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class GmailAuthStatusResponse(BaseModel):
    user_id: str
    connected: bool
    authorization_url: str | None = None


class GmailOAuthCallbackResponse(BaseModel):
    user_id: str
    connected: bool
    message: str


@router.get("/auth/{user_id}", response_model=GmailAuthStatusResponse)
async def get_gmail_auth_status(
    user_id: str,
    db_pool=Depends(get_db_pool),
):
    """
    Check whether Gmail is connected for a user.
    If not connected, return a Google OAuth login URL.
    """
    if await has_valid_gmail_token(db_pool, user_id):
        return GmailAuthStatusResponse(user_id=user_id, connected=True)

    flow = create_gmail_oauth_flow()
    authorization_url, code_verifier = build_gmail_authorization_url(flow, user_id)
    await save_oauth_pending(db_pool, user_id, code_verifier)

    return GmailAuthStatusResponse(
        user_id=user_id,
        connected=False,
        authorization_url=authorization_url,
    )


@router.get("/oauth/callback", response_model=GmailOAuthCallbackResponse)
async def gmail_oauth_callback(
    request: Request,
    db_pool=Depends(get_db_pool),
):
    """
    OAuth redirect target after the user signs in with Google.
    Exchanges the authorization code and stores the token in the database.
    """
    params = request.query_params
    oauth_error = params.get("error")
    if oauth_error:
        raise HTTPException(
            status_code=400,
            detail=f"Google OAuth failed: {oauth_error}",
        )

    user_id = params.get("state")
    code = params.get("code")
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing OAuth state (user_id).")
    if not code:
        raise HTTPException(status_code=400, detail="Missing OAuth authorization code.")

    code_verifier = await pop_oauth_pending(db_pool, user_id)
    if not code_verifier:
        raise HTTPException(
            status_code=400,
            detail="OAuth session expired. Request a new authorization URL.",
        )

    try:
        flow = create_gmail_oauth_flow()
        creds = exchange_authorization_code(
            flow,
            authorization_response=str(request.url),
            code_verifier=code_verifier,
        )
        await upsert_gmail_credentials(db_pool, user_id, creds)
    except Exception as exc:
        logger.exception("Gmail OAuth callback failed for user_id=%s", user_id)
        raise HTTPException(
            status_code=400,
            detail=f"Failed to complete Gmail OAuth: {exc}",
        ) from exc

    return GmailOAuthCallbackResponse(
        user_id=user_id,
        connected=True,
        message="Gmail account connected successfully.",
    )
