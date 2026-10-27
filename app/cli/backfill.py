import argparse
import sys
from datetime import date

from app.clients.elexon import ElexonClient
from app.core.database import SessionLocal
from app.services.ingestion import IngestionError, import_actuals, import_forecasts


def main() -> int:
    parser = argparse.ArgumentParser(description="Import Elexon wind actuals and forecast versions.")
    parser.add_argument("--delivery-from", type=date.fromisoformat, required=True)
    parser.add_argument("--delivery-to", type=date.fromisoformat, required=True)
    arguments = parser.parse_args()
    if arguments.delivery_to < arguments.delivery_from:
        parser.error("--delivery-to must not be before --delivery-from")

    session = SessionLocal()
    try:
        with ElexonClient() as client:
            summaries = [
                import_actuals(session, arguments.delivery_from, arguments.delivery_to, client),
                import_forecasts(session, arguments.delivery_from, arguments.delivery_to, client),
            ]
        for summary in summaries:
            print(
                f"{summary.dataset}: received={summary.received} written={summary.written} "
                f"duplicates={summary.duplicates} rejected={summary.rejected}"
            )
        return 0
    except IngestionError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
