from typing import Annotated

from pydantic import BaseModel, Field

# The worker POSTs to this address, so only real https addresses, never
# something like http://127.0.0.1:... on our own machine. 2048 is far more
# than any push service uses.
Endpoint = Annotated[str, Field(pattern=r"^https://", max_length=2048)]


# --- What comes in ---


class PushKeys(BaseModel):
    """The browser's two keys: pushes are locked with them (D26)."""

    p256dh: str = Field(min_length=1, max_length=200)
    auth: str = Field(min_length=1, max_length=100)


class SubscribeIn(BaseModel):
    """Exactly what the browser's subscription.toJSON() gives (its extra
    expirationTime is ignored), so the app can send it as it is."""

    endpoint: Endpoint
    keys: PushKeys


class UnsubscribeIn(BaseModel):
    endpoint: Endpoint


# --- What goes out ---


class PublicKeyOut(BaseModel):
    """The VAPID public key. The browser needs it to subscribe, so pushes
    signed with our private key are the only ones it accepts."""

    public_key: str
