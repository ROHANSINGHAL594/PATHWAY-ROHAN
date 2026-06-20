"""Utilities for ingesting SLA metrics from PDFs or manual chat input.

This module replaces the old `backend/extract` helpers so the contract parser
agent can be run without importing that package. It provides:
- PDF text extraction via PyMuPDF
- Metric extraction via Anthropic Claude
- Manual CLI collection of metric definitions
- JSON persistence helpers so downstream phases can reuse the metrics file
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import fitz  # type: ignore
except ImportError:  # pragma: no cover
    fitz = None

from anthropic import Anthropic

ANTHROPIC_METRICS_MODEL = os.getenv("ANTHROPIC_METRICS_MODEL", "claude-sonnet-4-5-20250929")


def _get_claude_client(api_key: Optional[str] = None) -> Anthropic:
    key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY missing. Set the env var or pass --anthropic_api_key."
        )
    return Anthropic(api_key=key)

def extract_pdf_text(pdf_path: str) -> str:
    """Return the concatenated text of every page in the PDF."""

    if fitz is None:
        raise RuntimeError("PyMuPDF is required for PDF extraction. Install via `pip install PyMuPDF`.")

    doc = fitz.open(pdf_path)
    try:
        return "".join(page.get_text() for page in doc)
    finally:
        doc.close()


def extract_sla_metrics_with_claude(
    text: str,
    api_key: Optional[str] = None,
    max_chars: int = 30_000,
    additional_context: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Use Claude to summarize SLA metrics from raw contract text.
    
    Args:
        text: The contract text to extract metrics from
        api_key: Optional Anthropic API key
        max_chars: Maximum characters to process from text
        additional_context: Optional additional context/description to help with extraction
    """

    client = _get_claude_client(api_key)
    snippet = text[:max_chars]
    
    context_section = ""
    if additional_context and additional_context.strip():
        context_section = f"\n\nAdditional Context/Requirements:\n{additional_context.strip()}\n\nIMPORTANT: Use BOTH the contract text above AND this additional context/description to extract and understand the metrics. Combine information from both sources to get a complete picture of the requirements. The additional context may provide clarification, specific requirements, or additional details that complement the contract text."

    user_prompt = f"""Extract all SLA (Service Level Agreement) metrics from the following contract text that can be classified into one of three performance categories.{context_section}

Categories:
- latency: Metrics measuring time durations for system responses, resolutions, processing, or fulfillment.
- uptime: Metrics measuring system availability or uptime percentages.
- error_rate: Metrics measuring rates of errors, defects, failures, or incidents.

For each qualifying SLA metric found, provide:
- metric_name: The name of the metric
- description: A detailed description of what is measured and the requirements
- category: One of "latency", "uptime", or "error_rate"

Do not include administrative metrics like RCA submission times, maintenance schedules, or success rates unless they directly fit the above categories.

Return ONLY a valid JSON array with this exact structure:
[
  {{
    "metric_name": "metric name here",
    "description": "detailed description here",
    "category": "latency/error/uptime"
  }}
]

Rules:
1. Include all actual measurable SLA metrics that fit the three categories.
2. Each metric must have name, description, and category.
3. Return valid JSON only, no additional text or markdown.
4. If no qualifying SLA metrics are found, return an empty array: [].

Contract Text:
{snippet}
"""

    response = client.messages.create(
        model=ANTHROPIC_METRICS_MODEL,
        max_tokens=4000,
        system="You are an expert SLA analyst who outputs strict JSON.",
        messages=[
            {"role": "user", "content": user_prompt},
        ],
    )
    response_text = response.content[0].text.strip()

    if response_text.startswith("```"):
        # Remove optional ```json fences
        response_text = response_text.strip("`").strip()
        if response_text.startswith("json"):
            response_text = response_text[4:].strip()

    metrics = json.loads(response_text)
    if not isinstance(metrics, list):
        raise ValueError("Claude response was not a JSON array.")

    for metric in metrics:
        if not isinstance(metric, dict):
            raise ValueError(f"Metric entry is not a dict: {metric}")
        for key in ("metric_name", "description", "category"):
            if key not in metric:
                raise ValueError(f"Metric missing '{key}': {metric}")

    return metrics


def save_metrics_json(
    metrics: List[Dict[str, Any]],
    output_path: Path,
    source_document: str,
    method: str,
) -> None:
    """Persist metrics along with provenance metadata."""

    payload = {
        "source_document": source_document,
        "total_metrics": len(metrics),
        "extraction_date": datetime.utcnow().isoformat() + "Z",
        "extraction_method": method,
        "metrics": metrics,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def load_metrics_from_file(path: Path) -> List[Dict[str, Any]]:
    """Load metrics from an existing JSON file (dict with 'metrics' or raw list)."""

    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "metrics" in data:
        metrics = data["metrics"]
    elif isinstance(data, list):
        metrics = data
    else:
        raise ValueError(
            "Metrics file must be either a list or an object containing a 'metrics' field"
        )

    if not isinstance(metrics, list):
        raise ValueError("The 'metrics' entry must be a list.")

    return metrics


def generate_metrics_from_pdf(
    pdf_path: str,
    output_dir: Path,
    api_key: Optional[str] = None,
    additional_context: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Path]:
    """Extract metrics from a PDF and save them into output_dir.
    
    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save extracted metrics
        api_key: Optional Anthropic API key
        additional_context: Optional additional context/description to help with extraction
    """

    pdf_path_obj = Path(pdf_path)
    if not pdf_path_obj.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    text = extract_pdf_text(str(pdf_path_obj))
    metrics = extract_sla_metrics_with_claude(text, api_key=api_key, additional_context=additional_context)

    output_path = output_dir / f"{pdf_path_obj.stem}_sla_metrics.json"
    save_metrics_json(metrics, output_path, pdf_path_obj.name, "pdf_extraction_claude")
    return metrics, output_path


def gather_metrics_via_cli(output_dir: Path) -> Tuple[List[Dict[str, Any]], Path]:
    """Interactively collect metrics via CLI "chat" and save them to JSON."""

    print("\nManual SLA Metric Entry")
    print("Enter one metric at a time. Leave the metric name blank to finish.")

    metrics: List[Dict[str, Any]] = []
    idx = 1
    while True:
        name = input(f"Metric #{idx} name (leave blank to finish): ").strip()
        if not name:
            if metrics:
                break
            print("You must enter at least one metric before finishing.")
            continue

        description = input("Description: ").strip()
        category = input("Category [latency/uptime/error_rate] (optional): ").strip().lower()
        if category not in {"latency", "uptime", "error_rate"}:
            category = "unspecified"

        metrics.append(
            {
                "metric_name": name,
                "description": description,
                "category": category,
            }
        )
        idx += 1

    output_path = output_dir / "manual_sla_metrics.json"
    save_metrics_json(metrics, output_path, "manual_input", "manual_chat")
    print(f"Saved manual metrics to {output_path}")
    return metrics, output_path
