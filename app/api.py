from html import escape

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse

from app.scheduler import load_products, run_once
from app.storage import (
    get_price_summary,
    get_product,
    initialize_database,
    list_price_records,
    list_products,
    upsert_product,
)

app = FastAPI(title="SSD Price Tracker API")


@app.on_event("startup")
def startup():
    initialize_database()

    for product in load_products():
        upsert_product(
            product["name"],
            product["url"],
            product["target_price"],
        )


@app.get("/", response_class=HTMLResponse)
def root():
    rows = []

    for item in get_price_summary():
        latest_price = format_price(item["latest_price"])
        target_price = format_price(item["target_price"])
        lowest_price = format_price(item["lowest_price"])
        checked_at = item["latest_checked_at"] or "-"
        status = "Reached" if item["is_target_reached"] else "Watching"
        status_class = "reached" if item["is_target_reached"] else "watching"
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
                <td><span class="status {status_class}">{status}</span></td>
            </tr>
            """
        )

    table_rows = "\n".join(rows)

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
                    <a href="/docs">API Docs</a>
                </div>
            </header>
            <table>
                <thead>
                    <tr>
                        <th>Product</th>
                        <th>Latest</th>
                        <th>Target</th>
                        <th>Lowest</th>
                        <th>Trend</th>
                        <th>Checked At</th>
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
        </script>
    </body>
    </html>
    """


@app.post("/check-now")
def check_now():
    run_once()
    return RedirectResponse(url="/", status_code=303)


def format_price(price):
    if price is None:
        return "-"

    return f"{price:,} KRW"


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
