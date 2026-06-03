from pathlib import Path

import pandas as pd
import pytest

from model_lab.data_loader import read_candidate_snapshot, read_kline_csv


def test_candidate_snapshot_missing_required_columns_raises(tmp_path: Path):
    path = tmp_path / "candidates.csv"
    pd.DataFrame({"code": ["510300"], "close": [4.0]}).to_csv(path, index=False)

    with pytest.raises(ValueError, match="candidate snapshot missing columns"):
        read_candidate_snapshot(path)


def test_candidate_snapshot_loads_sorted_and_limited(tmp_path: Path):
    path = tmp_path / "candidates.csv"
    pd.DataFrame(
        {
            "candidate_rank": [2, 1, 3],
            "trade_date": ["2026-06-02"] * 3,
            "code": ["159915", "510300", "588000"],
            "name": ["创业板ETF", "沪深300ETF", "科创ETF"],
            "close": [2.0, 4.0, 1.0],
            "kline_csv_path": ["b.csv", "a.csv", "c.csv"],
        }
    ).to_csv(path, index=False)

    loaded = read_candidate_snapshot(path, max_candidates=2)

    assert loaded["code"].tolist() == ["510300", "159915"]
    assert loaded["trade_date"].tolist() == ["2026-06-02", "2026-06-02"]


def test_kline_csv_loads_and_sorts_timestamps(tmp_path: Path):
    path = tmp_path / "kline.csv"
    pd.DataFrame(
        {
            "timestamps": ["2026-06-03", "2026-06-01", "2026-06-02"],
            "open": [3.0, 1.0, 2.0],
            "high": [3.2, 1.2, 2.2],
            "low": [2.8, 0.8, 1.8],
            "close": [3.1, 1.1, 2.1],
            "volume": [300, 100, 200],
            "amount": [3000, 1000, 2000],
        }
    ).to_csv(path, index=False)

    loaded = read_kline_csv(path)

    assert loaded["timestamps"].dt.strftime("%Y-%m-%d").tolist() == [
        "2026-06-01",
        "2026-06-02",
        "2026-06-03",
    ]
    assert loaded["close"].tolist() == [1.1, 2.1, 3.1]
