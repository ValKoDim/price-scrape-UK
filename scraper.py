import asyncio
import pandas as pd
from playwright.async_api import async_playwright
from fp.fp import FreeProxy # pip install free-proxy

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
                const regularPrice = was ? was : current;
                const salePrice = was ? current : "";
                return { name, regular_price: regularPrice, sale_price: salePrice };
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
                const regularPrice = compareAt ? compareAt : current;
                const salePrice = compareAt ? current : "";
                return { name, regular_price: regularPrice, sale_price: salePrice };
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
                const saleFixed = clean(sale.replace(/\|$/, "").trim());
                return { regular, sale: saleFixed };
            };
            const cards = Array.from(document.querySelectorAll(".product.product-columns"));
            return cards.map((card) => {
                const name = pickText(card, [".product-title a", ".product-details .product-title a", "h4 a"]);
                const { regular, sale } = parsePriceBlock(card);
                let reg = regular;
                let sal = sale;
                if (!reg && !sal) {
                    const h6 = pickText(card, [".product-price h6", ".product-price", "h6"]);
                    const parts = h6.split("|").map((x) => clean(x)).filter(Boolean);
                    if (parts.length === 2) { sal = parts[0]; reg = parts[1]; } 
                    else if (parts.length === 1) { reg = parts[0]; sal = ""; }
                }
                return { name, regular_price: reg, sale_price: sal };
            }).filter((r) => r.name || r.regular_price || r.sale_price);
        }"""
    },
    "Hi-Sky": {
        "urls": ["https://hi-sky.co.uk/category/rooflights-flat-roofs/flat-roof-skylights"],
        "js": r"""() => {
            const clean = (s) => (s ?? "").toString().replace(/\u00A0/g, " ").replace(/\s+/g, " ").trim();
            
            // Look for all product containers
            const cards = Array.from(document.querySelectorAll(".product.product-effect"));
            
            return cards.map((card) => {
                // Name is inside h3.product-title a
                const nameEl = card.querySelector(".product-title a");
                const name = clean(nameEl?.textContent);

                // Price logic based on your HTML snippet:
                // Current price is usually the first span or a span without a class
                // Old price is in .product-price__old
                const priceContainer = card.querySelector(".product-price");
                const oldPriceEl = priceContainer?.querySelector(".product-price__old");
                
                // If there is an old price, the 'current' price is the other span
                const allSpans = Array.from(priceContainer?.querySelectorAll("span") || []);
                const currentPriceEl = allSpans.find(s => !s.classList.contains("product-price__old"));

                const oldPrice = clean(oldPriceEl?.textContent);
                const currentPrice = clean(currentPriceEl?.textContent);

                return { 
                    name, 
                    regular_price: oldPrice ? oldPrice : currentPrice, 
                    sale_price: oldPrice ? currentPrice : "" 
                };
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
                const regular_price = pickText(card, [".price del .woocommerce-Price-amount", ".price del bdi", ".price del"]);
                const sale_price = pickText(card, [".price ins .woocommerce-Price-amount", ".price ins bdi", ".price ins"]);
                if (!regular_price && !sale_price) {
                    const single = pickText(card, [".price .woocommerce-Price-amount", ".price bdi", ".price"]);
                    return { name, regular_price: single, sale_price: "" };
                }
                if (regular_price && !sale_price) return { name, regular_price, sale_price: "" };
                if (!regular_price && sale_price) return { name, regular_price: sale_price, sale_price: "" };
                return { name, regular_price, sale_price };
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
                const name = pickText(card, [".product-grid-item__product-name", ".product-grid-item__info a.product-grid-item__product-name"]);
                const current = pickText(card, [".product-grid-item__price .js-product-price", ".product-grid-item__price .money.js-product-price"]);
                const compareAt = pickText(card, [".product-grid-item__compare-at-price", ".js-product-compare-price"]);
                const regular_price = compareAt ? compareAt : current;
                const sale_price = compareAt ? current : "";
                return { name, regular_price, sale_price };
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
    # Set a more human-like User Agent
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = await context.new_page()
    
    try:
        print(f"Requesting {url}...")
        response = await page.goto(url, wait_until="networkidle", timeout=60000)
        
        # Check for HTTP errors (403, 404, etc)
        if response.status != 200:
            print(f"WARNING: {domain_name} returned status {response.status}")
        
        # Give extra time for JS to render the product grid
        await asyncio.sleep(5) 
        
        data = await page.evaluate(js_script)
        
        # If we got nothing, take a screenshot to see if we are blocked
        if not data:
            screenshot_path = f"debug_{domain_name.replace(' ', '_')}.png"
            await page.screenshot(path=screenshot_path)
            print(f"DEBUG: No data found for {domain_name}. Screenshot saved to {screenshot_path}")
            # Optional: Print the first 500 chars of HTML to logs
            content = await page.content()
            print(f"HTML Snippet: {content[:500]}")

        return data
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return []
    finally:
        await page.close()

async def main():
    proxy_url = await get_uk_proxy()
    
    async with async_playwright() as p:
        browser_args = {}
        if proxy_url:
            print(f"Using proxy: {proxy_url}")
            browser_args['proxy'] = {"server": proxy_url}
            
        browser = await p.chromium.launch(**browser_args, headless=True)
        excel_data = {}

        for domain, config in SCRAPE_CONFIG.items():
            print(f"\n--- Scraping {domain} ---")
            domain_results = []
            
            for url in config["urls"]:
                print(f"Visiting: {url}")
                items = await scrape_url(browser, url, config["js"])
                print(f"Found {len(items)} items.")
                domain_results.extend(items)
                
            excel_data[domain] = pd.DataFrame(domain_results)

        await browser.close()
        
        file_name = "Weekly_Prices.xlsx"
        print(f"\nSaving data to {file_name}...")
        
        with pd.ExcelWriter(file_name, engine='openpyxl') as writer:
            for domain, df in excel_data.items():
                sheet_name = domain[:31] # Excel limits tab names to 31 chars
                if df.empty:
                    df = pd.DataFrame(columns=["name", "regular_price", "sale_price"])
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                
        print("Scrape and export complete!")

if __name__ == "__main__":
    asyncio.run(main())