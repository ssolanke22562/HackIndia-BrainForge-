import csv
import logging
from pathlib import Path
from typing import Dict, Any
import pandas as pd
from tabulate import tabulate

logger = logging.getLogger(__name__)

def sniff_csv_delimiter(file_path: Path) -> str:
    """Sniff CSV delimiter from file header sample."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            sample = f.read(4096)
            if sample:
                sniffer = csv.Sniffer()
                dialect = sniffer.sniff(sample)
                return dialect.delimiter
    except Exception as e:
        logger.debug(f"CSV Sniffer failed ({e}), defaulting to comma.")
    return ","

def parse_csv(file_path: str | Path) -> Dict[str, Any]:
    """
    Automated dialect sniffing, schema profiling, and Markdown serialization
    for CSV and Excel tabular datasets.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Spreadsheet file not found: {path}")

    title = path.stem.replace("_", " ").replace("-", " ").title()
    is_excel = path.suffix.lower() in [".xlsx", ".xls"]

    try:
        if is_excel:
            df = pd.read_excel(path)
        else:
            delimiter = sniff_csv_delimiter(path)
            df = pd.read_csv(path, sep=delimiter, on_bad_lines="skip")
    except Exception as e:
        logger.error(f"Failed to read spreadsheet '{path.name}': {e}")
        # Fallback raw line reading
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            raw_text = f.read(5000)
        return {
            "text": f"```csv\n{raw_text}\n```",
            "title": title,
            "row_count": 0,
            "col_count": 0,
            "metadata": {"format": "CSV", "error": str(e)}
        }

    row_count, col_count = df.shape
    columns = list(df.columns)
    
    # 1. Generate Schema Profile
    schema_lines = [
        f"### Tabular Dataset: {title}",
        f"- **Rows:** {row_count:,} | **Columns:** {col_count}",
        f"- **Column Schema:**",
    ]
    for col in columns:
        dtype = str(df[col].dtype)
        null_count = int(df[col].isnull().sum())
        schema_lines.append(f"  - `{col}` ({dtype}): {row_count - null_count}/{row_count} non-null values")

    # 2. Render Markdown Table
    if row_count <= 500:
        table_md = tabulate(df, headers="keys", tablefmt="pipe", showindex=False)
        content_text = "\n".join(schema_lines) + f"\n\n### Full Data Table:\n\n{table_md}"
    else:
        # Large dataset: Show schema + summary statistics + top/bottom sample rows
        head_sample = tabulate(df.head(5), headers="keys", tablefmt="pipe", showindex=False)
        tail_sample = tabulate(df.tail(5), headers="keys", tablefmt="pipe", showindex=False)
        
        # Numeric summary
        try:
            stats_df = df.describe().round(2)
            stats_md = tabulate(stats_df, headers="keys", tablefmt="pipe", showindex=True)
            stats_section = f"\n\n### Statistical Profile (Numeric Columns):\n\n{stats_md}"
        except Exception:
            stats_section = ""

        content_text = (
            "\n".join(schema_lines)
            + stats_section
            + f"\n\n### Sample Top 5 Rows:\n\n{head_sample}"
            + f"\n\n### Sample Bottom 5 Rows:\n\n{tail_sample}"
        )

    metadata = {
        "row_count": row_count,
        "column_count": col_count,
        "columns": [str(c) for c in columns],
        "format": "EXCEL" if is_excel else "CSV"
    }

    return {
        "text": content_text,
        "title": title,
        "row_count": row_count,
        "col_count": col_count,
        "metadata": metadata
    }
