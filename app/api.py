from html import escape
from urllib.parse import parse_qs

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

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
    rows = []
    summaries = get_price_summary()
    period_key, period_label, period_days = get_chart_period(period)
    period_tabs = build_period_tabs(period_key)

    for item in summaries:
        latest_price = format_price(item["latest_price"])
        target_price = format_price(item["target_price"])
        lowest_price = format_price(item["lowest_price"])
        checked_at = format_timestamp(
            item["status_last_checked_at"] or item["latest_checked_at"]
        )
        target_status = "At Target" if item["is_target_reached"] else "Watching"
        target_class = "reached" if item["is_target_reached"] else "watching"
        price_chart = build_price_chart(
            item["id"],
            item["target_price"],
            period_days,
            period_label,
        )
        product_link = (
            f'<a class="product-link" href="{escape(item["url"], quote=True)}" '
            f'target="_blank" rel="noreferrer">{escape(item["name"])}</a>'
        )

        rows.append(
            f"""
            <tr>
                <td>{product_link}</td>
                <td>{latest_price}</td>
                <td>{target_price}</td>
                <td>{lowest_price}</td>
                <td>{price_chart}</td>
                <td>{escape(checked_at)}</td>
                <td><span class="status {target_class}">{target_status}</span></td>
            </tr>
            """
        )

    table_rows = "\n".join(rows)
    dashboard_metrics = build_dashboard_metrics(summaries, period_label)

    return f"""
    <!doctype html>
    <html lang="ko">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>SSD Price Tracker</title>
        <style>
            body {{
                margin: 0;
                font-family: Arial, sans-serif;
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

            h1 {{
                margin: 0;
                font-size: 28px;
                font-weight: 700;
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

            .metrics {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
                gap: 12px;
                margin-bottom: 16px;
            }}

            .metric {{
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

            .metric-sub {{
                display: block;
                margin-top: 4px;
                color: #7a869a;
                font-size: 12px;
            }}

            .period-bar {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 12px;
                margin: 0 0 16px;
            }}

            .period-label {{
                color: #46556f;
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
                border: 1px solid #cfd7e6;
                border-radius: 6px;
                background: white;
                color: #46556f;
                padding: 7px 10px;
                font-size: 13px;
                font-weight: 800;
            }}

            .period-tab.active {{
                border-color: #2458d3;
                background: #eaf1ff;
                color: #2458d3;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
                border: 1px solid #dfe5f0;
            }}

            th,
            td {{
                padding: 14px 16px;
                border-bottom: 1px solid #e8edf5;
                text-align: left;
                font-size: 14px;
                vertical-align: middle;
            }}

            th {{
                background: #eef3fb;
                color: #46556f;
                font-size: 13px;
            }}

            tr:last-child td {{
                border-bottom: 0;
            }}

            .product-link {{
                color: #172033;
            }}

            .product-link:hover {{
                color: #2458d3;
            }}

            .status {{
                display: inline-block;
                min-width: 72px;
                padding: 5px 8px;
                border-radius: 6px;
                text-align: center;
                font-size: 13px;
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
                color: #69768d;
                font-size: 12px;
            }}

            .trend-head {{
                margin-bottom: 5px;
            }}

            .trend-head strong {{
                color: #172033;
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
                stroke: #2458d3;
                stroke-linecap: round;
                stroke-linejoin: round;
                stroke-width: 2.8;
            }}

            .chart-area {{
                fill: #eef3fb;
            }}

            .chart-target {{
                stroke: #d78a00;
                stroke-dasharray: 5 5;
                stroke-width: 1.5;
            }}

            .chart-dot {{
                fill: #2458d3;
                stroke: white;
                stroke-width: 2;
            }}

            .chart-point {{
                fill: white;
                stroke: #2458d3;
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
                fill: #2458d3;
                opacity: 0.16;
            }}

            .chart-tooltip {{
                position: fixed;
                z-index: 50;
                max-width: 260px;
                border: 1px solid #cfd7e6;
                border-radius: 6px;
                background: #172033;
                color: white;
                opacity: 0;
                padding: 8px 10px;
                pointer-events: none;
                transform: translate(12px, 12px);
                transition: opacity 120ms ease;
                font-size: 12px;
                font-weight: 700;
                line-height: 1.45;
                box-shadow: 0 8px 20px rgba(23, 32, 51, 0.18);
            }}

            .chart-tooltip.visible {{
                opacity: 1;
            }}

            .muted {{
                color: #7a869a;
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
                <div class="header-copy">
                    <h1>SSD Price Tracker</h1>
                    <p class="subtitle">Current prices, targets, and recent price changes.</p>
                </div>
                <div class="actions">
                    <form action="/check-now" method="post" onsubmit="return showChecking(this);">
                        <button type="submit">Check Now</button>
                    </form>
                    <a href="/manage">Manage</a>
                    <a href="/ops">Ops</a>
                    <a href="/docs">API Docs</a>
                </div>
            </header>
            {dashboard_metrics}
            <section class="period-bar" aria-label="Chart range">
                <span class="period-label">Trend Range</span>
                {period_tabs}
            </section>
            <table>
                <thead>
                    <tr>
                        <th>Product</th>
                        <th>Latest</th>
                        <th>Target</th>
                        <th>Lowest</th>
                        <th>Trend</th>
                        <th>Updated</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </main>
        <script>
            function showChecking(form) {{
                const button = form.querySelector("button");
                button.disabled = true;
                button.textContent = "Checking...";
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
        <title>SSD Price Tracker Ops</title>
        <style>
            body {{
                margin: 0;
                font-family: Arial, sans-serif;
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
                    <h1>Operations</h1>
                    <p class="subtitle">Automation runs, crawler health, and alert history.</p>
                </div>
                <div class="actions">
                    <a href="/">Dashboard</a>
                    <a href="/manage">Manage</a>
                    <a href="/docs">API Docs</a>
                </div>
            </header>
            <p class="note">
                Health means crawler status: Pending has no product check yet,
                Healthy means the latest product check succeeded, and Failing
                means the latest product check failed or has consecutive failures.
            </p>
            {status_metrics}
            <h2>Recent Runs</h2>
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Status</th>
                        <th>Started</th>
                        <th>Finished</th>
                        <th>Source</th>
                        <th>Success</th>
                        <th>Failures</th>
                        <th>Message</th>
                    </tr>
                </thead>
                <tbody>{run_rows}</tbody>
            </table>
            <h2>Product Health</h2>
            <table>
                <thead>
                    <tr>
                        <th>Product</th>
                        <th>Health</th>
                        <th>Last Checked</th>
                        <th>Last Success</th>
                        <th>Last Failure</th>
                        <th>Failures</th>
                        <th>Last Error</th>
                    </tr>
                </thead>
                <tbody>{product_status_rows}</tbody>
            </table>
            <h2>Alert Events</h2>
            <table>
                <thead>
                    <tr>
                        <th>Sent At</th>
                        <th>Type</th>
                        <th>Key</th>
                        <th>Detail</th>
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
        raise HTTPException(status_code=404, detail="Product not found")

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
            raise ValueError("Product name already exists.")

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
            raise ValueError("Product was not updated.")
    except ValueError as error:
        return HTMLResponse(render_manage_page(str(error)), status_code=400)

    return RedirectResponse(url="/manage", status_code=303)


@app.post("/manage/products/{product_id}/delete")
def delete_product(product_id: int):
    product = get_product(product_id)

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

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
        product_cards = '<div class="empty">No products are being tracked.</div>'

    return f"""
    <!doctype html>
    <html lang="ko">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Manage Products</title>
        <style>
            body {{
                margin: 0;
                font-family: Arial, sans-serif;
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
                <h1>Manage Products</h1>
                <div class="actions">
                    <a href="/">Dashboard</a>
                    <a href="/docs">API Docs</a>
                </div>
            </header>
            {error_html}
            <section class="panel">
                <h2>Add Product</h2>
                <form action="/manage/products" method="post">
                    <div class="grid">
                        <label>
                            Name
                            <input name="name" required>
                        </label>
                        <label>
                            URL
                            <input name="url" type="url" required>
                        </label>
                        <label>
                            Target
                            <input name="target_price" type="number" min="1" required>
                        </label>
                    </div>
                    <div class="form-actions">
                        <button type="submit">Add</button>
                    </div>
                </form>
            </section>
            <h2 class="section-title">Tracked Products</h2>
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
                    Name
                    <input name="name" value="{name}" required>
                </label>
                <label>
                    URL
                    <input name="url" type="url" value="{url}" required>
                </label>
                <label>
                    Target
                    <input name="target_price" type="number" min="1" value="{target_price}" required>
                </label>
            </div>
            <div class="form-actions">
                <button type="submit">Save</button>
            </div>
        </form>
        <form action="/manage/products/{product_id}/delete" method="post" onsubmit="return confirm('Remove this product from tracking?');">
            <div class="form-actions">
                <button class="danger" type="submit">Delete</button>
            </div>
        </form>
    </article>
    """


def build_run_rows(runs):
    if not runs:
        return '<tr><td class="muted" colspan="8">No runs recorded.</td></tr>'

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
        return '<tr><td class="muted" colspan="7">No products recorded.</td></tr>'

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
        return "Pending", "pending"

    if item["consecutive_failures"]:
        return "Failing", "failing"

    return "Healthy", "healthy"


def build_alert_rows(alerts):
    if not alerts:
        return '<tr><td class="muted" colspan="4">No alert events recorded.</td></tr>'

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


def get_chart_period(period):
    if period not in CHART_PERIODS:
        period = DEFAULT_CHART_PERIOD

    label, days = CHART_PERIODS[period]
    return period, label, days


def build_period_tabs(active_period):
    links = []

    for period, (label, _days) in CHART_PERIODS.items():
        active_class = " active" if period == active_period else ""
        current = ' aria-current="page"' if period == active_period else ""
        links.append(
            f'<a class="period-tab{active_class}" href="/?period={period}"'
            f"{current}>{escape(label)}</a>"
        )

    return f'<nav class="period-tabs">{"".join(links)}</nav>'


def build_dashboard_metrics(summaries, period_label):
    product_count = len(summaries)
    reached_count = sum(1 for item in summaries if item["is_target_reached"])
    latest_timestamps = [
        item["latest_checked_at"]
        for item in summaries
        if item["latest_checked_at"]
    ]
    latest_update = max(latest_timestamps) if latest_timestamps else None

    return f"""
    <section class="metrics" aria-label="Price summary">
        <div class="metric">
            <span class="metric-label">Products</span>
            <span class="metric-value">{product_count}</span>
            <span class="metric-sub">tracked SSDs</span>
        </div>
        <div class="metric">
            <span class="metric-label">At Target</span>
            <span class="metric-value">{reached_count}</span>
            <span class="metric-sub">ready to consider</span>
        </div>
        <div class="metric">
            <span class="metric-label">Last Updated</span>
            <span class="metric-value">{escape(format_timestamp(latest_update))}</span>
            <span class="metric-sub">latest price record</span>
        </div>
        <div class="metric">
            <span class="metric-label">Range</span>
            <span class="metric-value">{escape(period_label)}</span>
            <span class="metric-sub">chart window</span>
        </div>
    </section>
    """


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
            <span class="metric-label">Last Run</span>
            <span class="metric-value">{escape(run_status)}</span>
            <span class="metric-sub">{escape(run_time)}</span>
        </div>
        <div class="metric">
            <span class="metric-label">Success</span>
            <span class="metric-value">{escape(run_counts)}</span>
            <span class="metric-sub">successful checks</span>
        </div>
        <div class="metric">
            <span class="metric-label">Failures</span>
            <span class="metric-value">{escape(run_failures)}</span>
            <span class="metric-sub">latest run</span>
        </div>
        <div class="metric">
            <span class="metric-label">Products</span>
            <span class="metric-value">{product_count}</span>
            <span class="metric-sub">{failing_count} failing</span>
        </div>
    </section>
    """


def format_run_status(status):
    labels = {
        "running": "Running",
        "success": "Healthy",
        "skipped": "Skipped",
        "partial_failure": "Partial Failure",
        "failed": "Failed",
    }
    return labels.get(status, status or "-")


@app.post("/check-now")
def check_now():
    run_once()
    return RedirectResponse(url="/", status_code=303)


def format_price(price):
    if price is None:
        return "-"

    return f"{price:,} KRW"


def format_timestamp(timestamp):
    if not timestamp:
        return "-"

    return f"{timestamp} KST"


def build_price_chart(product_id, target_price, period_days, period_label):
    records = list_price_records_for_period(
        product_id,
        period_days,
        limit=MAX_CHART_RECORDS,
    )
    ordered_records = list(reversed(records))

    if not ordered_records:
        return f'<span class="muted">No records in {escape(period_label)}</span>'

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
        f"Price changes over {period_label}. Current {latest_price:,} KRW. "
        f"Low {min_price:,} KRW. High {max_price:,} KRW. "
        f"Target {target_price:,} KRW."
    )

    return f"""
    <div class="trend-panel">
        <div class="trend-head">
            <span><strong>{change_count}</strong> changes</span>
            <span>Target {format_price(target_price)}</span>
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
            <span>Low {format_price(min_price)}</span>
            <span>High {format_price(max_price)}</span>
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
        raise HTTPException(status_code=404, detail="Product not found")

    return product


@app.get("/products/{product_id}/prices")
def product_prices(
    product_id: int,
    limit: int = Query(default=30, ge=1, le=200),
    days: int = Query(default=0, ge=0, le=3650),
):
    product = get_product(product_id)

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    if days > 0:
        return list_price_records_for_period(product_id, days, limit)

    return list_price_records(product_id, limit)


@app.get("/summary")
def summary():
    return get_price_summary()
