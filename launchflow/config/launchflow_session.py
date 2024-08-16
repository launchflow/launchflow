import dataclasses
import json
import os
import uuid

SESSION_PATH = os.path.expanduser("~/.config/launchflow/session.json")


@dataclasses.dataclass
class LaunchFlowSession:
    session_id: str

    @classmethod
    def load(self):
        if os.path.exists(SESSION_PATH):
            with open(SESSION_PATH) as f:
                return LaunchFlowSession(**json.load(f))
        else:
            os.makedirs(os.path.dirname(SESSION_PATH), exist_ok=True)
            session_id = str(uuid.uuid4())
            session = LaunchFlowSession(session_id=session_id)
            with open(SESSION_PATH, "w") as f:
                json.dump(dataclasses.asdict(session), f)
            return session
