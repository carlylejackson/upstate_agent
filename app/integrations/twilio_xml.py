def twiml_message(text: str) -> str:
    safe_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"<?xml version=\"1.0\" encoding=\"UTF-8\"?><Response><Message>{safe_text}</Message></Response>"


def twiml_say_and_hangup(text: str) -> str:
    safe_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"<?xml version=\"1.0\" encoding=\"UTF-8\"?><Response><Say>{safe_text}</Say><Hangup/></Response>"
