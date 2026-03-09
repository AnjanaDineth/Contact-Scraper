# Universal Contact Info Scraper

A Python script that scrapes **emails, phone numbers, and social media links** from any website — including sites that hide emails behind Cloudflare protection.

---

## Features

- Finds emails hidden behind **Cloudflare protection** (`data-cfemail`)
- Finds emails via `mailto:` links and regex scanning
- Extracts phone numbers
- Finds social media links (Facebook, LinkedIn, Instagram, Twitter, YouTube, etc.)
- **3 scraping modes** - single page, deep crawl, or keyword-filtered crawl
- Saves everything to a clean **CSV file**

---

## Installation

```bash
git clone https://github.com/YOUR_USERNAME/contact-scraper.git
cd contact-scraper
pip install -r requirements.txt
```

---

## Usage

```bash
python contact_scraper.py
```

Enter any URL when prompted, then choose a scraping mode:

```
Enter URL to scrape: https://www.somesite.com

  Choose scraping mode:
  [1] Single page only
      - Scrapes just this URL + checks its /contact page

  [2] Deep mode - follow ALL internal links
      - Scrapes this page then follows every link on it
      - Great for directories or sites with multiple profiles

  [3] Deep mode - follow links matching a keyword
      - Same as above but only follows links containing
        a word you choose (e.g. 'company-profiles', 'team')
```

---

## Example Output

```
  [1/42] some-company
         -> ['info@somecompany.com']
  [2/42] another-company
         -> ['sales@another.com', 'hello@another.com']

  ── Summary ──────────────────────────────────
  Pages with contact info : 38
  Total emails found      : 61
  ─────────────────────────────────────────────

Saved 38 records to 'contacts.csv'
```

**contacts.csv** columns:
| Company/Page Name | URL | Emails | Phones | Facebook | LinkedIn | Instagram | Twitter | YouTube |

---

## Tips

- For a **company directory** (e.g. EDB Sri Lanka exporters), use **mode 3** with keyword `company-profiles`
- For a **team/staff page**, use **mode 2** to follow all internal links
- For a **single company website**, use **mode 1**
- You can scrape **multiple URLs** in one session before saving
- Type `done` at any time to save all results and exit

---

## Requirements

- Python 3.8+
- requests
- beautifulsoup4

---

## ⚠️ Disclaimer

This tool is for **personal research and business development purposes only**. Please respect each website's terms of service. A polite delay is built in between requests to avoid overloading servers.
