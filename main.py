import argparse
import json
import os
import uvicorn
from fastapi import FastAPI
from app.db.database import init_db
from app.api.routes import router
from app.core.prep_engine import run_prep_session

# --- FastAPI App ---
app = FastAPI(
    title="Adaptive Document Prep System",
    description="AI-powered prep system for the SLATEFALL dossier.",
    version="1.0.0"
)
app.include_router(router)


from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield



# --- CLI ---
def save_outputs(result: dict, output_dir: str):
    """Save questions and kb_snapshot to the outputs folder."""
    os.makedirs(output_dir, exist_ok=True)

    questions_path = os.path.join(output_dir, "questions.json")
    with open(questions_path, "w") as f:
        json.dump(result["questions"], f, indent=2)

    kb_path = os.path.join(output_dir, "kb_snapshot.json")
    with open(kb_path, "w") as f:
        json.dump(result["kb_snapshot"], f, indent=2)

    print(f"Outputs saved to: {output_dir}")


def run_cli():
    parser = argparse.ArgumentParser(
        description="Adaptive Document Prep System"
    )
    parser.add_argument(
        "--sections",
        nargs="+",
        type=int,
        default=None,
        help="Section IDs to study e.g. --sections 1 2 3"
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Simulate user answers (for Scenario B)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory to save questions.json and kb_snapshot.json"
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Run as FastAPI server instead of CLI"
    )

    args = parser.parse_args()

    if args.serve:
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
        return

    if not args.sections:
        parser.error("--sections is required when not using --serve")

    init_db()

    result = run_prep_session(
        section_ids=args.sections,
        simulate_answers=args.simulate
    )

    if args.output_dir:
        save_outputs(result, args.output_dir)


if __name__ == "__main__":
    run_cli()