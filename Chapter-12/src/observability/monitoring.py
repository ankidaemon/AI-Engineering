"""
Production monitoring.

`ProductionMonitor` polls LangSmith for the last hour of runs, computes latency,
error rate, token and cost figures, and raises alerts when any of them cross a
threshold. The threshold checking is a pure function (`check_thresholds`) so it
is easy to test without a LangSmith account: give it a metrics object and read
back the alerts.

The LangSmith client is injected. When none is given, alerts are logged instead
of posted, so this runs offline.
"""
import os
import asyncio
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class MetricThresholds:
    max_p95_latency_ms: int = 8000
    max_error_rate: float = 0.05
    max_hourly_cost_usd: float = 10.00
    min_run_volume: int = 10


@dataclass
class ProductionMetrics:
    period_start: datetime
    period_end: datetime
    run_count: int = 0
    error_count: int = 0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    alerts: list = field(default_factory=list)


def check_thresholds(metrics: ProductionMetrics, thresholds: MetricThresholds) -> list:
    """Pure function: compare metrics to thresholds and return a list of alerts."""
    alerts = []
    t = thresholds

    if metrics.p95_latency_ms > t.max_p95_latency_ms:
        alerts.append({
            "severity": "WARNING",
            "metric": "p95_latency",
            "message": f"P95 latency {metrics.p95_latency_ms:.0f}ms exceeds {t.max_p95_latency_ms}ms",
        })

    if metrics.run_count > 0:
        error_rate = metrics.error_count / metrics.run_count
        if error_rate > t.max_error_rate:
            alerts.append({
                "severity": "CRITICAL",
                "metric": "error_rate",
                "message": f"Error rate {error_rate:.1%} exceeds {t.max_error_rate:.1%}",
            })

    if metrics.estimated_cost_usd > t.max_hourly_cost_usd:
        alerts.append({
            "severity": "WARNING",
            "metric": "hourly_cost",
            "message": f"Hourly cost ${metrics.estimated_cost_usd:.2f} exceeds budget",
        })

    if 0 < metrics.run_count < t.min_run_volume:
        alerts.append({
            "severity": "INFO",
            "metric": "run_volume",
            "message": "Low run volume, possible upstream issue",
        })

    return alerts


class ProductionMonitor:
    def __init__(
        self,
        project_name: str,
        thresholds: Optional[MetricThresholds] = None,
        client=None,
        alert_webhook: Optional[str] = None,
        poll_interval_s: int = 300,
    ):
        self._project = project_name
        self._thresholds = thresholds or MetricThresholds()
        self._client = client
        self._webhook = alert_webhook or os.getenv("ALERT_WEBHOOK_URL", "")
        self._poll_interval = poll_interval_s
        self._running = False

    def stop(self) -> None:
        self._running = False

    async def start(self) -> None:
        self._running = True
        logger.info("Production monitor started for '%s'", self._project)
        while self._running:
            try:
                metrics = await self.collect_metrics(window_minutes=60)
                alerts = check_thresholds(metrics, self._thresholds)
                if alerts:
                    await self._send_alerts(alerts, metrics)
                logger.info(
                    "Monitor: %d runs, p95=%.0fms, errors=%d, cost=$%.4f",
                    metrics.run_count, metrics.p95_latency_ms,
                    metrics.error_count, metrics.estimated_cost_usd,
                )
            except Exception as exc:
                logger.error("Monitor error (continuing): %s", exc)
            await asyncio.sleep(self._poll_interval)

    async def collect_metrics(self, window_minutes: int = 60) -> ProductionMetrics:
        end = datetime.utcnow()
        start = end - timedelta(minutes=window_minutes)
        metrics = ProductionMetrics(period_start=start, period_end=end)

        client = self._client
        if client is None:
            try:
                from langsmith import Client
                client = Client()
            except Exception:
                return metrics  # no client available, return empty metrics

        try:
            runs = list(client.list_runs(
                project_name=self._project, start_time=start, end_time=end,
            ))
            metrics.run_count = len(runs)
            metrics.error_count = sum(1 for r in runs if getattr(r, "error", None))

            latencies = []
            for run in runs:
                st, et = getattr(run, "start_time", None), getattr(run, "end_time", None)
                if st and et:
                    latencies.append((et - st).total_seconds() * 1000)
                metrics.total_tokens += getattr(run, "total_tokens", 0) or 0

            if latencies:
                latencies.sort()
                metrics.p50_latency_ms = latencies[len(latencies) // 2]
                metrics.p95_latency_ms = latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))]

            # Self-hosted cost is compute time, approximated per token here.
            metrics.estimated_cost_usd = (metrics.total_tokens / 1_000_000) * 0.50
        except Exception as exc:
            logger.warning("Failed to collect metrics: %s", exc)

        return metrics

    async def _send_alerts(self, alerts: list, metrics: ProductionMetrics) -> None:
        if not self._webhook:
            logger.warning("ALERTS (no webhook configured): %s", alerts)
            return
        try:
            import httpx
            text = f"AI system alert for {self._project}: " + "; ".join(a["message"] for a in alerts)
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(self._webhook, json={"text": text})
        except Exception as exc:
            logger.error("Failed to send alert: %s", exc)
