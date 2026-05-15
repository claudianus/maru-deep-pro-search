"""Gateway hook handler for maru research gate."""


def handle(event, context):
    if event == "session:start":
        return {
            "action": "inject",
            "message": "[MARU] New session. Run /research before any tools.",
        }
    return None
