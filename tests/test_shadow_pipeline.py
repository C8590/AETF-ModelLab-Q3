from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from model_lab.kronos_adapter import KronosPredictionResult
from model_lab.shadow_pipeline import KronosShadowPipeline


@dataclass
class FakeConfig:
    model_name: str = "fake-kronos"
    tokenizer_name: str = "fake-tokenizer"
    device: str = "cpu"


class FakeAdapter:
    config = FakeConfig()

    def predict(self, df, **kwargs):
        if str(df["close"].iloc[-1]).startswith("999"):
            raise RuntimeError("simulated single-name failure")
        pred_len = kwargs["pred_len"]
        last_close = float(df["close"].iloc[-1])
        pred_df = pd.DataFrame(
            {
                "timestamps": kwargs["y_timestamp"],
                "open": [last_close] * pred_len,
                "high": [last_close * 1.02] * pred_len,
                "low": [last_close * 0.99] * pred_len,
                "close": [last_close * 1.01] * pred_len,
            }
        )
        return KronosPredictionResult(
            pred_df=pred_df,
            metadata={
                "model_name": self.config.model_name,
                "tokenizer_name": self.config.tokenizer_name,
                "device": self.config.device,
                "finished_at": "2026-06-03 12:00:00",
            },
        )


def write_kline(path: Path, *, fail_marker: bool = False) -> None:
    rows = 6
    closes = [10.0 + i * 0.1 for i in range(rows)]
    if fail_marker:
        closes[-1] = 999.0
    pd.DataFrame(
        {
            "timestamps": pd.date_range("2026-05-25", periods=rows, freq="B"),
            "open": closes,
            "high": [v + 0.1 for v in closes],
            "low": [v - 0.1 for v in closes],
            "close": closes,
            "volume": [1000] * rows,
            "amount": [10000] * rows,
        }
    ).to_csv(path, index=False)


def test_shadow_pipeline_single_failure_does_not_stop_batch(tmp_path: Path):
    kline_dir = tmp_path / "kline"
    kline_dir.mkdir()
    ok_path = kline_dir / "ok.csv"
    fail_path = kline_dir / "fail.csv"
    write_kline(ok_path)
    write_kline(fail_path, fail_marker=True)
    snapshot_path = tmp_path / "snapshot.csv"
    output_path = tmp_path / "shadow.csv"
    pd.DataFrame(
        {
            "candidate_rank": [2, 1],
            "trade_date": ["2026-06-03", "2026-06-03"],
            "code": ["FAIL", "PASS"],
            "name": ["失败样本", "通过样本"],
            "close": [999.0, 10.5],
            "kline_csv_path": [str(fail_path), str(ok_path)],
        }
    ).to_csv(snapshot_path, index=False)

    pipeline = KronosShadowPipeline(FakeAdapter(), project_root=tmp_path)
    result = pipeline.run_candidate_shadow_predictions(
        candidate_snapshot_path=snapshot_path,
        output_csv_path=output_path,
        lookback=5,
        pred_len=3,
        sample_count=1,
        T=1.0,
        top_p=0.9,
    )

    assert output_path.exists()
    assert result["code"].tolist() == ["PASS", "FAIL"]
    assert result["model_status"].tolist() == ["PASS", "FAIL"]
    assert result.loc[result["code"] == "FAIL", "error_message"].iloc[0] == "simulated single-name failure"


def test_run_kronos_shadow_daily_import_has_no_side_effects():
    import scripts.run_kronos_shadow_daily as shadow_script

    assert callable(shadow_script.main)
    assert callable(shadow_script.run)
