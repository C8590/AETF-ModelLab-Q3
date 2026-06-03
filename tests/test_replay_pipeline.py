from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from model_lab.kronos_adapter import KronosPredictionResult
from model_lab.replay_pipeline import KronosHistoricalReplayPipeline, ReplayPipelineConfig


@dataclass
class FakeConfig:
    model_name: str = "fake-kronos"
    tokenizer_name: str = "fake-tokenizer"
    device: str = "cpu"


class FakeAdapter:
    config = FakeConfig()

    def predict(self, df, **kwargs):
        if float(df["close"].iloc[-1]) > 900:
            raise RuntimeError("simulated replay failure")
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
            },
        )


def write_replay_kline(path: Path, *, fail_marker: bool = False) -> None:
    rows = 12
    closes = [10.0 + i * 0.1 for i in range(rows)]
    if fail_marker:
        closes[5] = 999.0
    pd.DataFrame(
        {
            "timestamps": pd.date_range("2026-01-01", periods=rows, freq="B"),
            "open": closes,
            "high": [v + 0.2 for v in closes],
            "low": [max(v - 0.2, 0.1) for v in closes],
            "close": closes,
            "volume": [1000] * rows,
            "amount": [10000] * rows,
        }
    ).to_csv(path, index=False)


def test_replay_pipeline_single_case_failure_does_not_stop_batch(tmp_path: Path):
    ok_kline = tmp_path / "ok.csv"
    fail_kline = tmp_path / "fail.csv"
    write_replay_kline(ok_kline)
    write_replay_kline(fail_kline, fail_marker=True)
    cases_path = tmp_path / "cases.csv"
    output_predictions = tmp_path / "predictions.csv"
    output_metrics = tmp_path / "metrics.csv"
    report_path = tmp_path / "report.md"
    as_of_date = "2026-01-08"
    pd.DataFrame(
        {
            "replay_id": ["ok_case", "fail_case"],
            "as_of_date": [as_of_date, as_of_date],
            "symbol": ["OK", "FAIL"],
            "display_name": ["通过样本", "失败样本"],
            "candidate_rank": [1, 2],
            "left_score": [80.0, 70.0],
            "kline_path": [str(ok_kline), str(fail_kline)],
            "notes": ["demo", "demo"],
        }
    ).to_csv(cases_path, index=False)

    pipeline = KronosHistoricalReplayPipeline(
        FakeAdapter(),
        ReplayPipelineConfig(
            replay_cases_path=cases_path,
            output_predictions_path=output_predictions,
            output_metrics_path=output_metrics,
            report_path=report_path,
            lookback=4,
            pred_len=3,
            sample_count=1,
            max_cases=2,
            project_root=tmp_path,
        ),
    )

    replay_df, metrics = pipeline.run()

    assert output_predictions.exists()
    assert output_metrics.exists()
    assert replay_df["model_status"].tolist() == ["PASS", "FAIL"]
    assert replay_df.loc[replay_df["symbol"] == "FAIL", "error_message"].iloc[0] == "simulated replay failure"
    assert metrics["case_count"] == 2
    assert metrics["success_count"] == 1
    assert metrics["fail_count"] == 1


def test_replay_result_has_no_forbidden_trading_fields(tmp_path: Path):
    kline = tmp_path / "ok.csv"
    write_replay_kline(kline)
    cases_path = tmp_path / "cases.csv"
    pd.DataFrame(
        {
            "replay_id": ["ok_case"],
            "as_of_date": ["2026-01-08"],
            "symbol": ["OK"],
            "display_name": ["通过样本"],
            "candidate_rank": [1],
            "left_score": [80.0],
            "kline_path": [str(kline)],
            "notes": ["demo"],
        }
    ).to_csv(cases_path, index=False)
    pipeline = KronosHistoricalReplayPipeline(
        FakeAdapter(),
        ReplayPipelineConfig(
            replay_cases_path=cases_path,
            output_predictions_path=tmp_path / "predictions.csv",
            output_metrics_path=tmp_path / "metrics.csv",
            report_path=tmp_path / "report.md",
            lookback=4,
            pred_len=3,
            project_root=tmp_path,
        ),
    )

    replay_df, _ = pipeline.run()

    lowered = " ".join(replay_df.columns).lower()
    for forbidden in ["buy", "sell", "order", "trade", "signal"]:
        assert forbidden not in lowered


def test_run_kronos_historical_replay_import_has_no_side_effects():
    import scripts.run_kronos_historical_replay as replay_script

    assert callable(replay_script.main)
    assert callable(replay_script.run)
