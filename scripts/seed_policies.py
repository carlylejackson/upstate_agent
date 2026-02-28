from app.db.session import get_session_factory
from app.services.policy_service import PolicyService


def run() -> None:
    session = get_session_factory()()
    try:
        service = PolicyService(session)
        service.update_policy(
            "business_hours",
            "Monday-Friday 9:00 AM-4:00 PM ET. Appointments available by request outside these hours.",
            "seed",
        )
        service.update_policy("phone", "(864) 770-8822", "seed")
        service.update_policy("address", "25 Woods Lake Rd Suite 401, Greenville, SC 29607", "seed")
    finally:
        session.close()


if __name__ == "__main__":
    run()
