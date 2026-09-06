from pathlib import Path

import streamlit.components.v1 as components

_COMPONENT = components.declare_component(
    "google_calendar_auth",
    path=str(Path(__file__).parent / "google_calendar_component"),
)


def request_google_access_token(client_id, request_id):
    """Render the browser OAuth component and return a token or error result."""
    return _COMPONENT(client_id=client_id, request_id=request_id, key=f"google_calendar_{request_id}", default=None)
