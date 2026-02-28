from app.db.session import get_session_factory
from app.services.kb_service import KBService


def run_reindex(updated_by: str = "system") -> dict:
    session = get_session_factory()()
    try:
        return KBService(session).reindex(urls=None, updated_by=updated_by)
    finally:
        session.close()


if __name__ == "__main__":
    print(run_reindex())
