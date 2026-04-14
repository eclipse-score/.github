from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING

from .collector import collect_snapshot, ensure_snapshot, load_snapshot
from .console import print_status
from .constants import (
    DEFAULT_CACHE,
    DEFAULT_METRICS_OUTPUT,
    DEFAULT_ORG,
    DEFAULT_OUTPUT,
    DEFAULT_TOKEN_ENV,
)
from .metrics_report import render_metrics_report
from .profile_readme import load_config, load_template, render_readme

if TYPE_CHECKING:
    from collections.abc import Sequence


CLI_EPILOG = dedent(
    f"""\
    Quick start:
      uv run generate-repo-overview collect
          Sync the cached snapshot from GitHub.

      uv run generate-repo-overview render
          Re-render both built-in reports from the local cache only.

    Defaults:
      Cache:   {DEFAULT_CACHE}
      README:  {DEFAULT_OUTPUT}
      Metrics: {DEFAULT_METRICS_OUTPUT}

    Use `uv run generate-repo-overview <command> --help` for command-specific options.
    """
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Collect cached GitHub organization repository overviews and render "
            "different Markdown views from the same snapshot."
        ),
        epilog=CLI_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(
        dest="command",
        metavar="command",
    )

    collect_parser = subparsers.add_parser(
        "collect",
        help="Collect and write the cached repository snapshot.",
    )
    add_collection_args(collect_parser, include_refresh=False)

    render_parser = subparsers.add_parser(
        "render",
        help="Render all built-in reports from a cached snapshot.",
    )
    add_render_input_arg(render_parser)
    add_combined_render_args(render_parser)

    generate_profile_parser = subparsers.add_parser(
        "generate-profile-readme",
        help="Use the cached snapshot when possible and render the profile README.",
    )
    add_collection_args(generate_profile_parser, include_refresh=True)
    add_profile_render_args(generate_profile_parser)

    generate_metrics_parser = subparsers.add_parser(
        "generate-metrics",
        help="Use the cached snapshot when possible and render the metrics report.",
    )
    add_collection_args(generate_metrics_parser, include_refresh=True)
    add_metrics_render_args(generate_metrics_parser)

    return parser


def add_collection_args(
    parser: argparse.ArgumentParser,
    *,
    include_refresh: bool,
) -> None:
    parser.add_argument("--org", default=DEFAULT_ORG, help="GitHub organization name")
    parser.add_argument(
        "--cache",
        type=Path,
        default=DEFAULT_CACHE,
        help="JSON snapshot cache file",
    )
    parser.add_argument(
        "--token-env",
        default=DEFAULT_TOKEN_ENV,
        help="Environment variable that contains the GitHub token",
    )
    if include_refresh:
        parser.add_argument(
            "--refresh",
            action="store_true",
            help="Refresh the snapshot from GitHub instead of reusing the cache",
        )


def add_render_input_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_CACHE,
        help="JSON snapshot file to render from",
    )


def add_profile_render_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Markdown file to write",
    )
    parser.add_argument(
        "--template",
        type=Path,
        help="Optional markdown template file with a {{ repo_sections }} placeholder",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Optional category config file that defines order and descriptions",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the generated markdown instead of writing the file",
    )


def add_metrics_render_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_METRICS_OUTPUT,
        help="Markdown file to write",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the generated markdown instead of writing the file",
    )


def add_combined_render_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--readme-output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Markdown file for the organization profile README",
    )
    parser.add_argument(
        "--metrics-output",
        type=Path,
        default=DEFAULT_METRICS_OUTPUT,
        help="Markdown file for the metrics report",
    )
    parser.add_argument(
        "--template",
        type=Path,
        help="Optional markdown template file with a {{ repo_sections }} placeholder",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Optional category config file that defines order and descriptions",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the generated markdown instead of writing the files",
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    command = args.command

    if command is None:
        parser.print_help()
        return 0

    if command == "collect":
        return run_collect(args)
    if command == "render":
        return run_render(args)
    if command == "generate-profile-readme":
        return run_generate_profile_readme(args)
    if command == "generate-metrics":
        return run_generate_metrics(args)
    raise ValueError(f"Unsupported command {command!r}.")


def run_collect(args: argparse.Namespace) -> int:
    collect_snapshot(
        org_name=args.org,
        token_env=args.token_env,
        cache_path=args.cache,
        status_prefix="repo-overview",
    )
    return 0


def run_render(args: argparse.Namespace) -> int:
    snapshot = load_snapshot(args.input)
    return render_all_outputs(
        snapshot,
        readme_output=args.readme_output,
        metrics_output=args.metrics_output,
        template_path=args.template,
        config_path=args.config,
        dry_run=args.dry_run,
        status_prefix="repo-overview",
    )


def run_generate_profile_readme(args: argparse.Namespace) -> int:
    snapshot = ensure_snapshot(
        org_name=args.org,
        cache_path=args.cache,
        token_env=args.token_env,
        refresh=args.refresh,
        status_prefix="repo-overview",
    )
    markdown = render_profile_readme(
        snapshot,
        template_path=args.template,
        config_path=args.config,
    )
    return write_or_print(
        markdown=markdown,
        output_path=args.output,
        dry_run=args.dry_run,
        status_prefix="repo-overview",
    )


def run_generate_metrics(args: argparse.Namespace) -> int:
    snapshot = ensure_snapshot(
        org_name=args.org,
        cache_path=args.cache,
        token_env=args.token_env,
        refresh=args.refresh,
        status_prefix="repo-overview",
    )
    markdown = render_metrics_report(snapshot)
    return write_or_print(
        markdown=markdown,
        output_path=args.output,
        dry_run=args.dry_run,
        status_prefix="repo-overview",
    )


def render_profile_readme(
    snapshot,
    *,
    template_path: Path | None,
    config_path: Path | None,
) -> str:
    template = load_template(template_path)
    config = load_config(config_path)
    return render_readme(
        list(snapshot.repos),
        template=template,
        config=config,
        org_name=snapshot.org_name,
    )


def write_or_print(
    *,
    markdown: str,
    output_path: Path,
    dry_run: bool,
    status_prefix: str,
) -> int:
    if dry_run:
        print(markdown)
        return 0

    write_text_file(path=output_path, content=markdown, status_prefix=status_prefix)
    return 0


def render_all_outputs(
    snapshot,
    *,
    readme_output: Path,
    metrics_output: Path,
    template_path: Path | None,
    config_path: Path | None,
    dry_run: bool,
    status_prefix: str,
) -> int:
    readme_markdown = render_profile_readme(
        snapshot,
        template_path=template_path,
        config_path=config_path,
    )
    metrics_markdown = render_metrics_report(snapshot)

    if dry_run:
        print("<!-- profile README -->")
        print(readme_markdown.rstrip())
        print()
        print("<!-- metrics report -->")
        print(metrics_markdown.rstrip())
        return 0

    write_text_file(
        path=readme_output,
        content=readme_markdown,
        status_prefix=status_prefix,
    )
    write_text_file(
        path=metrics_output,
        content=metrics_markdown,
        status_prefix=status_prefix,
    )
    return 0


def write_text_file(*, path: Path, content: str, status_prefix: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print_status(f"Wrote {path}", prefix=status_prefix)
