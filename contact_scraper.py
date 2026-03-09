"""
Universal Contact Info Scraper (Deep Mode)
===========================================
Enter any website URL and this script will:
  1. Scrape the page you give it
  2. Find ALL internal links on that page
  3. Follow each internal link and scrape contact info from those too
  4. Save everything to contacts.csv

This means if you give it a directory page (like EDB exporters),
it will automatically visit every company profile and grab their emails too.

Usage:
    pip install requests beautifulsoup4
    python contact_scraper.py
"""

import requests
from bs4 import BeautifulSoup
import re
import csv
import time
from urllib.parse import urljoin, urlparse


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def decode_cloudflare_email(encoded_hex):
    """Decode Cloudflare-obfuscated emails (data-cfemail attribute)."""
    try:
        encoded_hex = encoded_hex.strip()
        key = int(encoded_hex[:2], 16)
        email = ""
        for i in range(2, len(encoded_hex), 2):
            email += chr(int(encoded_hex[i:i+2], 16) ^ key)
        return email
    except Exception:
        return ""


def extract_emails(html, soup):
    """Extract all email addresses from a page using 3 methods."""
    emails = set()

    # Method 1: mailto: links
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("mailto:"):
            email = href.replace("mailto:", "").split("?")[0].strip()
            if email:
                emails.add(email)

    # Method 2: Cloudflare data-cfemail attribute
    for a in soup.find_all("a", attrs={"data-cfemail": True}):
        decoded = decode_cloudflare_email(a["data-cfemail"])
        if "@" in decoded:
            emails.add(decoded)

    # Method 3: Regex in raw HTML
    pattern = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
    for email in re.findall(pattern, html):
        if not re.search(r"\.(png|jpg|jpeg|gif|svg|css|js|woff)$", email, re.I):
            emails.add(email)

    return sorted(emails)


def extract_phones(html):
    """Extract phone numbers from raw HTML."""
    phones = set()
    patterns = [
        r"\(\d{2,4}\)\s?\d{3,4}[\s\-]?\d{4}",
        r"\+\d{1,3}[\s\-]?\d{2,4}[\s\-]?\d{3,4}[\s\-]?\d{4}",
        r"\b\d{3}[\s\-]\d{3}[\s\-]\d{4}\b",
    ]
    for pattern in patterns:
        for m in re.findall(pattern, html):
            digits = re.sub(r"\D", "", m)
            if 7 <= len(digits) <= 15:
                phones.add(m.strip())
    return sorted(phones)[:10]


def extract_social_links(soup):
    """Extract social media profile links."""
    social = {}
    domains = {
        "facebook.com": "Facebook",
        "twitter.com": "Twitter",
        "x.com": "X (Twitter)",
        "linkedin.com": "LinkedIn",
        "instagram.com": "Instagram",
        "youtube.com": "YouTube",
        "tiktok.com": "TikTok",
        "pinterest.com": "Pinterest",
        "whatsapp.com": "WhatsApp",
    }
    for a in soup.find_all("a", href=True):
        href = a["href"]
        for domain, name in domains.items():
            if domain in href and name not in social:
                social[name] = href
    return social


def extract_company_name(soup, url):
    """Best-effort company/page name extraction."""
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return h1.get_text(strip=True)
    title = soup.find("title")
    if title:
        return title.get_text(strip=True).split("|")[0].split("-")[0].strip()
    path = urlparse(url).path.rstrip("/")
    return path.split("/")[-1].replace("-", " ").title() if path else url


def fetch_page(session, url):
    """Fetch a URL and return (html, soup) or (None, None) on failure."""
    try:
        resp = session.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        return resp.text, soup
    except Exception:
        return None, None


def get_internal_links(soup, base_domain, base_url, keyword_filter=None):
    """
    Find all internal links on a page.
    If keyword_filter is set, only return links whose URL contains that keyword.
    """
    links = set()
    for a in soup.find_all("a", href=True):
        full = urljoin(base_url, a["href"])
        parsed = urlparse(full)
        if parsed.netloc and parsed.netloc != base_domain:
            continue
        if parsed.scheme not in ("http", "https"):
            continue
        if keyword_filter and keyword_filter not in full:
            continue
        if full.rstrip("/") == base_url.rstrip("/"):
            continue
        links.add(full.rstrip("/") + "/")
    return sorted(links)


# ── Core scraper ──────────────────────────────────────────────────────────────

def scrape_single_page(session, url, visited):
    """Scrape one page and return a result dict."""
    if url in visited:
        return None
    visited.add(url)

    html, soup = fetch_page(session, url)
    if not soup:
        return None

    return {
        "name":   extract_company_name(soup, url),
        "url":    url,
        "emails": extract_emails(html, soup),
        "phones": extract_phones(html),
        "social": extract_social_links(soup),
    }


def scrape_with_deep_mode(start_url, keyword_filter=None, max_pages=500):
    """
    Scrape start_url, then follow ALL internal links found on it.
    keyword_filter: only follow links containing this string
    max_pages: safety limit
    """
    if not start_url.startswith("http"):
        start_url = "https://" + start_url

    parsed      = urlparse(start_url)
    base_domain = parsed.netloc
    visited     = set()
    all_results = []

    print(f"\n{'='*60}")
    print(f"  Starting URL : {start_url}")
    if keyword_filter and keyword_filter != "NONE":
        print(f"  Link filter  : URLs containing '{keyword_filter}'")
    print(f"  Max pages    : {max_pages}")
    print(f"{'='*60}\n")

    with requests.Session() as session:

        # Step 1: Scrape the starting page
        print(f"Fetching starting page...")
        html, soup = fetch_page(session, start_url)
        if not soup:
            print("  Could not load the page. Check the URL and try again.")
            return []

        visited.add(start_url.rstrip("/") + "/")

        start_result = {
            "name":   extract_company_name(soup, start_url),
            "url":    start_url,
            "emails": extract_emails(html, soup),
            "phones": extract_phones(html),
            "social": extract_social_links(soup),
        }
        if start_result["emails"] or start_result["phones"]:
            all_results.append(start_result)

        # Step 2: Single page mode - check /contact page
        if keyword_filter == "NONE":
            for path in ["/contact", "/contact-us", "/contacts"]:
                contact_url = f"{parsed.scheme}://{base_domain}{path}"
                r = scrape_single_page(session, contact_url, visited)
                if r and (r["emails"] or r["phones"]):
                    all_results.append(r)
                    print(f"  Found on contact page: {r['emails']}")
                time.sleep(0.4)

        # Step 3: Deep mode - follow internal links
        else:
            kw = keyword_filter if keyword_filter else None
            internal_links = get_internal_links(soup, base_domain, start_url, kw)

            if not internal_links:
                print("  No internal links found. Try leaving the filter blank.")
            else:
                total = min(len(internal_links), max_pages)
                print(f"Found {len(internal_links)} internal links. Scraping up to {total}...\n")

                for i, link in enumerate(internal_links[:max_pages], 1):
                    label = link.rstrip("/").split("/")[-1]
                    print(f"  [{i}/{total}] {label}")
                    result = scrape_single_page(session, link, visited)
                    if result and (result["emails"] or result["phones"]):
                        all_results.append(result)
                        print(f"         -> {result['emails']}")
                    time.sleep(0.5)

    return all_results


def save_to_csv(results, filename="contacts.csv"):
    """Save all scraped results to CSV."""
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Company/Page Name", "URL",
            "Emails", "Phones",
            "Facebook", "LinkedIn", "Instagram", "Twitter", "YouTube"
        ])
        for r in results:
            writer.writerow([
                r["name"],
                r["url"],
                " | ".join(r["emails"]),
                " | ".join(r["phones"]),
                r["social"].get("Facebook", ""),
                r["social"].get("LinkedIn", ""),
                r["social"].get("Instagram", ""),
                r["social"].get("X (Twitter)", r["social"].get("Twitter", "")),
                r["social"].get("YouTube", ""),
            ])
    print(f"\n  Saved {len(results)} records to '{filename}'")


# ── Main Program ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  Universal Contact Info Scraper")
    print("=" * 60)

    all_results = []

    while True:
        print()
        url = input("Enter URL to scrape (or 'done' to save & exit): ").strip()

        if url.lower() == "done":
            break
        if not url:
            continue

        print()
        print("  Choose scraping mode:")
        print("  [1] Single page only")
        print("      - Scrapes just this URL + checks its /contact page")
        print()
        print("  [2] Deep mode - follow ALL internal links")
        print("      - Scrapes this page, then follows every link on it")
        print("      - Great for any site with multiple pages/profiles")
        print()
        print("  [3] Deep mode - follow links matching a keyword")
        print("      - Same as above but only follows links containing")
        print("        a word you choose (e.g. 'company-profiles', 'team')")
        print()

        mode = input("  Enter 1, 2 or 3: ").strip()

        if mode == "1":
            results = scrape_with_deep_mode(url, keyword_filter="NONE")

        elif mode == "2":
            max_p = input("  Max pages to scrape (press Enter for 200): ").strip()
            max_p = int(max_p) if max_p.isdigit() else 200
            results = scrape_with_deep_mode(url, keyword_filter=None, max_pages=max_p)

        elif mode == "3":
            kw = input("  Keyword to filter links (e.g. 'company-profiles'): ").strip()
            max_p = input("  Max pages to scrape (press Enter for 500): ").strip()
            max_p = int(max_p) if max_p.isdigit() else 500
            results = scrape_with_deep_mode(url, keyword_filter=kw, max_pages=max_p)

        else:
            print("  Invalid option, defaulting to single page.")
            results = scrape_with_deep_mode(url, keyword_filter="NONE")

        all_results.extend(results)

        print(f"\n  ── Summary ──────────────────────────────────")
        print(f"  Pages with contact info : {len(results)}")
        print(f"  Total emails found      : {sum(len(r['emails']) for r in results)}")
        print(f"  ─────────────────────────────────────────────")

    if all_results:
        print()
        filename = input("Save filename (press Enter for 'contacts.csv'): ").strip()
        if not filename:
            filename = "contacts.csv"
        if not filename.endswith(".csv"):
            filename += ".csv"
        save_to_csv(all_results, filename)
    else:
        print("\nNo results to save.")

    print("\nDone!")
