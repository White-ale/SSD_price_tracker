from html import escape
from urllib.parse import parse_qs

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.products_config import (
    add_product_to_config,
    load_products,
    remove_product_from_config,
    update_product_in_config,
    validate_product,
)
from app.scheduler import run_once
from app.storage import (
    deactivate_product,
    get_latest_check_run,
    get_price_summary,
    get_product,
    get_product_by_name,
    initialize_database,
    list_price_records,
    list_products,
    sync_products_from_config,
    update_product,
    upsert_product,
)

app = FastAPI(title="SSD Price Tracker API")


@app.on_event("startup")
def startup():
    initialize_database()
    sync_products_from_config(load_products())


@app.get("/", response_class=HTMLResponse)
def root():
    rows = []
    summaries = get_price_summary()
    latest_run = get_latest_check_run()

    for item in summaries:
        latest_price = format_price(item["latest_price"])
        target_price = format_price(item["target_price"])
        lowest_price = format_price(item["lowest_price"])
        checked_at = format_timestamp(
            item["status_last_checked_at"] or item["latest_checked_at"]
        )
        target_status = "Reached" if item["is_target_reached"] else "Watching"
        target_class = "reached" if item["is_target_reached"] else "watching"
        failure_count = item["consecutive_failures"]
        if item["status_last_checked_at"] is None:
            health_status = "Pending"
            health_class = "pending"
        elif failure_count:
            health_status = "Failing"
            health_class = "failing"
        else:
            health_status = "Healthy"
            health_class = "healthy"
        last_error = item["last_error"] or ""
        health_title = (
            f' title="{escape(last_error)}"' if last_error else ""
        )
        price_chart = build_price_chart(item["id"])

        rows.append(
            f"""
            <tr>
                <td>{escape(item["name"])}</td>
                <td>{latest_price}</td>
                <td>{target_price}</td>
                <td>{lowest_price}</td>
                <td>{price_chart}</td>
                <td>{escape(checked_at)}</td>
                <td>{failure_count}</td>
                <td><span class="status {health_class}"{health_title}>{health_status}</span></td>
                <td><span class="status {target_class}">{target_status}</span></td>
            </tr>
            """
        )

    table_rows = "\n".join(rows)
    status_metrics = build_status_metrics(latest_run, summaries)

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

            h1 {{
                margin: 0;
                font-size: 28px;
                font-weight: 700;
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

            .chart {{
                display: block;
                width: 180px;
                height: 52px;
            }}

            .chart-line {{
                fill: none;
                stroke: #2458d3;
                stroke-linecap: round;
                stroke-linejoin: round;
                stroke-width: 3;
            }}

            .chart-area {{
                fill: #eef3fb;
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
                <h1>SSD Price Tracker</h1>
                <div class="actions">
                    <form action="/check-now" method="post" onsubmit="return showChecking(this);">
                        <button type="submit">Check Now</button>
                    </form>
                    <a href="/manage">Manage</a>
                    <a href="/docs">API Docs</a>
                </div>
            </header>
            {status_metrics}
            <table>
                <thead>
                    <tr>
                        <th>Product</th>
                        <th>Latest</th>
                        <th>Target</th>
                        <th>Lowest</th>
                        <th>Trend</th>
                        <th>Checked At</th>
                        <th>Failures</th>
                        <th>Health</th>
                        <th>Target</th>
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
        </script>
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
        run_time = format_timestamp(
            latest_run["finished_at"] or latest_run["started_at"]
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


def build_price_chart(product_id):
    records = list_price_records(product_id, limit=30)
    prices = [record["price"] for record in reversed(records)]

    if not prices:
        return '<span class="muted">-</span>'

    width = 180
    height = 52
    padding = 5
    min_price = min(prices)
    max_price = max(prices)
    price_range = max_price - min_price
    usable_width = width - padding * 2
    usable_height = height - padding * 2
    points = []

    if len(prices) == 1:
        points = [(padding, height / 2), (width - padding, height / 2)]
    else:
        for index, price in enumerate(prices):
            x = padding + (usable_width * index / (len(prices) - 1))

            if price_range == 0:
                y = height / 2
            else:
                y = padding + usable_height * (max_price - price) / price_range

            points.append((x, y))

    line_points = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    area_points = (
        f"{padding},{height - padding} "
        f"{line_points} "
        f"{width - padding},{height - padding}"
    )
    label = escape(
        f"Recent price trend from {min_price:,} KRW to {max_price:,} KRW"
    )

    return f"""
    <svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="{label}">
        <polygon class="chart-area" points="{area_points}"></polygon>
        <polyline class="chart-line" points="{line_points}"></polyline>
    </svg>
    """


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
):
    product = get_product(product_id)

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    return list_price_records(product_id, limit)


@app.get("/summary")
def summary():
    return get_price_summary()
