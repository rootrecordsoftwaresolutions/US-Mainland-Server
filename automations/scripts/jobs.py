# Mainland job catalog — RootRecord scheduler.
DEFAULTS = {"enabled": False, "timeout_sec": 120, "cwd": "", "env": {}}

ON_BOOT = [
    {
        "id": "self_process",
        "enabled": True,
        "priority": 0,
        "builtin": "self_process",
        "command": "",
        "timeout_sec": 5,
        "cwd": "",
        "env": {},
    },
]

ONCE_AT_START = []

EVERY_SECONDS = []

EVERY_MINUTE = [
    {
        "id": "public_ip_notify",
        "enabled": True,
        "builtin": "public_ip_notify",
        "command": "",
        "timeout_sec": 30,
        "needs_internet": True,
        "cwd": "",
        "env": {},
    },
    {
        "id": "github_pull",
        "enabled": True,
        "builtin": "",
        "command": "git fetch origin main --quiet && git merge --ff-only origin/main",
        "timeout_sec": 60,
        "needs_internet": True,
        "cwd": "/home/ubuntu/US-Mainland-Server",
        "env": {},
    },
]

EVERY_HOUR = []
ON_AT = []
