"""
Pytest configuration для eval тестов.

Содержит фикстуру для автоматического запуска FastAPI сервиса перед тестами.
"""

import html
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx
import pytest

# Глобальное хранилище результатов eval-метрик для генерации HTML-отчёта
EVAL_REPORT_DATA: list[dict] = []

# Отключаем телеметрию deepeval (отправку на PostHog/Sentry), чтобы избежать SSL-ошибок в корп. сети
os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "YES")

# Конфигурация запуска сервиса
AGENT_STARTUP_TIMEOUT = int(os.getenv("AGENT_STARTUP_TIMEOUT", "60"))
AGENT_HEALTH_URL = os.getenv("AGENT_HEALTH_URL", "http://localhost:8080/health")
AGENT_START_COMMAND = os.getenv("AGENT_START_COMMAND", "uvicorn service.api:create_app --host 0.0.0.0 --port 8080 --workers 1")
SKIP_AGENT_START = os.getenv("SKIP_AGENT_START", "false").lower() == "true"


def pytest_configure(config):
    """Добавляем кастомные маркеры."""
    config.addinivalue_line(
        "markers", "eval_quality: тесты оценки качества агента (медленные, требуют LLM)"
    )


def wait_for_agent_health(url: str, timeout: int = 60, interval: float = 1.0) -> bool:
    """
    Ожидает готовности агента через health endpoint.

    Args:
        url: URL health endpoint
        timeout: Максимальное время ожидания (сек)
        interval: Интервал между проверками (сек)

    Returns:
        True если агент готов, False если таймаут
    """
    print(f"  Waiting for agent at {url}...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            response = httpx.get(url, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "running":
                    print(f"  ✓ Agent is ready (took {time.time() - start_time:.1f}s)")
                    return True
        except Exception:
            pass

        time.sleep(interval)

    return False


@pytest.fixture(scope="session")
def agent_service():
    """
    Фикстура для управления жизненным циклом FastAPI сервиса.

    Запускает сервис через uvicorn, ждёт готовности через /health,
    выполняет тесты, затем останавливает сервис.

    Если SKIP_AGENT_START=true, предполагает что сервис уже запущен.

    Yields:
        dict с информацией о сервисе (url, pid и т.д.)
    """
    process = None

    if SKIP_AGENT_START:
        print("\n" + "=" * 60)
        print("SKIP_AGENT_START=true, using existing agent service")
        print("=" * 60)

        # Проверяем что сервис доступен
        if not wait_for_agent_health(AGENT_HEALTH_URL, timeout=10):
            pytest.fail(
                f"Agent service is not available at {AGENT_HEALTH_URL}. "
                f"Either start it manually or set SKIP_AGENT_START=false"
            )

        yield {"url": AGENT_HEALTH_URL.replace("/health", ""), "managed": False}
        return

    # Находим корень проекта
    project_root = Path(__file__).parent.parent.parent

    print("\n" + "=" * 60)
    print("Starting FastAPI service for eval tests")
    print("=" * 60)
    print(f"Command: {AGENT_START_COMMAND}")
    print(f"Working directory: {project_root}")
    print(f"Health URL: {AGENT_HEALTH_URL}")
    print("-" * 60)

    try:
        # Запускаем сервис
        process = subprocess.Popen(
            AGENT_START_COMMAND,
            shell=True,
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=os.setsid if os.name != 'nt' else None,
        )

        print(f"  Process started with PID: {process.pid}")

        # Ждём готовности сервиса
        if not wait_for_agent_health(AGENT_HEALTH_URL, timeout=AGENT_STARTUP_TIMEOUT):
            # Пытаемся получить логи ошибки
            try:
                stdout, stderr = process.communicate(timeout=5)
                print(f"\n  STDOUT:\n{stdout[-2000:]}")  # Последние 2000 символов
                print(f"\n  STDERR:\n{stderr[-2000:]}")
            except Exception:
                pass

            pytest.fail(
                f"Agent service failed to start within {AGENT_STARTUP_TIMEOUT}s. "
                f"Check logs above or run manually: {AGENT_START_COMMAND}"
            )

        print("=" * 60 + "\n")

        yield {
            "url": AGENT_HEALTH_URL.replace("/health", ""),
            "pid": process.pid,
            "managed": True,
        }

    finally:
        if process and process.poll() is None:
            print("\n" + "=" * 60)
            print("Stopping FastAPI service")
            print("=" * 60)

            try:
                # Завершаем процесс группой (включая дочерние процессы)
                if os.name != 'nt':
                    os.killpg(os.getpgid(process.pid), 15)  # SIGTERM
                else:
                    process.terminate()

                # Ждём graceful shutdown
                try:
                    process.wait(timeout=10)
                    print(f"  ✓ Service stopped gracefully")
                except subprocess.TimeoutExpired:
                    # Force kill
                    if os.name != 'nt':
                        os.killpg(os.getpgid(process.pid), 9)  # SIGKILL
                    else:
                        process.kill()
                    process.wait()
                    print(f"  ✓ Service killed (forced)")

            except Exception as e:
                print(f"  Warning: Error stopping service: {e}")

            print("=" * 60 + "\n")


@pytest.fixture(scope="session")
def judge_model():
    """Фикстура для judge модели."""
    from .eval_utils import get_judge_model
    return get_judge_model()


@pytest.fixture(scope="session")
def test_scenarios():
    """Фикстура для загрузки тестовых сценариев."""
    from .eval_utils import load_golden_dataset

    golden_dataset_path = os.getenv(
        "GOLDEN_DATASET_PATH",
        "tests/evals/fixtures/scenarios.json"
    )

    if not os.path.exists(golden_dataset_path):
        pytest.skip(f"Golden dataset не найден: {golden_dataset_path}")

    return load_golden_dataset(golden_dataset_path)


@pytest.fixture(scope="session")
def eval_report_store():
    """Фикстура-хранилище для сбора результатов метрик."""
    return EVAL_REPORT_DATA


def _generate_html_report(data: list[dict]) -> Path:
    """Генерирует статический HTML-отчёт и сохраняет в tests/evals/results/."""
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    report_path = results_dir / f"eval_report_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.html"

    # Отделяем агрегацию от сценариев
    aggregate_items = [item for item in data if item.get("_type") == "aggregate"]
    scenario_items = [item for item in data if item.get("_type") != "aggregate"]

    total = len(scenario_items)
    passed = sum(1 for item in scenario_items if item.get("overall_passed"))
    failed = total - passed

    # Агрегированная таблица
    aggregate_html = ""
    if aggregate_items:
        agg = aggregate_items[-1]
        agg_rows = []
        for row in agg.get("aggregate_rows", []):
            m_passed = row.get("passed", False)
            m_color = "#22c55e" if m_passed else "#ef4444"
            m_status = "PASS" if m_passed else "FAIL"
            agg_rows.append(
                f"""
                <tr>
                    <td><strong>{html.escape(row.get('display_name', row.get('metric_name', '-')))}</strong></td>
                    <td>{row.get('display_score', 0):.2f} {html.escape(row.get('unit', ''))}</td>
                    <td>{row.get('display_threshold', 0):.2f} {html.escape(row.get('unit', ''))}</td>
                    <td style="color:{m_color};font-weight:600;">{m_status}</td>
                    <td>{row.get('count', 0)}</td>
                </tr>
                """
            )
        agg_overall = agg.get("overall_passed", False)
        agg_border = "#22c55e" if agg_overall else "#ef4444"
        agg_status = "✅ PASSED" if agg_overall else "❌ FAILED"
        agg_status_color = "#22c55e" if agg_overall else "#ef4444"
        aggregate_html = f"""
        <div class="scenario-card" style="border-left: 6px solid {agg_border};">
            <div class="scenario-header">
                <div>
                    <div class="scenario-title">📊 Агрегированные метрики</div>
                    <div class="scenario-input">Средние значения по всем запущенным сценариям</div>
                </div>
                <div class="scenario-status" style="color:{agg_status_color};">{agg_status}</div>
            </div>
            <table class="metrics-table">
                <thead>
                    <tr>
                        <th>Метрика</th>
                        <th>Average Score</th>
                        <th>Threshold</th>
                        <th>Status</th>
                        <th>N scenarios</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(agg_rows)}
                </tbody>
            </table>
        </div>
        """

    rows = []
    for item in scenario_items:
        scenario_idx = item.get("scenario_idx", "-")
        input_msg = html.escape(item.get("input", ""))
        response = html.escape(item.get("actual_output", ""))
        category = html.escape(item.get("category") or "-")
        overall_passed = item.get("overall_passed", False)
        card_border = "#22c55e" if overall_passed else "#ef4444"
        status_text = "✅ PASSED" if overall_passed else "❌ FAILED"
        status_color = "#22c55e" if overall_passed else "#ef4444"

        title = f"Сценарий #{scenario_idx}"

        metrics_rows = []
        for m in item.get("metrics", []):
            m_passed = m.get("passed", False)
            m_color = "#22c55e" if m_passed else "#ef4444"
            m_status = "PASS" if m_passed else "FAIL"
            reason = html.escape(m.get("reason", ""))
            metrics_rows.append(
                f"""
                <tr>
                    <td><strong>{html.escape(m.get('display_name', m.get('metric_name', '-')))}</strong></td>
                    <td>{m.get('display_score', 0):.1f} {html.escape(m.get('unit', ''))}</td>
                    <td>{m.get('display_threshold', 0):.2f} {html.escape(m.get('unit', ''))}</td>
                    <td style="color:{m_color};font-weight:600;">{m_status}</td>
                    <td class="reason">{reason}</td>
                </tr>
                """
            )

        rows.append(
            f"""
            <div class="scenario-card" style="border-left: 6px solid {card_border};">
                <div class="scenario-header">
                    <div>
                        <div class="scenario-title">{title}</div>
                        <div class="scenario-input">{input_msg}</div>
                    </div>
                    <div class="scenario-status" style="color:{status_color};">{status_text}</div>
                </div>
                <div class="scenario-meta">
                    <span><strong>Категория:</strong> {category}</span>
                </div>
                <div class="response-box">
                    <strong>Response:</strong><br/>{response}
                </div>
                <table class="metrics-table">
                    <thead>
                        <tr>
                            <th>Метрика</th>
                            <th>Score</th>
                            <th>Threshold</th>
                            <th>Status</th>
                            <th>Reason</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(metrics_rows)}
                    </tbody>
                </table>
            </div>
            """
        )

    html_content = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Eval Report — {datetime.now().strftime('%Y-%m-%d %H:%M')}</title>
    <style>
        :root {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; }}
        body {{ background: #f8fafc; color: #1f2937; margin: 0; padding: 24px; }}
        .container {{ max-width: 1100px; margin: 0 auto; }}
        h1 {{ margin: 0 0 8px; font-size: 28px; }}
        .subtitle {{ color: #64748b; margin-bottom: 24px; }}
        .summary {{ display: flex; gap: 16px; margin-bottom: 32px; }}
        .summary-card {{
            background: #fff; border-radius: 12px; padding: 16px 24px; min-width: 140px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06); text-align: center;
        }}
        .summary-card .value {{ font-size: 32px; font-weight: 700; }}
        .summary-card .label {{ font-size: 13px; color: #64748b; text-transform: uppercase; letter-spacing: .4px; }}
        .summary-card.pass .value {{ color: #22c55e; }}
        .summary-card.fail .value {{ color: #ef4444; }}
        .scenario-card {{
            background: #fff; border-radius: 12px; padding: 20px 22px;
            margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        }}
        .scenario-header {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }}
        .scenario-title {{ font-size: 16px; font-weight: 700; color: #0f172a; margin-bottom: 4px; }}
        .scenario-input {{ color: #334155; font-size: 14px; }}
        .scenario-status {{ font-size: 14px; font-weight: 700; white-space: nowrap; }}
        .scenario-meta {{ display: flex; gap: 24px; margin-top: 10px; font-size: 13px; color: #475569; }}
        .response-box {{ background: #f1f5f9; border-radius: 8px; padding: 12px; margin-top: 12px; font-size: 13px; color: #334155; line-height: 1.5; }}
        .metrics-table {{ width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 13px; }}
        .metrics-table th {{ text-align: left; padding: 10px 8px; background: #f8fafc; color: #475569; border-bottom: 1px solid #e2e8f0; }}
        .metrics-table td {{ padding: 10px 8px; border-bottom: 1px solid #f1f5f9; vertical-align: top; }}
        .metrics-table .reason {{ color: #64748b; max-width: 420px; }}
        .empty {{ color: #64748b; font-style: italic; padding: 40px 0; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Eval Quality Report — Профсоюзный консультант</h1>
        <div class="subtitle">Сгенерирован: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>

        <div class="summary">
            <div class="summary-card"><div class="value">{total}</div><div class="label">Scenarios</div></div>
            <div class="summary-card pass"><div class="value">{passed}</div><div class="label">Passed</div></div>
            <div class="summary-card fail"><div class="value">{failed}</div><div class="label">Failed</div></div>
        </div>

        {aggregate_html + ''.join(rows) if (aggregate_html or rows) else '<div class="empty">Нет данных для отображения</div>'}
    </div>
</body>
</html>"""

    report_path.write_text(html_content, encoding="utf-8")
    print(f"\n[REPORT] HTML-отчёт сохранён: {report_path}")
    return report_path


def pytest_sessionfinish(session, exitstatus):
    """После завершения сессии генерируем HTML-отчёт, если есть данные."""
    if EVAL_REPORT_DATA:
        _generate_html_report(EVAL_REPORT_DATA)
