import argparse
import asyncio
import sys
from pathlib import Path

from app.core.config import get_settings
from app.evaluation.dataset import load_dataset
from app.evaluation.runner import RunOptions, run_evaluation, save_results


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description="Offline retrieval and RAGAS evaluation")
    command.add_argument("--dataset", type=Path, required=True)
    command.add_argument("--user-email", required=True)
    command.add_argument("--top-k", type=int, default=5)
    command.add_argument("--mode", choices=("retrieval", "ragas", "all"), default="retrieval")
    command.add_argument("--limit", type=int)
    command.add_argument("--case-id")
    command.add_argument("--tag")
    command.add_argument("--max-concurrency", type=int)
    command.add_argument("--output", type=Path, default=Path("evaluation/results.json"))
    command.add_argument("--fail-on-error", action="store_true")
    return command


async def main_async(arguments: argparse.Namespace) -> int:
    if arguments.top_k < 5:
        raise ValueError("--top-k must be at least 5 so Hit@5 and Recall@5 are valid")
    cases = load_dataset(arguments.dataset)
    if arguments.case_id:
        cases = [case for case in cases if case.id == arguments.case_id]
    if arguments.tag:
        cases = [case for case in cases if arguments.tag in case.tags]
    if arguments.limit is not None:
        if arguments.limit <= 0:
            raise ValueError("--limit must be positive")
        cases = cases[: arguments.limit]
    if not cases:
        raise ValueError("No evaluation cases match the supplied filters")
    options = RunOptions(
        mode=arguments.mode,
        top_k=arguments.top_k,
        max_concurrency=arguments.max_concurrency or get_settings().ragas_max_concurrency,
        fail_on_error=arguments.fail_on_error,
    )
    results = await run_evaluation(cases, arguments.user_email, options)
    json_path, csv_path = save_results(results, arguments.output)
    print(f"Evaluation complete: {json_path} and {csv_path}")
    return 1 if arguments.fail_on_error and any(results["api_failure_counts"].values()) else 0


def main() -> int:
    try:
        return asyncio.run(main_async(parser().parse_args()))
    except Exception as exc:
        print(f"Evaluation failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
