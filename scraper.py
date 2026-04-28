import asyncio
import pandas as pd
from datetime import datetime
from playwright.async_api import async_playwright
from fp.fp import FreeProxy # pip install free-proxy
import requests
import smtplib
from email.message import EmailMessage
import os

SCRAPE_CONFIG = {
    "Lanterns Direct": {
        "urls": ["https://www.lanterns-direct.co.uk/collections/flat-roof-skylights"],
        "js": r"""() => {
            const clean = (s) => (s ?? "").toString().replace(/\u00A0/g, " ").replace(/\s+/g, " ").trim();
            const pickText = (root, selectors) => {
                for (const sel of selectors) {
                    const el = root.querySelector(sel);
                    const t = clean(el?.textContent);
                    if (t) return t;
                }
                return "";
            };
            const cards = Array.from(document.querySelectorAll("li.js-pagination-result product-card"));
            return cards.map((card) => {
                const name = pickText(card, [".card__title a", ".card__title", "a.js-prod-link", "a[aria-label]"]);
                const current = pickText(card, [".price__current"]);
                const was = pickText(card, [".price__was", ".price__compare", "s"]);
                return { name, regular_price: was ? was : current, sale_price: was ? current : "" };
            }).filter(r => r.name || r.regular_price || r.sale_price);
        }"""
    },
    "Skylight Depot": {
        "urls": [
            "https://skylightdepot.co.uk/collections/frameless-skylights-flat-roof",
            "https://skylightdepot.co.uk/collections/frameless-skylights-flat-roof?page=2"
        ],
        "js": r"""() => {
            const clean = (s) => (s ?? "").toString().replace(/\u00A0/g, " ").replace(/\s+/g, " ").trim();
            const pickText = (root, selectors) => {
                for (const sel of selectors) {
                    const el = root.querySelector(sel);
                    const t = clean(el?.textContent);
                    if (t) return t;
                }
                return "";
            };
            const cards = Array.from(document.querySelectorAll("[data-product-item]"));
            return cards.map((card) => {
                const name = pickText(card, [".productitem--title a", ".productitem--title", "figure .visually-hidden"]);
                const current = pickText(card, [".price__current[data-price-container] .money", ".price__current .money", ".price__current"]);
                const compareAt = pickText(card, [".price__compare-at.visible .money", ".price__compare-at .money", ".price__compare-at--single"]);
                return { name, regular_price: compareAt ? compareAt : current, sale_price: compareAt ? current : "" };
            }).filter((r) => r.name || r.regular_price || r.sale_price);
        }"""
    },
    "Skylight Factory": {
        "urls": [
            "https://skylightfactory.co.uk/collections/flat-roof-skylights",
            "https://skylightfactory.co.uk/collections/flat-roof-skylights?page=2",
            "https://skylightfactory.co.uk/collections/flat-roof-skylights?page=3"
        ],
        "js": r"""() => {
            const clean = (s) => (s ?? "").toString().replace(/\u00A0/g, " ").replace(/\s+/g, " ").trim();
            const pickText = (root, selectors) => {
                for (const sel of selectors) {
                    const el = root.querySelector(sel);
                    const t = clean(el?.textContent);
                    if (t) return t;
                }
                return "";
            };
            const parsePriceBlock = (root) => {
                const priceWrap = root.querySelector(".product-price") || root.querySelector(".product-variants .product-price") || root;
                const sale = clean(priceWrap.querySelector("del")?.previousSibling?.textContent || priceWrap.querySelector("h6")?.childNodes?.[0]?.textContent || priceWrap.querySelector("h6")?.textContent || "");
                const regular = clean(priceWrap.querySelector("del")?.textContent || "");
                if (!regular) return { regular: sale, sale: "" };
                return { regular, sale: clean(sale.replace(/\|$/, "").trim()) };
            };
            const cards = Array.from(document.querySelectorAll(".product.product-columns"));
            return cards.map((card) => {
                const name = pickText(card, [".product-title a", ".product-details .product-title a", "h4 a"]);
                const { regular, sale } = parsePriceBlock(card);
                return { name, regular_price: regular, sale_price: sale };
            }).filter((r) => r.name || r.regular_price || r.sale_price);
        }"""
    },
    "Hi-Sky": {
        "urls": ["https://hi-sky.co.uk/category/rooflights-flat-roofs/flat-roof-skylights"],
        "js": r"""() => {
            const clean = (s) => (s ?? "").toString().replace(/\u00A0/g, " ").replace(/\s+/g, " ").trim();
            const cards = Array.from(document.querySelectorAll(".product.product-effect"));
            return cards.map((card) => {
                const name = clean(card.querySelector(".product-title a")?.textContent);
                const priceContainer = card.querySelector(".product-price");
                const oldPriceEl = priceContainer?.querySelector(".product-price__old");
                const allSpans = Array.from(priceContainer?.querySelectorAll("span") || []);
                const currentPriceEl = allSpans.find(s => !s.classList.contains("product-price__old"));
                const oldPrice = clean(oldPriceEl?.textContent);
                const currentPrice = clean(currentPriceEl?.textContent);
                return { name, regular_price: oldPrice ? oldPrice : currentPrice, sale_price: oldPrice ? currentPrice : "" };
            }).filter((r) => r.name || r.regular_price);
        }"""
    },
    "Hi-Tech": {
        "urls": [
            "https://hitechrooflights.co.uk/shop/?filter_blind=without-blind",
            "https://hitechrooflights.co.uk/shop/page/2/?filter_blind=without-blind"
        ],
        "js": r"""() => {
            const clean = (s) => (s ?? "").toString().replace(/\u00A0/g, " ").replace(/\s+/g, " ").trim();
            const pickText = (root, selectors) => {
                for (const sel of selectors) {
                    const el = root.querySelector(sel);
                    const t = clean(el?.textContent);
                    if (t) return t;
                }
                return "";
            };
            const cards = Array.from(document.querySelectorAll(".product-small.type-product"));
            return cards.map((card) => {
                const name = pickText(card, [".name.product-title a", ".woocommerce-loop-product__title a", ".product-title a"]);
                const reg = pickText(card, [".price del .woocommerce-Price-amount", ".price del bdi", ".price del"]);
                const sal = pickText(card, [".price ins .woocommerce-Price-amount", ".price ins bdi", ".price ins"]);
                if (!reg && !sal) return { name, regular_price: pickText(card, [".price bdi", ".price"]), sale_price: "" };
                return { name, regular_price: reg || sal, sale_price: reg ? sal : "" };
            }).filter((r) => r.name || r.regular_price || r.sale_price);
        }"""
    },
    "Skylights Rooflight": {
        "urls": ["https://skylights-rooflight.co.uk/collections/flat-rooflights"],
        "js": r"""() => {
            const clean = (s) => (s ?? "").toString().replace(/\u00A0/g, " ").replace(/\s+/g, " ").trim();
            const pickText = (root, selectors) => {
                for (const sel of selectors) {
                    const el = root.querySelector(sel);
                    const t = clean(el?.textContent);
                    if (t) return t;
                }
                return "";
            };
            const cards = Array.from(document.querySelectorAll(".collection-page__product .product-grid-item"));
            return cards.map((card) => {
                const name = pickText(card, [".product-grid-item__product-name"]);
                const current = pickText(card, [".js-product-price"]);
                const compareAt = pickText(card, [".js-product-compare-price"]);
                return { name, regular_price: compareAt || current, sale_price: compareAt ? current : "" };
            }).filter((r) => r.name || r.regular_price || r.sale_price);
        }"""
    }
}

async def get_uk_proxy():
    print("Searching for a working UK proxy...")
    try:
        return FreeProxy(country_id=['GB'], https=True, timeout=2).get()
    except Exception:
        print("Could not fetch a free proxy. Trying without one.")
        return None

async def scrape_url(browser, url, js_script, domain_name):
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-GB",
            timezone_id="Europe/London",
            extra_http_headers={
                "Accept-Language": "en-GB,en;q=0.9"
            }
    )
    page = await context.new_page()
    try:
        print(f"Requesting {url}...")
        response = await page.goto(url, wait_until="domcontentloaded", timeout=90000)

        try:
            await page.get_by_role("button", name="Accept").click(timeout=5000)
            print(f"Cookies accepted for {domain_name}")
        except:
            try:
                await page.locator("button:has-text('Accept')").click(timeout=5000)
                print(f"Cookies accepted for {domain_name}")
            except:
                pass
        
        if response and response.status != 200:
            print(f"WARNING: {domain_name} returned status {response.status}")
        
        await asyncio.sleep(5) # Extra time for grid to render
        data = await page.evaluate(js_script)
        
        if not data:
            await page.screenshot(path=f"debug_{domain_name.replace(' ', '_')}.png")
            print(f"DEBUG: No data found for {domain_name}. Screenshot taken.")
            
        return data
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return []
    finally:
        await page.close()

def scrape_hitech_api():
    results = []

    for page in range(1, 5):  # пробва страници 1 до 4
        url = "https://hitechrooflights.co.uk/wp-json/wc/store/v1/products"

        params = {
            "per_page": 100,
            "page": page,
            "attributes[0][attribute]": "pa_blind",
            "attributes[0][slug]": "without-blind"
        }

        response = requests.get(url, params=params, timeout=30)

        if response.status_code == 400:
            break

        response.raise_for_status()

        products = response.json()

        if not products:
            break

        for p in products:
            name = p.get("name", "")

            prices = p.get("prices", {})
            regular = prices.get("regular_price")
            sale = prices.get("sale_price")
            current = prices.get("price")

            def format_price(value):
                if not value:
                    return ""
                return f"£{int(value) / 100:.2f}"

            results.append({
                "name": name,
                "regular_price": format_price(regular or current),
                "sale_price": format_price(sale) if sale else ""
            })

    return results

def send_email_with_attachment(file_path):
    msg = EmailMessage()
    msg["Subject"] = "Weekly Price Report"
    msg["From"] = os.environ["EMAIL_USER"]
    msg["To"] = "nikoleta@digitalmarketing.bg"

    msg.set_content("Please find attached the weekly price report.")

    with open(file_path, "rb") as f:
        file_data = f.read()

    msg.add_attachment(
        file_data,
        maintype="application",
        subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="Weekly_Prices.xlsx"
    )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(os.environ["EMAIL_USER"], os.environ["EMAIL_PASS"])
        smtp.send_message(msg)

async def main():
    proxy_url = await get_uk_proxy()
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    async with async_playwright() as p:
        args = {'proxy': {'server': proxy_url}} if proxy_url else {}
        browser = await p.chromium.launch(**args, headless=True)
        excel_data = {}

        for domain, config in SCRAPE_CONFIG.items():
            print(f"\n--- Scraping {domain} ---")
            domain_results = []

            if domain == "Hi-Tech":
                items = scrape_hitech_api()
                for item in items:
                    item["date_scraped"] = today_str
                domain_results.extend(items)

            else:
                for url in config["urls"]:
                    items = await scrape_url(browser, url, config["js"], domain)
                    for item in items:
                        item["date_scraped"] = today_str
                    domain_results.extend(items)

            excel_data[domain] = pd.DataFrame(domain_results)

        await browser.close()
        
        with pd.ExcelWriter("Weekly_Prices.xlsx", engine='openpyxl') as writer:
            for domain, df in excel_data.items():
                df.to_excel(writer, sheet_name=domain[:31], index=False)
        print("\nScrape complete! File saved.")
        send_email_with_attachment("Weekly_Prices.xlsx")

if __name__ == "__main__":
    asyncio.run(main())