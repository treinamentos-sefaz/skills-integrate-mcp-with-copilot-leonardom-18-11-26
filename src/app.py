"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import hashlib
import hmac
import json
import logging
import os
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ValidationError

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

logger = logging.getLogger(__name__)
bearer = HTTPBearer(auto_error=False)


class Account(BaseModel):
    email: str
    role: Literal["student", "admin"]
    token: str


def current_account(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> Account:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Authentication required",
                            headers={"WWW-Authenticate": "Bearer"})

    path = os.environ.get("AUTH_ACCOUNTS_FILE")
    if not path:
        logger.error("AUTH_ACCOUNTS_FILE is not configured")
        raise HTTPException(status_code=503, detail="Authentication is not configured")

    try:
        with open(path, encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, list) or not data:
            raise ValueError("Account file must contain a non-empty list")
        accounts = [Account.model_validate(item) for item in data]
        tokens = [account.token for account in accounts]
        if (len(set(tokens)) != len(tokens) or
                any(not token.isascii() or len(token) < 32 or
                    any(char.isspace() for char in token) for token in tokens) or
                any(not account.email.strip() or account.email != account.email.strip()
                    for account in accounts)):
            raise ValueError("Invalid account or duplicate token")
    except (OSError, ValueError, ValidationError) as exc:
        logger.error("Unable to load authentication accounts: %s", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Authentication is unavailable") from exc

    supplied_digest = hashlib.sha256(credentials.credentials.encode("utf-8")).digest()
    for account in accounts:
        token_digest = hashlib.sha256(account.token.encode("ascii")).digest()
        if hmac.compare_digest(supplied_digest, token_digest):
            return account
    raise HTTPException(status_code=401, detail="Invalid credentials",
                        headers={"WWW-Authenticate": "Bearer"})


def authorize_email(account: Account, email: str) -> None:
    if account.role == "student" and account.email.casefold() != email.strip().casefold():
        raise HTTPException(status_code=403, detail="Students can only manage their own registration")

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.get("/auth/me")
def get_current_account(account: Annotated[Account, Depends(current_account)]):
    return {"email": account.email, "role": account.role}


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str,
                        account: Annotated[Account, Depends(current_account)]):
    """Sign up a student for an activity"""
    email = email.strip()
    authorize_email(account, email)
    if account.role == "student":
        email = account.email
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if any(participant.casefold() == email.strip().casefold()
           for participant in activity["participants"]):
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str,
                             account: Annotated[Account, Depends(current_account)]):
    """Unregister a student from an activity"""
    authorize_email(account, email)
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    participant = next((participant for participant in activity["participants"]
                        if participant.casefold() == email.strip().casefold()), None)
    if participant is None:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(participant)
    return {"message": f"Unregistered {email} from {activity_name}"}
