from __future__ import annotations

from pathlib import Path

import pandas as pd

from .crawler import UrlRecord


def export_urls_to_excel(records: list[UrlRecord], output_path: Path) -> None:
    dataframe = pd.DataFrame(
        [
            {
                "url": record.url,
                "depth": record.depth,
                "status_code": record.status_code,
                "source_url": record.source_url,
            }
            for record in records
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_excel(output_path, index=False, sheet_name="urls")
