#!/usr/bin/env python3
"""Batch-generate case metadata v1 with short/medium/long routing.

Designed for long-running local jobs (e.g., RTX 4090 24GB, 10-hour batch window).
Primary model is configurable; default recommends Qwen3-8B-Instruct (4-bit).
Optional fallback model (e.g., Gemma-3-12B-IT) is only used for hard cases.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_MERGED_ROOT = Path("data/corpus/raw/macau_court_cases_full")
DEFAULT_OUTPUT = Path("data/eval/model_generated_metadata_output.jsonl")
DEFAULT_SYSTEM_PROMPT = Path("prompts/case_metadata_v1_system.txt")
DEFAULT_USER_PROMPT = Path("prompts/case_metadata_v1_user.txt")
DEBUG_RAW_OUTPUT = Path("data/eval/debug_case_metadata_raw_outputs.jsonl")

FIXED_FIELDS = (
    "case_summary",
    "holding",
    "disputed_issues",
    "legal_basis",
    "reasoning_summary",
    "doctrinal_point",
)


@dataclass(frozen=True)
class CaseInput:
    sentence_id: str
    authoritative_case_number: str
    authoritative_decision_date: str
    language: str
    court: str
    case_type: str
    full_text: str


def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\u3000", " ")).strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate case_metadata_v1 via configurable local model backends")
    parser.add_argument("--merged-root", type=Path, default=DEFAULT_MERGED_ROOT)
    parser.add_argument("--manifest-path", type=Path, default=None)
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--system-prompt", type=Path, default=DEFAULT_SYSTEM_PROMPT)
    parser.add_argument("--user-prompt", type=Path, default=DEFAULT_USER_PROMPT)

    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int, default=0, help="exclusive index; 0 means until file end")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--resume", action="store_true", help="skip sentence_id already present in output")

    parser.add_argument("--short-char-threshold", type=int, default=3800)
    parser.add_argument("--medium-char-threshold", type=int, default=14000)
    parser.add_argument("--medium-head-chars", type=int, default=2600)
    parser.add_argument("--medium-tail-chars", type=int, default=1800)
    parser.add_argument("--medium-reasoning-max-chars", type=int, default=2400)
    parser.add_argument("--long-snippet-max-chars", type=int, default=5200)

    parser.add_argument("--backend", default="transformers", choices=["transformers", "mock"])
    parser.add_argument("--model-name", default="Qwen/Qwen3-8B-Instruct")
    parser.add_argument("--quantization", default="awq-4bit", choices=["awq-4bit", "gptq-4bit", "none"])
    parser.add_argument("--device-map", default="auto")

    parser.add_argument("--fallback-enabled", action="store_true")
    parser.add_argument("--fallback-model-name", default="google/gemma-3-12b-it")
    parser.add_argument("--fallback-backend", default="transformers", choices=["transformers", "mock"])
    parser.add_argument("--fallback-quantization", default="awq-4bit", choices=["awq-4bit", "gptq-4bit", "none"])
    parser.add_argument("--fallback-on-long", action="store_true")

    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--top-p", type=float, default=0.85, dest="top_p")
    parser.add_argument("--max-new-tokens", type=int, default=260)
    parser.add_argument("--repetition-penalty", type=float, default=1.05)
    parser.add_argument("--do-sample", action="store_true", default=False)
    parser.add_argument("--max-retries", type=int, default=2)

    parser.add_argument("--print-every", type=int, default=50)

    parser.add_argument("--language-filter", default="", help="optional language filter, e.g. zh or pt")

    return parser.parse_args()


def load_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def load_done_ids(path: Path) -> set[str]:
    done: set[str] = set()
    if not path.exists():
        return done
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            raw = line.strip()
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue
            sid = normalize_space(payload.get("sentence_id"))
            if sid:
                done.add(sid)
    return done


def read_cases(
    merged_root: Path,
    manifest_path: Path,
    start: int,
    end: int,
    limit: int,
    language_filter: str,
) -> list[CaseInput]:

    rows: list[CaseInput] = []
    with manifest_path.open("r", encoding="utf-8") as fh:
        for idx, line in enumerate(fh):
            if idx < max(start, 0):
                continue
            if end > 0 and idx >= end:
                break
            raw = line.strip()
            if not raw:
                continue
            payload = json.loads(raw)
            sentence_id = normalize_space(payload.get("sentence_id"))
            if not sentence_id:
                continue

            language = normalize_space(payload.get("language"))
            if language_filter and language.lower() != language_filter.lower():
                continue

            metadata_rel = normalize_space(payload.get("metadata_path"))
            full_text_rel = normalize_space(payload.get("full_text_path"))
            full_text = ""
            case_type = ""

            if metadata_rel:
                metadata_path = merged_root / metadata_rel
                if metadata_path.exists():
                    md = json.loads(metadata_path.read_text(encoding="utf-8"))
                    case_type = normalize_space(md.get("source_list_case_type"))

            if full_text_rel:
                full_path = merged_root / full_text_rel
                if full_path.exists():
                    full_text = normalize_space(full_path.read_text(encoding="utf-8"))

            rows.append(
                CaseInput(
                    sentence_id=sentence_id,
                    authoritative_case_number=normalize_space(payload.get("authoritative_case_number")),
                    authoritative_decision_date=normalize_space(payload.get("authoritative_decision_date")),
                    language=normalize_space(payload.get("language")),
                    court=normalize_space(payload.get("court")),
                    case_type=case_type,
                    full_text=full_text,
                )
            )
            if limit > 0 and len(rows) >= limit:
                break
    return rows


def choose_route(text: str, short_threshold: int, medium_threshold: int) -> str:
    n = len(text)
    if n <= short_threshold:
        return "short"
    if n <= medium_threshold:
        return "medium"
    return "long"


def clip(text: str, max_chars: int) -> str:
    value = normalize_space(text)
    if len(value) <= max_chars:
        return value
    return value[: max_chars - 3] + "..."


def extract_heading_blocks(text: str, heading_patterns: list[str], stop_patterns: list[str]) -> list[str]:
    if not text:
        return []
    heading = "|".join(heading_patterns)
    stop = "|".join(stop_patterns)
    pattern = re.compile(
        rf"(?:{heading})\s*[:：]?\s*(.+?)(?=(?:{stop})\s*[:：]?|$)",
        flags=re.IGNORECASE | re.DOTALL,
    )
    return [normalize_space(m.group(1)) for m in pattern.finditer(text) if normalize_space(m.group(1))]


def prepare_medium_text(case: CaseInput, args: argparse.Namespace) -> str:
    text = case.full_text
    if not text:
        return ""
    head = text[: args.medium_head_chars]
    tail = text[-args.medium_tail_chars :] if len(text) > args.medium_tail_chars else ""
    reasoning_blocks = extract_heading_blocks(
        text,
        heading_patterns=[r"理由", r"理由說明", r"法律分析", r"fundamenta[cç][ãa]o", r"fundamentos"],
        stop_patterns=[r"裁判", r"決定", r"結論", r"decis[ãa]o"],
    )
    reasoning = " ".join(reasoning_blocks)
    reasoning = clip(reasoning, args.medium_reasoning_max_chars)
    combined = "\n\n".join([normalize_space(head), reasoning, normalize_space(tail)])
    return clip(combined, args.medium_head_chars + args.medium_tail_chars + args.medium_reasoning_max_chars)


def select_long_snippets(case: CaseInput, args: argparse.Namespace) -> str:
    text = case.full_text
    if not text:
        return ""
    snippets: list[str] = []
    snippets.append(text[:1800])

    heading_priority = [
        ([r"爭議焦點", r"主要問題", r"上訴理由", r"quest[õo]es?"], [r"理由", r"fundamenta"]),
        ([r"理由", r"法律分析", r"fundamenta[cç][ãa]o"], [r"裁判", r"決定", r"結論", r"decis[ãa]o"]),
        ([r"裁判", r"決定", r"主文", r"decis[ãa]o", r"acordam"], [r"日期", r"簽署", r"assinado"]),
    ]
    for headings, stops in heading_priority:
        blocks = extract_heading_blocks(text, headings, stops)
        if blocks:
            snippets.append(blocks[0])

    sentence_hits: list[str] = []
    split_sents = re.split(r"(?<=[。！？!?；;\.])\s+", text)
    keywords = ["第", "條", "裁定", "判決", "駁回", "維持", "改判", "理由", "本院認為", "princ", "art"]
    for sent in split_sents:
        s = normalize_space(sent)
        if not s:
            continue
        if any(k.lower() in s.lower() for k in keywords):
            sentence_hits.append(s)
        if len(" ".join(sentence_hits)) >= 2200:
            break
    if sentence_hits:
        snippets.append(" ".join(sentence_hits))

    snippets.append(text[-1500:])
    merged = "\n\n".join([normalize_space(s) for s in snippets if normalize_space(s)])
    return clip(merged, args.long_snippet_max_chars)


def prepare_case_text(case: CaseInput, route: str, args: argparse.Namespace) -> str:
    if route == "short":
        return case.full_text
    if route == "medium":
        return prepare_medium_text(case, args)
    return select_long_snippets(case, args)


def safe_json_extract(raw: str) -> dict[str, Any] | None:
    if not raw:
        return None

    text = raw.strip()

    # strip common markdown fences
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)

    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None

    candidate = text[start : end + 1]

    try:
        obj = json.loads(candidate)
    except json.JSONDecodeError:
        return None

    return obj if isinstance(obj, dict) else None



def normalize_model_output(payload: dict[str, Any] | None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "case_summary": "",
        "holding": "",
        "disputed_issues": [],
        "legal_basis": [],
        "reasoning_summary": "",
        "doctrinal_point": "",
    }
    if not payload:
        return result

    for field in FIXED_FIELDS:
        value = payload.get(field)
        if field in ("disputed_issues", "legal_basis"):
            if isinstance(value, list):
                cleaned = [normalize_space(v) for v in value if normalize_space(v)]
            elif isinstance(value, str):
                cleaned = [normalize_space(v) for v in re.split(r"[\n,，、;；]+", value) if normalize_space(v)]
            else:
                cleaned = []
            uniq: list[str] = []
            seen: set[str] = set()
            for item in cleaned:
                k = item.lower()
                if k in seen:
                    continue
                seen.add(k)
                uniq.append(item)
            result[field] = uniq
        else:
            result[field] = normalize_space(value)
    return result

def append_debug_raw_output(
    *,
    sentence_id: str,
    authoritative_case_number: str,
    route: str,
    raw_output: str,
    user_prompt: str,
    fallback: bool,
) -> None:
    DEBUG_RAW_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with DEBUG_RAW_OUTPUT.open("a", encoding="utf-8") as fh:
        fh.write(
            json.dumps(
                {
                    "sentence_id": sentence_id,
                    "authoritative_case_number": authoritative_case_number,
                    "route": route,
                    "fallback": fallback,
                    "raw_output": raw_output,
                    "user_prompt_preview": user_prompt[:3000],
                },
                ensure_ascii=False,
            )
            + "\n"
        )


def has_missing_fields(output: dict[str, Any]) -> bool:
    for field in FIXED_FIELDS:
        value = output.get(field)
        if isinstance(value, list) and len(value) == 0:
            return True
        if isinstance(value, str) and not normalize_space(value):
            return True
    return False


class GenerationClient:
    def generate(self, system_prompt: str, user_prompt: str, args: argparse.Namespace, *, fallback: bool = False) -> str:
        raise NotImplementedError


class MockClient(GenerationClient):
    def generate(self, system_prompt: str, user_prompt: str, args: argparse.Namespace, *, fallback: bool = False) -> str:
        del system_prompt, args, fallback
        if "[抽取片段]" not in user_prompt:
            return "{}"
        return json.dumps(
            {
                "case_summary": "",
                "holding": "",
                "disputed_issues": [],
                "legal_basis": [],
                "reasoning_summary": "",
                "doctrinal_point": "",
            },
            ensure_ascii=False,
        )


class TransformersClient(GenerationClient):
    def __init__(self, model_name: str, quantization: str, device_map: str) -> None:
        try:
            import torch  # type: ignore
            from transformers import AutoModelForCausalLM, AutoTokenizer  # type: ignore
        except Exception as exc:  # pragma: no cover - runtime dependency
            raise RuntimeError("transformers backend not available; install torch+transformers first") from exc

        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)

        model_kwargs: dict[str, Any] = {"trust_remote_code": True, "device_map": device_map}
        if quantization in {"awq-4bit", "gptq-4bit"}:
            # Keep framework/model configurable: when quantized weights are provided,
            # transformers will load by model metadata; here we avoid hard lock-in.
            model_kwargs["torch_dtype"] = torch.float16

        self.model = AutoModelForCausalLM.from_pretrained(model_name, **model_kwargs)

    def generate(self, system_prompt: str, user_prompt: str, args: argparse.Namespace, *,
                 fallback: bool = False) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)

        gen_kwargs: dict[str, Any] = {
            "max_new_tokens": args.max_new_tokens,
            "repetition_penalty": args.repetition_penalty,
            "do_sample": bool(args.do_sample),
            "pad_token_id": self.tokenizer.eos_token_id,
        }

        if gen_kwargs["do_sample"]:
            gen_kwargs["temperature"] = args.temperature
            gen_kwargs["top_p"] = args.top_p

        with self.torch.no_grad():
            output = self.model.generate(**inputs, **gen_kwargs)

        decoded = self.tokenizer.decode(
            output[0][inputs["input_ids"].shape[1]:],
            skip_special_tokens=True,
        )
        return decoded


def build_client(backend: str, model_name: str, quantization: str, device_map: str) -> GenerationClient:
    if backend == "mock":
        return MockClient()
    return TransformersClient(model_name=model_name, quantization=quantization, device_map=device_map)


def render_user_prompt(template: str, case: CaseInput, route: str, case_text: str) -> str:
    return template.format(
        sentence_id=case.sentence_id,
        authoritative_case_number=case.authoritative_case_number,
        language=case.language,
        route=route,
        case_text=case_text,
    )


def generate_with_retries(
    client: GenerationClient,
    *,
    sentence_id: str,
    authoritative_case_number: str,
    route: str,
    system_prompt: str,
    user_prompt: str,
    args: argparse.Namespace,
    fallback: bool,
) -> tuple[dict[str, Any], bool]:
    for _ in range(max(args.max_retries, 1) + 1):
        raw = client.generate(system_prompt, user_prompt, args, fallback=fallback)
        parsed = safe_json_extract(raw)
        normalized = normalize_model_output(parsed)

        if parsed is not None:
            return normalized, True

        append_debug_raw_output(
            sentence_id=sentence_id,
            authoritative_case_number=authoritative_case_number,
            route=route,
            raw_output=raw,
            user_prompt=user_prompt,
            fallback=fallback,
        )

    return normalize_model_output(None), False




def main() -> None:
    args = parse_args()
    manifest_path = args.manifest_path or (args.merged_root / "manifest.jsonl")

    system_prompt = load_prompt(args.system_prompt)
    user_template = load_prompt(args.user_prompt)

    primary_client = build_client(
        backend=args.backend,
        model_name=args.model_name,
        quantization=args.quantization,
        device_map=args.device_map,
    )

    fallback_client: GenerationClient | None = None
    if args.fallback_enabled:
        fallback_client = build_client(
            backend=args.fallback_backend,
            model_name=args.fallback_model_name,
            quantization=args.fallback_quantization,
            device_map=args.device_map,
        )

    cases = read_cases(
        merged_root=args.merged_root,
        manifest_path=manifest_path,
        start=args.start,
        end=args.end,
        limit=args.limit,
        language_filter=args.language_filter,
    )

    done_ids = load_done_ids(args.output_path) if args.resume else set()
    args.output_path.parent.mkdir(parents=True, exist_ok=True)

    processed = 0
    skipped = 0
    with args.output_path.open("a" if args.resume else "w", encoding="utf-8") as out:
        for case in cases:
            if args.resume and case.sentence_id in done_ids:
                skipped += 1
                continue

            route = choose_route(case.full_text, args.short_char_threshold, args.medium_char_threshold)
            routed_text = prepare_case_text(case, route, args)
            user_prompt = render_user_prompt(user_template, case, route, routed_text)

            result, json_ok = generate_with_retries(
                primary_client,
                sentence_id=case.sentence_id,
                authoritative_case_number=case.authoritative_case_number,
                route=route,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                args=args,
                fallback=False,
            )

            model_used = args.model_name
            backend_used = args.backend
            fallback_applied = False
            needs_fallback = (
                fallback_client is not None
                and (has_missing_fields(result) or not json_ok or (route == "long" and args.fallback_on_long))
            )
            if needs_fallback:
                result_fb, json_ok_fb = generate_with_retries(
                    fallback_client,
                    sentence_id=case.sentence_id,
                    authoritative_case_number=case.authoritative_case_number,
                    route=route,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    args=args,
                    fallback=True,
                )

                if json_ok_fb and (not has_missing_fields(result_fb) or not json_ok):
                    result = result_fb
                    json_ok = json_ok_fb
                    model_used = args.fallback_model_name
                    backend_used = args.fallback_backend
                    fallback_applied = True

            row = {
                "sentence_id": case.sentence_id,
                "authoritative_case_number": case.authoritative_case_number,
                "core_case_metadata": {
                    "authoritative_case_number": case.authoritative_case_number,
                    "authoritative_decision_date": case.authoritative_decision_date,
                    "language": case.language,
                    "court": case.court,
                },
                "generated_digest_metadata": result,
                "case_metadata_v1": result,
                "generation_meta": {
                    "route": route,
                    "backend": backend_used,
                    "model_name": model_used,
                    "quantization": args.quantization if not fallback_applied else args.fallback_quantization,
                    "json_valid": json_ok,
                    "fallback_applied": fallback_applied,
                    "input_chars_full_text": len(case.full_text),
                    "input_chars_sent": len(routed_text),
                },
            }
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            processed += 1

            if args.print_every > 0 and processed % args.print_every == 0:
                print(
                    json.dumps(
                        {
                            "processed": processed,
                            "skipped": skipped,
                            "last_sentence_id": case.sentence_id,
                            "route": route,
                        },
                        ensure_ascii=False,
                    )
                )

    print(
        json.dumps(
            {
                "status": "ok",
                "manifest_path": manifest_path.as_posix(),
                "output_path": args.output_path.as_posix(),
                "input_cases": len(cases),
                "processed": processed,
                "skipped": skipped,
                "backend": args.backend,
                "model_name": args.model_name,
                "fallback_enabled": bool(args.fallback_enabled),
                "fallback_model_name": args.fallback_model_name,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
