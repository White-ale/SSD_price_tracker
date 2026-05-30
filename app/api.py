from pathlib import Path
from html import escape
from urllib.parse import parse_qs

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.products_config import (
    add_product_to_config,
    remove_product_from_config,
    update_product_in_config,
    validate_product,
)
from app.product_source import seed_products_from_config_if_empty
from app.scheduler import run_once
from app.storage import (
    deactivate_product,
    list_alert_events,
    list_check_runs,
    get_latest_check_run,
    get_price_summary,
    get_product,
    get_product_by_name,
    initialize_database,
    list_price_records,
    list_price_records_for_period,
    list_products,
    update_product,
    upsert_product,
)

app = FastAPI(title="SSD Price Tracker API")
STATIC_DIR = Path(__file__).with_name("static")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

FONT_FACE_CSS = """
            @font-face {
                font-family: 'Paperlogy';
                src: url('/static/fonts/Paperlogy-1Thin.ttf') format('truetype');
                font-weight: 100;
                font-style: normal;
                font-display: swap;
            }

            @font-face {
                font-family: 'Paperlogy';
                src: url('/static/fonts/Paperlogy-2ExtraLight.ttf') format('truetype');
                font-weight: 200;
                font-style: normal;
                font-display: swap;
            }

            @font-face {
                font-family: 'Paperlogy';
                src: url('/static/fonts/Paperlogy-3Light.ttf') format('truetype');
                font-weight: 300;
                font-style: normal;
                font-display: swap;
            }

            @font-face {
                font-family: 'Paperlogy';
                src: url('/static/fonts/Paperlogy-4Regular.ttf') format('truetype');
                font-weight: 400;
                font-style: normal;
                font-display: swap;
            }

            @font-face {
                font-family: 'Paperlogy';
                src: url('/static/fonts/Paperlogy-5Medium.ttf') format('truetype');
                font-weight: 500;
                font-style: normal;
                font-display: swap;
            }

            @font-face {
                font-family: 'Paperlogy';
                src: url('/static/fonts/Paperlogy-6SemiBold.ttf') format('truetype');
                font-weight: 600;
                font-style: normal;
                font-display: swap;
            }

            @font-face {
                font-family: 'Paperlogy';
                src: url('/static/fonts/Paperlogy-7Bold.ttf') format('truetype');
                font-weight: 700;
                font-style: normal;
                font-display: swap;
            }

            @font-face {
                font-family: 'Paperlogy';
                src: url('/static/fonts/Paperlogy-8ExtraBold.ttf') format('truetype');
                font-weight: 800;
                font-style: normal;
                font-display: swap;
            }

            @font-face {
                font-family: 'Paperlogy';
                src: url('/static/fonts/Paperlogy-9Black.ttf') format('truetype');
                font-weight: 900;
                font-style: normal;
                font-display: swap;
            }
"""

CHART_PERIODS = {
    "7d": ("7일", 7),
    "30d": ("1개월", 30),
    "90d": ("3개월", 90),
    "180d": ("6개월", 180),
}
DEFAULT_CHART_PERIOD = "30d"
MAX_CHART_RECORDS = 6000


@app.on_event("startup")
def startup():
    initialize_database()
    seed_products_from_config_if_empty()


@app.get("/", response_class=HTMLResponse)
def root(period: str = Query(default=DEFAULT_CHART_PERIOD)):
    product_cards = []
    summaries = get_price_summary()
    period_key, period_label, period_days = get_chart_period(period)
    period_tabs = build_period_tabs(period_key)

    for item in summaries:
        latest_price = format_price(item["latest_price"])
        target_price = format_price(item["target_price"])
        lowest_price = format_price(item["lowest_price"])
        target_status = "지금 살만해요" if item["is_target_reached"] else "조금 더 기다려요"
        target_class = "reached" if item["is_target_reached"] else "watching"
        price_chart = build_price_chart(
            item["id"],
            item["target_price"],
            period_days,
            period_label,
        )
        detail_url = f"/products/{item['id']}/view?period={period_key}"
        product_name = escape(item["name"])

        product_cards.append(
            f"""
            <article class="product-card">
                <div class="product-cell product-name">
                    <span class="cell-label">상품</span>
                    <strong class="product-title">{product_name}</strong>
                    <a class="detail-link" href="{detail_url}">상세 페이지</a>
                </div>
                <div class="product-cell">
                    <span class="cell-label">현재 가격</span>
                    <strong class="price-value">{latest_price}</strong>
                </div>
                <div class="product-cell">
                    <span class="cell-label">역대 최저가</span>
                    <strong class="price-value">{lowest_price}</strong>
                </div>
                <div class="product-cell target-cell">
                    <span class="cell-label">이 가격엔 사야돼!</span>
                    <strong class="price-value">{target_price}</strong>
                    <span class="status {target_class}">{target_status}</span>
                </div>
                <div class="product-cell chart-cell">
                    <span class="cell-label">가격 그래프</span>
                    {price_chart}
                </div>
            </article>
            """
        )

    product_list = "\n".join(product_cards)

    if not product_list:
        product_list = '<div class="empty">아직 등록된 상품이 없습니다.</div>'

    return f"""
    <!doctype html>
    <html lang="ko">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>지금 사면 될까?</title>
        <style>
            {FONT_FACE_CSS}

            body {{
                margin: 0;
                font-family: 'Paperlogy', Arial, sans-serif;
                background: #f6f7f2;
                color: #1f2a2a;
            }}

            main {{
                max-width: 1220px;
                margin: 0 auto;
                padding: 38px 20px 24px;
            }}

            header {{
                display: flex;
                align-items: start;
                justify-content: space-between;
                gap: 16px;
                margin-bottom: 22px;
            }}

            h1 {{
                margin: 0;
                font-size: 34px;
                font-weight: 800;
            }}

            a {{
                color: #1967b3;
                text-decoration: none;
                font-weight: 600;
            }}

            .header-action {{
                display: flex;
                align-items: center;
            }}

            button {{
                cursor: pointer;
                border: 0;
                border-radius: 6px;
                background: #176b55;
                color: white;
                padding: 10px 16px;
                font: inherit;
                font-size: 14px;
                font-weight: 700;
            }}

            button:hover {{
                background: #125642;
            }}

            .period-bar {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 12px;
                margin: 0 0 14px;
            }}

            .period-label {{
                color: #52605b;
                font-size: 13px;
                font-weight: 800;
            }}

            .period-tabs {{
                display: flex;
                align-items: center;
                gap: 8px;
                flex-wrap: wrap;
            }}

            .period-tab {{
                border: 1px solid #cbd8d0;
                border-radius: 6px;
                background: white;
                color: #52605b;
                padding: 7px 10px;
                font-size: 13px;
                font-weight: 800;
            }}

            .period-tab.active {{
                border-color: #176b55;
                background: #e7f3ee;
                color: #176b55;
            }}

            .product-list {{
                display: grid;
                gap: 12px;
            }}

            .product-card {{
                display: grid;
                grid-template-columns: minmax(190px, 1.3fr) minmax(110px, 0.75fr) minmax(120px, 0.8fr) minmax(150px, 0.95fr) minmax(300px, 1.9fr);
                gap: 14px;
                align-items: center;
                border: 1px solid #d9e1db;
                border-radius: 8px;
                background: white;
                padding: 16px;
            }}

            .product-cell {{
                min-width: 0;
            }}

            .cell-label {{
                display: block;
                margin-bottom: 6px;
                color: #68736f;
                font-size: 12px;
                font-weight: 800;
            }}

            .product-title {{
                display: block;
                color: #1f2a2a;
                font-size: 15px;
                font-weight: 800;
                overflow-wrap: anywhere;
            }}

            .detail-link {{
                display: inline-block;
                margin-top: 8px;
                border: 1px solid #cbd8d0;
                border-radius: 6px;
                background: #f7faf8;
                color: #52605b;
                padding: 5px 8px;
                font-size: 12px;
                font-weight: 800;
            }}

            .detail-link:hover {{
                border-color: #176b55;
                color: #176b55;
            }}

            .price-value {{
                display: block;
                color: #1f2a2a;
                font-size: 16px;
                font-weight: 800;
                white-space: nowrap;
            }}

            .target-cell .status {{
                margin-top: 7px;
            }}

            .chart-cell {{
                min-width: 280px;
            }}

            .status {{
                display: inline-block;
                min-width: 96px;
                padding: 5px 8px;
                border-radius: 6px;
                text-align: center;
                font-size: 12px;
                font-weight: 700;
            }}

            .reached {{
                background: #dff7e8;
                color: #176b37;
            }}

            .watching {{
                background: #fff1d6;
                color: #835300;
            }}

            .healthy {{
                background: #e6f4ff;
                color: #155b82;
            }}

            .failing {{
                background: #ffe5e5;
                color: #9f1f1f;
            }}

            .pending {{
                background: #edf0f5;
                color: #5f6b7a;
            }}

            .trend-panel {{
                min-width: 280px;
            }}

            .trend-head,
            .trend-scale {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 12px;
                color: #68736f;
                font-size: 12px;
            }}

            .trend-head {{
                margin-bottom: 5px;
            }}

            .trend-head strong {{
                color: #1f2a2a;
                font-size: 13px;
            }}

            .trend-scale {{
                margin-top: 4px;
            }}

            .chart {{
                display: block;
                width: 100%;
                height: 86px;
            }}

            .chart-line {{
                fill: none;
                stroke: #1967b3;
                stroke-linecap: round;
                stroke-linejoin: round;
                stroke-width: 2.8;
            }}

            .chart-area {{
                fill: #edf4f7;
            }}

            .chart-target {{
                stroke: #d78a00;
                stroke-dasharray: 5 5;
                stroke-width: 1.5;
            }}

            .chart-dot {{
                fill: #1967b3;
                stroke: white;
                stroke-width: 2;
            }}

            .chart-point {{
                fill: white;
                stroke: #1967b3;
                stroke-width: 1.6;
            }}

            .chart-hit {{
                cursor: pointer;
                fill: transparent;
                outline: none;
                stroke: transparent;
            }}

            .chart-hit:hover,
            .chart-hit:focus {{
                fill: #1967b3;
                opacity: 0.16;
            }}

            .chart-tooltip {{
                position: fixed;
                z-index: 50;
                max-width: 260px;
                border: 1px solid #cbd8d0;
                border-radius: 6px;
                background: #1f2a2a;
                color: white;
                opacity: 0;
                padding: 8px 10px;
                pointer-events: none;
                transform: translate(12px, 12px);
                transition: opacity 120ms ease;
                font-size: 12px;
                font-weight: 700;
                line-height: 1.45;
                box-shadow: 0 8px 20px rgba(31, 42, 42, 0.18);
            }}

            .chart-tooltip.visible {{
                opacity: 1;
            }}

            .muted {{
                color: #7a8580;
            }}

            .empty {{
                border: 1px solid #d9e1db;
                border-radius: 8px;
                background: white;
                color: #68736f;
                padding: 18px;
            }}

            .footer-links {{
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 16px;
                flex-wrap: wrap;
                margin-top: 24px;
                color: #68736f;
                font-size: 13px;
            }}

            @media (max-width: 760px) {{
                main {{
                    padding: 20px 12px;
                }}

                header {{
                    align-items: start;
                    flex-direction: column;
                }}

                .period-bar {{
                    align-items: start;
                    flex-direction: column;
                }}

                .product-card {{
                    grid-template-columns: 1fr;
                }}

                .chart-cell {{
                    min-width: 0;
                }}
            }}
        </style>
    </head>
    <body>
        <main>
            <header>
                <div class="header-copy">
                    <h1>지금 사면 될까?</h1>
                </div>
                <div class="header-action">
                    <form action="/check-now" method="post" onsubmit="return showChecking(this);">
                        <button type="submit">가격 갱신</button>
                    </form>
                </div>
            </header>
            <section class="period-bar" aria-label="Chart range">
                {period_tabs}
            </section>
            <section class="product-list" aria-label="SSD 가격 목록">
                {product_list}
            </section>
            <footer class="footer-links">
                <a href="/manage">상품 관리</a>
                <a href="/ops">운영 화면</a>
                <a href="/docs">API 문서</a>
            </footer>
        </main>
        <script>
            function showChecking(form) {{
                const button = form.querySelector("button");
                button.disabled = true;
                button.textContent = "갱신 중...";
                return true;
            }}

            const chartTooltip = document.createElement("div");
            chartTooltip.className = "chart-tooltip";
            document.body.appendChild(chartTooltip);

            function moveChartTooltip(event) {{
                if (!("clientX" in event)) {{
                    return;
                }}

                chartTooltip.style.left = `${{event.clientX}}px`;
                chartTooltip.style.top = `${{event.clientY}}px`;
            }}

            function moveChartTooltipToElement(element) {{
                const rect = element.getBoundingClientRect();
                chartTooltip.style.left = `${{rect.left + rect.width / 2}}px`;
                chartTooltip.style.top = `${{rect.top + rect.height / 2}}px`;
            }}

            document.querySelectorAll(".chart-hit").forEach((point) => {{
                point.addEventListener("mouseenter", (event) => {{
                    chartTooltip.textContent = point.dataset.tooltip || "";
                    chartTooltip.classList.add("visible");
                    moveChartTooltip(event);
                }});

                point.addEventListener("mousemove", moveChartTooltip);

                point.addEventListener("mouseleave", () => {{
                    chartTooltip.classList.remove("visible");
                }});

                point.addEventListener("focus", () => {{
                    chartTooltip.textContent = point.dataset.tooltip || "";
                    chartTooltip.classList.add("visible");
                    moveChartTooltipToElement(point);
                }});

                point.addEventListener("blur", () => {{
                    chartTooltip.classList.remove("visible");
                }});
            }});
        </script>
    </body>
    </html>
    """


@app.get("/products/{product_id}/view", response_class=HTMLResponse)
def product_view(
    product_id: int,
    period: str = Query(default=DEFAULT_CHART_PERIOD),
):
    item = get_summary_item(product_id)

    if item is None:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")

    period_key, period_label, period_days = get_chart_period(period)
    period_tabs = build_period_tabs(
        period_key,
        base_path=f"/products/{product_id}/view",
    )
    price_chart = build_price_chart(
        item["id"],
        item["target_price"],
        period_days,
        period_label,
    )
    latest_price = format_price(item["latest_price"])
    target_price = format_price(item["target_price"])
    lowest_price = format_price(item["lowest_price"])
    updated_at = format_timestamp(
        item["status_last_checked_at"] or item["latest_checked_at"]
    )
    target_status = "지금 살만해요" if item["is_target_reached"] else "조금 더 기다려요"
    target_class = "reached" if item["is_target_reached"] else "watching"
    product_url = escape(item["url"], quote=True)
    recent_rows = build_recent_price_rows(item["id"])

    return f"""
    <!doctype html>
    <html lang="ko">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{escape(item["name"])} - 지금 사면 될까?</title>
        <style>
            {FONT_FACE_CSS}

            body {{
                margin: 0;
                font-family: 'Paperlogy', Arial, sans-serif;
                background: #f6f7f2;
                color: #1f2a2a;
            }}

            main {{
                max-width: 1040px;
                margin: 0 auto;
                padding: 38px 20px 24px;
            }}

            header {{
                display: flex;
                align-items: start;
                justify-content: space-between;
                gap: 16px;
                margin-bottom: 22px;
            }}

            h1,
            h2 {{
                margin: 0;
            }}

            h1 {{
                font-size: 30px;
                font-weight: 800;
            }}

            h2 {{
                margin: 26px 0 12px;
                font-size: 18px;
                font-weight: 800;
            }}

            a {{
                color: #1967b3;
                text-decoration: none;
                font-weight: 700;
            }}

            .summary-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                gap: 12px;
                margin-bottom: 18px;
            }}

            .summary-box,
            .chart-box,
            table {{
                border: 1px solid #d9e1db;
                border-radius: 8px;
                background: white;
            }}

            .summary-box {{
                padding: 14px;
            }}

            .box-label {{
                display: block;
                margin-bottom: 7px;
                color: #68736f;
                font-size: 12px;
                font-weight: 800;
            }}

            .box-value {{
                display: block;
                color: #1f2a2a;
                font-size: 18px;
                font-weight: 800;
            }}

            .status {{
                display: inline-block;
                margin-top: 8px;
                min-width: 96px;
                padding: 5px 8px;
                border-radius: 6px;
                text-align: center;
                font-size: 12px;
                font-weight: 700;
            }}

            .reached {{
                background: #dff7e8;
                color: #176b37;
            }}

            .watching {{
                background: #fff1d6;
                color: #835300;
            }}

            .period-bar {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 12px;
                margin: 0 0 12px;
            }}

            .period-label {{
                color: #52605b;
                font-size: 13px;
                font-weight: 800;
            }}

            .period-tabs {{
                display: flex;
                align-items: center;
                gap: 8px;
                flex-wrap: wrap;
            }}

            .period-tab {{
                border: 1px solid #cbd8d0;
                border-radius: 6px;
                background: white;
                color: #52605b;
                padding: 7px 10px;
                font-size: 13px;
                font-weight: 800;
            }}

            .period-tab.active {{
                border-color: #176b55;
                background: #e7f3ee;
                color: #176b55;
            }}

            .chart-box {{
                padding: 16px;
            }}

            .trend-panel {{
                min-width: 280px;
            }}

            .trend-head,
            .trend-scale {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 12px;
                color: #68736f;
                font-size: 12px;
            }}

            .trend-head {{
                margin-bottom: 5px;
            }}

            .trend-head strong {{
                color: #1f2a2a;
                font-size: 13px;
            }}

            .trend-scale {{
                margin-top: 4px;
            }}

            .chart {{
                display: block;
                width: 100%;
                height: 180px;
            }}

            .chart-line {{
                fill: none;
                stroke: #1967b3;
                stroke-linecap: round;
                stroke-linejoin: round;
                stroke-width: 2.8;
            }}

            .chart-area {{
                fill: #edf4f7;
            }}

            .chart-target {{
                stroke: #d78a00;
                stroke-dasharray: 5 5;
                stroke-width: 1.5;
            }}

            .chart-dot {{
                fill: #1967b3;
                stroke: white;
                stroke-width: 2;
            }}

            .chart-point {{
                fill: white;
                stroke: #1967b3;
                stroke-width: 1.6;
            }}

            .chart-hit {{
                cursor: pointer;
                fill: transparent;
                outline: none;
                stroke: transparent;
            }}

            .chart-hit:hover,
            .chart-hit:focus {{
                fill: #1967b3;
                opacity: 0.16;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                overflow: hidden;
            }}

            th,
            td {{
                padding: 12px 14px;
                border-bottom: 1px solid #e7ece8;
                text-align: left;
                font-size: 13px;
            }}

            th {{
                background: #edf4f0;
                color: #52605b;
            }}

            tr:last-child td {{
                border-bottom: 0;
            }}

            .chart-tooltip {{
                position: fixed;
                z-index: 50;
                max-width: 260px;
                border: 1px solid #cbd8d0;
                border-radius: 6px;
                background: #1f2a2a;
                color: white;
                opacity: 0;
                padding: 8px 10px;
                pointer-events: none;
                transform: translate(12px, 12px);
                transition: opacity 120ms ease;
                font-size: 12px;
                font-weight: 700;
                line-height: 1.45;
                box-shadow: 0 8px 20px rgba(31, 42, 42, 0.18);
            }}

            .chart-tooltip.visible {{
                opacity: 1;
            }}

            .footer-links {{
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 16px;
                flex-wrap: wrap;
                margin-top: 24px;
                color: #68736f;
                font-size: 13px;
            }}

            .muted {{
                color: #7a8580;
            }}

            @media (max-width: 760px) {{
                main {{
                    padding: 20px 12px;
                }}

                header,
                .period-bar {{
                    align-items: start;
                    flex-direction: column;
                }}

                table {{
                    display: block;
                    overflow-x: auto;
                }}
            }}
        </style>
    </head>
    <body>
        <main>
            <header>
                <div>
                    <h1>{escape(item["name"])}</h1>
                </div>
                <a href="/">목록으로</a>
            </header>
            <section class="summary-grid" aria-label="상품 요약">
                <div class="summary-box">
                    <span class="box-label">현재 가격</span>
                    <span class="box-value">{latest_price}</span>
                </div>
                <div class="summary-box">
                    <span class="box-label">역대 최저가</span>
                    <span class="box-value">{lowest_price}</span>
                </div>
                <div class="summary-box">
                    <span class="box-label">이 가격엔 사야돼!</span>
                    <span class="box-value">{target_price}</span>
                    <span class="status {target_class}">{target_status}</span>
                </div>
                <div class="summary-box">
                    <span class="box-label">최근 업데이트</span>
                    <span class="box-value">{escape(updated_at)}</span>
                </div>
            </section>
            <section class="summary-grid" aria-label="상품 링크">
                <div class="summary-box">
                    <span class="box-label">상품 링크</span>
                    <a href="{product_url}" target="_blank" rel="noreferrer">상품 페이지 열기</a>
                </div>
            </section>
            <section class="period-bar" aria-label="그래프 기간">
                {period_tabs}
            </section>
            <section class="chart-box">
                {price_chart}
            </section>
            <h2>최근 가격 기록</h2>
            <table>
                <thead>
                    <tr>
                        <th>확인 시각</th>
                        <th>가격</th>
                    </tr>
                </thead>
                <tbody>{recent_rows}</tbody>
            </table>
            <footer class="footer-links">
                <a href="/manage">상품 관리</a>
                <a href="/ops">운영 화면</a>
                <a href="/docs">API 문서</a>
            </footer>
        </main>
        {build_chart_tooltip_script()}
    </body>
    </html>
    """


@app.get("/ops", response_class=HTMLResponse)
def ops():
    summaries = get_price_summary()
    latest_run = get_latest_check_run()
    recent_runs = list_check_runs(limit=12)
    recent_alerts = list_alert_events(limit=12)
    status_metrics = build_status_metrics(latest_run, summaries)
    run_rows = build_run_rows(recent_runs)
    product_status_rows = build_product_status_rows(summaries)
    alert_rows = build_alert_rows(recent_alerts)

    return f"""
    <!doctype html>
    <html lang="ko">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>운영 화면</title>
        <style>
            {FONT_FACE_CSS}

            body {{
                margin: 0;
                font-family: 'Paperlogy', Arial, sans-serif;
                background: #f5f7fb;
                color: #172033;
            }}

            main {{
                max-width: 1180px;
                margin: 0 auto;
                padding: 32px 20px;
            }}

            header {{
                display: flex;
                align-items: start;
                justify-content: space-between;
                gap: 16px;
                margin-bottom: 20px;
            }}

            h1,
            h2 {{
                margin: 0;
            }}

            h1 {{
                font-size: 28px;
                font-weight: 700;
            }}

            h2 {{
                margin: 26px 0 12px;
                font-size: 18px;
                font-weight: 800;
            }}

            .subtitle {{
                margin: 6px 0 0;
                color: #65728a;
                font-size: 14px;
            }}

            a {{
                color: #2458d3;
                text-decoration: none;
                font-weight: 600;
            }}

            .actions {{
                display: flex;
                align-items: center;
                gap: 12px;
                flex-wrap: wrap;
            }}

            .metrics {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
                gap: 12px;
                margin-bottom: 16px;
            }}

            .metric,
            .note {{
                border: 1px solid #dfe5f0;
                border-radius: 6px;
                background: white;
                padding: 12px 14px;
            }}

            .metric-label {{
                display: block;
                margin-bottom: 6px;
                color: #6a768d;
                font-size: 12px;
                font-weight: 700;
                text-transform: uppercase;
            }}

            .metric-value {{
                display: block;
                color: #172033;
                font-size: 18px;
                font-weight: 800;
            }}

            .metric-sub,
            .note {{
                color: #7a869a;
                font-size: 12px;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
                border: 1px solid #dfe5f0;
            }}

            th,
            td {{
                padding: 12px 14px;
                border-bottom: 1px solid #e8edf5;
                text-align: left;
                font-size: 13px;
                vertical-align: top;
            }}

            th {{
                background: #eef3fb;
                color: #46556f;
            }}

            tr:last-child td {{
                border-bottom: 0;
            }}

            .status {{
                display: inline-block;
                min-width: 72px;
                padding: 5px 8px;
                border-radius: 6px;
                text-align: center;
                font-size: 12px;
                font-weight: 700;
            }}

            .healthy,
            .success {{
                background: #e6f4ff;
                color: #155b82;
            }}

            .skipped,
            .pending {{
                background: #edf0f5;
                color: #5f6b7a;
            }}

            .failing,
            .failed,
            .partial_failure {{
                background: #ffe5e5;
                color: #9f1f1f;
            }}

            .running {{
                background: #fff1d6;
                color: #835300;
            }}

            .muted {{
                color: #7a869a;
            }}

            .error-cell {{
                max-width: 360px;
                overflow-wrap: anywhere;
            }}

            @media (max-width: 760px) {{
                main {{
                    padding: 20px 12px;
                }}

                header {{
                    align-items: start;
                    flex-direction: column;
                }}

                table {{
                    display: block;
                    overflow-x: auto;
                }}

                th,
                td {{
                    white-space: nowrap;
                }}
            }}
        </style>
    </head>
    <body>
        <main>
            <header>
                <div>
                    <h1>운영 화면</h1>
                    <p class="subtitle">자동 실행, 수집 상태, 알림 이력을 확인합니다.</p>
                </div>
                <div class="actions">
                    <a href="/">대시보드</a>
                    <a href="/manage">상품 관리</a>
                    <a href="/docs">API 문서</a>
                </div>
            </header>
            <p class="note">
                수집 상태는 상품별 크롤링 결과입니다. 대기는 아직 기록이 없다는 뜻이고,
                정상은 최근 수집 성공, 실패 중은 최근 수집 실패 또는 연속 실패가 있다는 뜻입니다.
            </p>
            {status_metrics}
            <h2>최근 실행</h2>
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>상태</th>
                        <th>시작</th>
                        <th>종료</th>
                        <th>출처</th>
                        <th>성공</th>
                        <th>실패</th>
                        <th>메시지</th>
                    </tr>
                </thead>
                <tbody>{run_rows}</tbody>
            </table>
            <h2>상품별 수집 상태</h2>
            <table>
                <thead>
                    <tr>
                        <th>상품</th>
                        <th>상태</th>
                        <th>마지막 확인</th>
                        <th>마지막 성공</th>
                        <th>마지막 실패</th>
                        <th>실패 횟수</th>
                        <th>마지막 오류</th>
                    </tr>
                </thead>
                <tbody>{product_status_rows}</tbody>
            </table>
            <h2>알림 이력</h2>
            <table>
                <thead>
                    <tr>
                        <th>전송 시각</th>
                        <th>종류</th>
                        <th>키</th>
                        <th>내용</th>
                    </tr>
                </thead>
                <tbody>{alert_rows}</tbody>
            </table>
        </main>
    </body>
    </html>
    """


@app.get("/manage", response_class=HTMLResponse)
def manage_products():
    return render_manage_page()


@app.post("/manage/products")
async def add_product(request: Request):
    form = await parse_product_form(request)

    try:
        product = add_product_to_config(
            form.get("name", ""),
            form.get("url", ""),
            form.get("target_price", ""),
        )
        upsert_product(
            product["name"],
            product["url"],
            product["target_price"],
        )
    except ValueError as error:
        return HTMLResponse(render_manage_page(str(error)), status_code=400)

    return RedirectResponse(url="/manage", status_code=303)


@app.post("/manage/products/{product_id}")
async def edit_product(product_id: int, request: Request):
    existing_product = get_product(product_id)

    if existing_product is None:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")

    form = await parse_product_form(request)

    try:
        product = validate_product(
            form.get("name", ""),
            form.get("url", ""),
            form.get("target_price", ""),
        )
        product_with_same_name = get_product_by_name(
            product["name"],
            include_inactive=True,
        )

        if (
            product_with_same_name is not None
            and product_with_same_name["id"] != product_id
        ):
            raise ValueError("이미 같은 이름의 상품이 있습니다.")

        update_product_in_config(
            existing_product["name"],
            product["name"],
            product["url"],
            product["target_price"],
        )

        if not update_product(
            product_id,
            product["name"],
            product["url"],
            product["target_price"],
        ):
            raise ValueError("상품이 수정되지 않았습니다.")
    except ValueError as error:
        return HTMLResponse(render_manage_page(str(error)), status_code=400)

    return RedirectResponse(url="/manage", status_code=303)


@app.post("/manage/products/{product_id}/delete")
def delete_product(product_id: int):
    product = get_product(product_id)

    if product is None:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")

    remove_product_from_config(product["name"])
    deactivate_product(product_id)
    return RedirectResponse(url="/manage", status_code=303)


async def parse_product_form(request):
    body = (await request.body()).decode("utf-8")
    fields = parse_qs(body, keep_blank_values=True)
    return {key: values[0] if values else "" for key, values in fields.items()}


def render_manage_page(error=None):
    products = list_products()
    product_cards = "\n".join(build_product_form(product) for product in products)
    error_html = (
        f'<div class="alert" role="alert">{escape(error)}</div>' if error else ""
    )

    if not product_cards:
        product_cards = '<div class="empty">추적 중인 상품이 없습니다.</div>'

    return f"""
    <!doctype html>
    <html lang="ko">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>상품 관리</title>
        <style>
            {FONT_FACE_CSS}

            body {{
                margin: 0;
                font-family: 'Paperlogy', Arial, sans-serif;
                background: #f5f7fb;
                color: #172033;
            }}

            main {{
                max-width: 1100px;
                margin: 0 auto;
                padding: 32px 20px;
            }}

            header {{
                display: flex;
                align-items: end;
                justify-content: space-between;
                gap: 16px;
                margin-bottom: 20px;
            }}

            h1,
            h2 {{
                margin: 0;
            }}

            h1 {{
                font-size: 28px;
                font-weight: 700;
            }}

            h2 {{
                font-size: 18px;
                font-weight: 800;
            }}

            a {{
                color: #2458d3;
                text-decoration: none;
                font-weight: 600;
            }}

            .actions,
            .form-actions {{
                display: flex;
                align-items: center;
                gap: 12px;
                flex-wrap: wrap;
            }}

            .form-actions {{
                margin-top: 12px;
            }}

            form {{
                margin: 0;
            }}

            .panel,
            .product-card {{
                border: 1px solid #dfe5f0;
                border-radius: 6px;
                background: white;
            }}

            .panel {{
                margin-bottom: 18px;
                padding: 16px;
            }}

            .product-list {{
                display: grid;
                gap: 12px;
            }}

            .product-card {{
                padding: 14px;
            }}

            .grid {{
                display: grid;
                grid-template-columns: minmax(160px, 1fr) minmax(240px, 2fr) 150px;
                gap: 12px;
            }}

            label {{
                display: grid;
                gap: 6px;
                color: #46556f;
                font-size: 13px;
                font-weight: 700;
            }}

            input {{
                box-sizing: border-box;
                width: 100%;
                border: 1px solid #cfd7e6;
                border-radius: 6px;
                padding: 9px 10px;
                color: #172033;
                font: inherit;
                font-size: 14px;
            }}

            input:focus {{
                border-color: #2458d3;
                outline: 2px solid #d9e5ff;
            }}

            button {{
                cursor: pointer;
                border: 0;
                border-radius: 6px;
                background: #2458d3;
                color: white;
                padding: 9px 14px;
                font: inherit;
                font-size: 14px;
                font-weight: 700;
            }}

            button:hover {{
                background: #1d48ad;
            }}

            .danger {{
                background: #b3261e;
            }}

            .danger:hover {{
                background: #8f1d17;
            }}

            .alert {{
                margin-bottom: 16px;
                border: 1px solid #ffc9c9;
                border-radius: 6px;
                background: #ffecec;
                color: #9f1f1f;
                padding: 10px 12px;
                font-size: 14px;
                font-weight: 700;
            }}

            .empty {{
                border: 1px solid #dfe5f0;
                border-radius: 6px;
                background: white;
                color: #7a869a;
                padding: 16px;
            }}

            .section-title {{
                margin: 22px 0 12px;
            }}

            @media (max-width: 760px) {{
                main {{
                    padding: 20px 12px;
                }}

                header {{
                    align-items: start;
                    flex-direction: column;
                }}

                .grid {{
                    grid-template-columns: 1fr;
                }}
            }}
        </style>
    </head>
    <body>
        <main>
            <header>
                <h1>상품 관리</h1>
                <div class="actions">
                    <a href="/">대시보드</a>
                    <a href="/ops">운영 화면</a>
                    <a href="/docs">API 문서</a>
                </div>
            </header>
            {error_html}
            <section class="panel">
                <h2>상품 추가</h2>
                <form action="/manage/products" method="post">
                    <div class="grid">
                        <label>
                            상품명
                            <input name="name" required>
                        </label>
                        <label>
                            URL
                            <input name="url" type="url" required>
                        </label>
                        <label>
                            목표가
                            <input name="target_price" type="number" min="1" required>
                        </label>
                    </div>
                    <div class="form-actions">
                        <button type="submit">추가</button>
                    </div>
                </form>
            </section>
            <h2 class="section-title">추적 중인 상품</h2>
            <section class="product-list">
                {product_cards}
            </section>
        </main>
    </body>
    </html>
    """


def build_product_form(product):
    product_id = product["id"]
    name = escape(product["name"], quote=True)
    url = escape(product["url"], quote=True)
    target_price = product["target_price"]

    return f"""
    <article class="product-card">
        <form action="/manage/products/{product_id}" method="post">
            <div class="grid">
                <label>
                    상품명
                    <input name="name" value="{name}" required>
                </label>
                <label>
                    URL
                    <input name="url" type="url" value="{url}" required>
                </label>
                <label>
                    목표가
                    <input name="target_price" type="number" min="1" value="{target_price}" required>
                </label>
            </div>
            <div class="form-actions">
                <button type="submit">저장</button>
            </div>
        </form>
        <form action="/manage/products/{product_id}/delete" method="post" onsubmit="return confirm('이 상품을 추적 목록에서 삭제할까요?');">
            <div class="form-actions">
                <button class="danger" type="submit">삭제</button>
            </div>
        </form>
    </article>
    """


def build_run_rows(runs):
    if not runs:
        return '<tr><td class="muted" colspan="8">기록된 실행이 없습니다.</td></tr>'

    rows = []

    for run in runs:
        status = run["status"] or "unknown"
        status_class = escape(status)
        status_label = escape(format_run_status(status))
        message = escape(run["error_message"] or "")
        rows.append(
            f"""
            <tr>
                <td>{run["id"]}</td>
                <td><span class="status {status_class}">{status_label}</span></td>
                <td>{escape(format_timestamp(run["started_at"]))}</td>
                <td>{escape(format_timestamp(run["finished_at"]))}</td>
                <td>{escape(run["source"] or "unknown")}</td>
                <td>{run["success_count"]} / {run["checked_count"]}</td>
                <td>{run["failure_count"]}</td>
                <td class="error-cell">{message or '<span class="muted">-</span>'}</td>
            </tr>
            """
        )

    return "\n".join(rows)


def build_product_status_rows(summaries):
    if not summaries:
        return '<tr><td class="muted" colspan="7">기록된 상품이 없습니다.</td></tr>'

    rows = []

    for item in summaries:
        health_status, health_class = get_product_health(item)
        last_error = escape(item["last_error"] or "")
        rows.append(
            f"""
            <tr>
                <td>{escape(item["name"])}</td>
                <td><span class="status {health_class}">{health_status}</span></td>
                <td>{escape(format_timestamp(item["status_last_checked_at"]))}</td>
                <td>{escape(format_timestamp(item["last_success_at"]))}</td>
                <td>{escape(format_timestamp(item["last_failure_at"]))}</td>
                <td>{item["consecutive_failures"]}</td>
                <td class="error-cell">{last_error or '<span class="muted">-</span>'}</td>
            </tr>
            """
        )

    return "\n".join(rows)


def get_product_health(item):
    if item["status_last_checked_at"] is None:
        return "대기", "pending"

    if item["consecutive_failures"]:
        return "실패 중", "failing"

    return "정상", "healthy"


def build_alert_rows(alerts):
    if not alerts:
        return '<tr><td class="muted" colspan="4">기록된 알림이 없습니다.</td></tr>'

    rows = []

    for alert in alerts:
        detail = escape(alert["detail"] or "")
        rows.append(
            f"""
            <tr>
                <td>{escape(format_timestamp(alert["sent_at"]))}</td>
                <td>{escape(alert["alert_type"])}</td>
                <td>{escape(alert["alert_key"])}</td>
                <td class="error-cell">{detail or '<span class="muted">-</span>'}</td>
            </tr>
            """
        )

    return "\n".join(rows)


def get_summary_item(product_id):
    for item in get_price_summary():
        if item["id"] == product_id:
            return item

    return None


def build_recent_price_rows(product_id):
    records = list_price_records(product_id, limit=10)

    if not records:
        return '<tr><td class="muted" colspan="2">아직 가격 기록이 없습니다.</td></tr>'

    rows = []

    for record in records:
        rows.append(
            f"""
            <tr>
                <td>{escape(format_timestamp(record["checked_at"]))}</td>
                <td>{format_price(record["price"])}</td>
            </tr>
            """
        )

    return "\n".join(rows)


def build_chart_tooltip_script():
    return """
        <script>
            const chartTooltip = document.createElement("div");
            chartTooltip.className = "chart-tooltip";
            document.body.appendChild(chartTooltip);

            function moveChartTooltip(event) {
                if (!("clientX" in event)) {
                    return;
                }

                chartTooltip.style.left = `${event.clientX}px`;
                chartTooltip.style.top = `${event.clientY}px`;
            }

            function moveChartTooltipToElement(element) {
                const rect = element.getBoundingClientRect();
                chartTooltip.style.left = `${rect.left + rect.width / 2}px`;
                chartTooltip.style.top = `${rect.top + rect.height / 2}px`;
            }

            document.querySelectorAll(".chart-hit").forEach((point) => {
                point.addEventListener("mouseenter", (event) => {
                    chartTooltip.textContent = point.dataset.tooltip || "";
                    chartTooltip.classList.add("visible");
                    moveChartTooltip(event);
                });

                point.addEventListener("mousemove", moveChartTooltip);

                point.addEventListener("mouseleave", () => {
                    chartTooltip.classList.remove("visible");
                });

                point.addEventListener("focus", () => {
                    chartTooltip.textContent = point.dataset.tooltip || "";
                    chartTooltip.classList.add("visible");
                    moveChartTooltipToElement(point);
                });

                point.addEventListener("blur", () => {
                    chartTooltip.classList.remove("visible");
                });
            });
        </script>
    """


def get_chart_period(period):
    if period not in CHART_PERIODS:
        period = DEFAULT_CHART_PERIOD

    label, days = CHART_PERIODS[period]
    return period, label, days


def build_period_tabs(active_period, base_path="/"):
    links = []

    for period, (label, _days) in CHART_PERIODS.items():
        active_class = " active" if period == active_period else ""
        current = ' aria-current="page"' if period == active_period else ""
        links.append(
            f'<a class="period-tab{active_class}" href="{base_path}?period={period}"'
            f"{current}>{escape(label)}</a>"
        )

    return f'<nav class="period-tabs">{"".join(links)}</nav>'


def build_status_metrics(latest_run, summaries):
    product_count = len(summaries)
    failing_count = sum(1 for item in summaries if item["consecutive_failures"])

    if latest_run is None:
        run_status = "-"
        run_time = "-"
        run_counts = "0 / 0"
        run_failures = "0"
    else:
        run_status = format_run_status(latest_run["status"])
        run_time = (
            format_timestamp(
                latest_run["finished_at"] or latest_run["started_at"]
            )
            + f" | {latest_run.get('source') or 'unknown'}"
        )
        run_counts = f"{latest_run['success_count']} / {latest_run['checked_count']}"
        run_failures = str(latest_run["failure_count"])

    return f"""
    <section class="metrics" aria-label="Tracker status">
        <div class="metric">
            <span class="metric-label">마지막 실행</span>
            <span class="metric-value">{escape(run_status)}</span>
            <span class="metric-sub">{escape(run_time)}</span>
        </div>
        <div class="metric">
            <span class="metric-label">성공</span>
            <span class="metric-value">{escape(run_counts)}</span>
            <span class="metric-sub">성공한 상품 수</span>
        </div>
        <div class="metric">
            <span class="metric-label">실패</span>
            <span class="metric-value">{escape(run_failures)}</span>
            <span class="metric-sub">최근 실행 기준</span>
        </div>
        <div class="metric">
            <span class="metric-label">상품</span>
            <span class="metric-value">{product_count}</span>
            <span class="metric-sub">실패 중 {failing_count}개</span>
        </div>
    </section>
    """


def format_run_status(status):
    labels = {
        "running": "실행 중",
        "success": "정상",
        "skipped": "건너뜀",
        "partial_failure": "일부 실패",
        "failed": "실패",
    }
    return labels.get(status, status or "-")


@app.post("/check-now")
def check_now():
    run_once()
    return RedirectResponse(url="/", status_code=303)


def format_price(price):
    if price is None:
        return "-"

    return f"{price:,}원"


def format_timestamp(timestamp):
    if not timestamp:
        return "-"

    return f"{timestamp} 한국시간"


def build_price_chart(product_id, target_price, period_days, period_label):
    records = list_price_records_for_period(
        product_id,
        period_days,
        limit=MAX_CHART_RECORDS,
    )
    ordered_records = list(reversed(records))

    if not ordered_records:
        return f'<span class="muted">{escape(period_label)} 기록 없음</span>'

    display_records, change_record_ids, change_count = select_price_change_records(
        ordered_records
    )
    display_prices = [record["price"] for record in display_records]
    period_prices = [record["price"] for record in ordered_records]

    width = 300
    height = 86
    padding_x = 10
    padding_y = 10
    min_price = min(period_prices)
    max_price = max(period_prices)
    display_min = min(min_price, target_price)
    display_max = max(max_price, target_price)

    if display_min == display_max:
        display_min -= 1000
        display_max += 1000

    price_range = display_max - display_min
    usable_width = width - padding_x * 2
    usable_height = height - padding_y * 2
    points = []
    chart_points = []

    if len(display_prices) == 1:
        x = width - padding_x
        y = price_to_chart_y(
            display_prices[0],
            display_max,
            price_range,
            padding_y,
            usable_height,
        )
        points = [(padding_x, y), (x, y)]
        chart_points = [(x, y, display_records[0])]
    else:
        for index, record in enumerate(display_records):
            price = record["price"]
            x = padding_x + (usable_width * index / (len(display_prices) - 1))
            y = price_to_chart_y(
                price,
                display_max,
                price_range,
                padding_y,
                usable_height,
            )
            points.append((x, y))
            chart_points.append((x, y, record))

    line_points = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    area_points = (
        f"{padding_x},{height - padding_y} "
        f"{line_points} "
        f"{width - padding_x},{height - padding_y}"
    )
    target_y = price_to_chart_y(
        target_price,
        display_max,
        price_range,
        padding_y,
        usable_height,
    )
    latest_x, latest_y, _latest_record = chart_points[-1]
    latest_price = ordered_records[-1]["price"]
    visible_points = "\n".join(
        f'<circle class="chart-point" cx="{x:.1f}" cy="{y:.1f}" r="2.5"></circle>'
        for x, y, _record in chart_points
        if _record["id"] in change_record_ids
    )
    hover_points = "\n".join(
        build_chart_hover_point(x, y, record)
        for x, y, record in chart_points
    )
    label = escape(
        f"{period_label} 가격 변화. 현재 {latest_price:,}원. "
        f"최저 {min_price:,}원. 최고 {max_price:,}원. "
        f"목표 {target_price:,}원."
    )

    return f"""
    <div class="trend-panel">
        <div class="trend-head">
            <span><strong>{change_count}</strong>번 변동</span>
            <span>목표 {format_price(target_price)}</span>
        </div>
        <svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="{label}">
            <polygon class="chart-area" points="{area_points}"></polygon>
            <line class="chart-target" x1="{padding_x}" y1="{target_y:.1f}" x2="{width - padding_x}" y2="{target_y:.1f}"></line>
            <polyline class="chart-line" points="{line_points}"></polyline>
            {visible_points}
            <circle class="chart-dot" cx="{latest_x:.1f}" cy="{latest_y:.1f}" r="4"></circle>
            {hover_points}
        </svg>
        <div class="trend-scale">
            <span>최저 {format_price(min_price)}</span>
            <span>최고 {format_price(max_price)}</span>
        </div>
    </div>
    """


def select_price_change_records(ordered_records):
    display_records = []
    change_record_ids = set()
    previous_price = None
    change_count = 0

    for record in ordered_records:
        price = record["price"]

        if previous_price is None:
            display_records.append(record)
            change_record_ids.add(record["id"])
        elif price != previous_price:
            display_records.append(record)
            change_record_ids.add(record["id"])
            change_count += 1

        previous_price = price

    latest_record = ordered_records[-1]

    if display_records[-1]["id"] != latest_record["id"]:
        display_records.append(latest_record)

    return display_records, change_record_ids, change_count


def build_chart_hover_point(x, y, record):
    tooltip = escape(
        f"{format_timestamp(record['checked_at'])} | {format_price(record['price'])}",
        quote=True,
    )

    return (
        f'<circle class="chart-hit" cx="{x:.1f}" cy="{y:.1f}" r="9" '
        f'tabindex="0" data-tooltip="{tooltip}"><title>{tooltip}</title></circle>'
    )


def price_to_chart_y(price, display_max, price_range, padding_y, usable_height):
    return padding_y + usable_height * (display_max - price) / price_range


@app.get("/health")
def health():
    return {
        "message": "SSD price tracker API",
        "docs": "/docs",
    }


@app.get("/status")
def status():
    summaries = get_price_summary()
    latest_run = get_latest_check_run()

    return {
        "latest_run": latest_run,
        "product_count": len(summaries),
        "failing_product_count": sum(
            1 for item in summaries if item["consecutive_failures"]
        ),
        "products": [
            {
                "id": item["id"],
                "name": item["name"],
                "last_checked_at": item["status_last_checked_at"],
                "last_success_at": item["last_success_at"],
                "last_failure_at": item["last_failure_at"],
                "last_error": item["last_error"],
                "consecutive_failures": item["consecutive_failures"],
            }
            for item in summaries
        ],
    }


@app.get("/products")
def products():
    return list_products()


@app.get("/products/{product_id}")
def product_detail(product_id: int):
    product = get_product(product_id)

    if product is None:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")

    return product


@app.get("/products/{product_id}/prices")
def product_prices(
    product_id: int,
    limit: int = Query(default=30, ge=1, le=200),
    days: int = Query(default=0, ge=0, le=3650),
):
    product = get_product(product_id)

    if product is None:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")

    if days > 0:
        return list_price_records_for_period(product_id, days, limit)

    return list_price_records(product_id, limit)


@app.get("/summary")
def summary():
    return get_price_summary()
