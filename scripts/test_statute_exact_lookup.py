#!/usr/bin/env python3
"""Local CLI test script for statute exact lookup adapter."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from retrieval.statutes.exact_lookup import StatuteExactLookupService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Test local statute exact lookup")
    parser.add_argument("--statute-id", help="authoritative statute_id")
    parser.add_argument("--code-slug", help="code_slug value")
    parser.add_argument("--code-label", help="code_label value")
    parser.add_argument("--article-no", help="article_no value")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    service = StatuteExactLookupService.from_default_paths()

    result = None
    if args.statute_id:
        result = service.lookup_by_statute_id(args.statute_id)
    elif args.code_slug and args.article_no:
        result = service.lookup_by_code_slug_and_article_no(args.code_slug, args.article_no)
    elif args.code_label and args.article_no:
        result = service.lookup_by_code_label_and_article_no(args.code_label, args.article_no)
    else:
        print(
            "Invalid arguments: provide --statute-id OR (--code-slug + --article-no) OR (--code-label + --article-no)",
            file=sys.stderr,
        )
        return 2

    if result is None:
        print("No statute record found for the provided lookup arguments.", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
