"""
Web Scraper Module
Scrapes websites for: title, description, services, products,
contact info, location, FAQ, about, and all text content.
"""

import re
import time
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup


class WebScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })
        self.visited = set()
        self.max_pages = 8  # Limit pages to scrape
        self.timeout = 15

    def scrape(self, base_url: str) -> dict:
        """Main scrape method - returns structured data."""
        parsed = urlparse(base_url)
        base_domain = f"{parsed.scheme}://{parsed.netloc}"
        
        all_data = {
            "base_url": base_url,
            "base_domain": base_domain,
            "title": "",
            "description": "",
            "logo_url": "",
            "pages": {},
            "contact": {},
            "services": [],
            "products": [],
            "faq": [],
            "about": "",
            "location": "",
            "social_links": {},
            "nav_links": [],
            "pages_scraped": 0,
            "data_points": 0,
        }
        
        # Scrape home page first
        home_data = self._scrape_page(base_url)
        if not home_data:
            return None
        
        all_data["title"] = home_data.get("title", "")
        all_data["description"] = home_data.get("meta_description", "")
        all_data["logo_url"] = home_data.get("logo_url", "")
        all_data["pages"][base_url] = home_data
        all_data["pages_scraped"] = 1
        
        # Extract navigation links to scrape key pages
        nav_links = self._extract_nav_links(home_data.get("html", ""), base_domain)
        all_data["nav_links"] = [{"text": l["text"], "url": l["url"]} for l in nav_links[:10]]
        
        # Priority pages to look for
        priority_keywords = ["about", "contact", "service", "product", "faq", "price", 
                             "team", "location", "store", "portfolio", "work"]
        
        pages_to_visit = []
        for link in nav_links:
            url = link["url"]
            text_lower = link["text"].lower()
            if any(kw in text_lower or kw in url.lower() for kw in priority_keywords):
                pages_to_visit.insert(0, url)
            else:
                pages_to_visit.append(url)
        
        # Scrape additional pages
        for url in pages_to_visit[:self.max_pages - 1]:
            if url in self.visited or url == base_url:
                continue
            time.sleep(0.5)  # Be polite
            page_data = self._scrape_page(url)
            if page_data:
                all_data["pages"][url] = page_data
                all_data["pages_scraped"] += 1
        
        # Aggregate all scraped data
        self._aggregate_data(all_data)
        all_data["data_points"] = self._count_data_points(all_data)
        
        return all_data

    def _scrape_page(self, url: str) -> dict | None:
        """Scrape a single page and return structured data."""
        if url in self.visited:
            return None
        self.visited.add(url)
        
        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            
            # Skip non-HTML content
            content_type = resp.headers.get("content-type", "")
            if "text/html" not in content_type:
                return None
            
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Remove script, style, nav noise
            for tag in soup(["script", "style", "noscript", "iframe", "svg"]):
                tag.decompose()
            
            data = {
                "url": url,
                "html": resp.text,
                "title": self._get_title(soup),
                "meta_description": self._get_meta(soup, "description"),
                "meta_keywords": self._get_meta(soup, "keywords"),
                "logo_url": self._get_logo(soup, url),
                "headings": self._get_headings(soup),
                "paragraphs": self._get_paragraphs(soup),
                "contact_info": self._extract_contact(soup, resp.text),
                "links": self._get_links(soup, url),
                "images_alt": self._get_image_alts(soup),
                "lists": self._get_lists(soup),
                "tables": self._get_tables(soup),
                "page_text": self._get_clean_text(soup),
            }
            return data
        
        except Exception as e:
            print(f"  [!] Failed to scrape {url}: {e}")
            return None

    def _get_title(self, soup: BeautifulSoup) -> str:
        og_title = soup.find("meta", property="og:title")
        if og_title:
            return og_title.get("content", "")
        title_tag = soup.find("title")
        return title_tag.get_text(strip=True) if title_tag else ""

    def _get_meta(self, soup: BeautifulSoup, name: str) -> str:
        tag = soup.find("meta", attrs={"name": name})
        if not tag:
            tag = soup.find("meta", property=f"og:{name}")
        return tag.get("content", "") if tag else ""

    def _get_logo(self, soup: BeautifulSoup, page_url: str) -> str:
        for selector in [
            'img[alt*="logo" i]', 'img[src*="logo" i]',
            'a.navbar-brand img', 'a.logo img', '.site-logo img',
            'header img:first-of-type'
        ]:
            logo = soup.select_one(selector)
            if logo and logo.get("src"):
                return urljoin(page_url, logo["src"])
        return ""

    def _get_headings(self, soup: BeautifulSoup) -> list:
        headings = []
        for tag in soup.find_all(["h1", "h2", "h3"]):
            text = tag.get_text(strip=True)
            if text and len(text) > 2:
                headings.append({"level": tag.name, "text": text})
        return headings[:30]

    def _get_paragraphs(self, soup: BeautifulSoup) -> list:
        paras = []
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if len(text) > 30:
                paras.append(text)
        return paras[:20]

    def _extract_contact(self, soup: BeautifulSoup, raw_html: str) -> dict:
        contact = {}
        text = soup.get_text(" ")
        
        # Email
        emails = re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', text)
        emails = [e for e in emails if not any(skip in e.lower() 
                  for skip in ["example", "test", "@sentry", "@webpack", "noreply"])]
        if emails:
            contact["email"] = list(dict.fromkeys(emails))[:3]
        
        # Phone
        phones = re.findall(
            r'(?:\+?\d{1,3}[\s\-.]?)?\(?\d{3,4}\)?[\s\-.]?\d{3,4}[\s\-.]?\d{3,4}(?:[\s\-.]?\d{1,4})?',
            text
        )
        phones = [p.strip() for p in phones if len(re.sub(r'\D', '', p)) >= 7]
        if phones:
            contact["phone"] = list(dict.fromkeys(phones))[:3]
        
        # Address patterns
        address_pattern = re.compile(
            r'\d{1,5}\s+\w+\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|'
            r'Lane|Ln|Drive|Dr|Court|Ct|Way|Place|Pl)[,\s]+\w',
            re.IGNORECASE
        )
        addresses = address_pattern.findall(text)
        if addresses:
            contact["address"] = addresses[:2]
        
        # Social links
        social = {}
        for a in soup.find_all("a", href=True):
            href = a["href"].lower()
            for platform in ["facebook", "twitter", "instagram", "linkedin", 
                             "youtube", "tiktok", "whatsapp"]:
                if platform in href and platform not in social:
                    social[platform] = a["href"]
        if social:
            contact["social"] = social
        
        return contact

    def _get_links(self, soup: BeautifulSoup, page_url: str) -> list:
        links = []
        parsed = urlparse(page_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue
            full_url = urljoin(page_url, href)
            if urlparse(full_url).netloc == parsed.netloc:
                links.append({"text": text, "url": full_url})
        return links[:50]

    def _extract_nav_links(self, html: str, base_domain: str) -> list:
        soup = BeautifulSoup(html, "html.parser")
        links = []
        seen = set()
        
        for nav in soup.find_all(["nav", "header"]):
            for a in nav.find_all("a", href=True):
                href = a["href"]
                text = a.get_text(strip=True)
                if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                    continue
                full_url = urljoin(base_domain, href)
                parsed = urlparse(full_url)
                if parsed.netloc == urlparse(base_domain).netloc and full_url not in seen:
                    seen.add(full_url)
                    links.append({"text": text, "url": full_url})
        return links

    def _get_image_alts(self, soup: BeautifulSoup) -> list:
        alts = [img.get("alt", "").strip() for img in soup.find_all("img") if img.get("alt")]
        return [a for a in alts if len(a) > 2][:20]

    def _get_lists(self, soup: BeautifulSoup) -> list:
        lists = []
        for ul in soup.find_all(["ul", "ol"]):
            items = [li.get_text(strip=True) for li in ul.find_all("li") if li.get_text(strip=True)]
            if 2 <= len(items) <= 20:
                lists.append(items)
        return lists[:10]

    def _get_tables(self, soup: BeautifulSoup) -> list:
        tables = []
        for table in soup.find_all("table"):
            rows = []
            for tr in table.find_all("tr"):
                row = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                if row:
                    rows.append(row)
            if rows:
                tables.append(rows)
        return tables[:5]

    def _get_clean_text(self, soup: BeautifulSoup) -> str:
        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r'\s+', ' ', text)
        return text[:5000]

    def _aggregate_data(self, all_data: dict):
        """Combine data from all pages into structured fields."""
        all_contacts = {}
        all_services = []
        all_products = []
        all_faqs = []
        about_texts = []
        locations = []
        
        service_keywords = ["service", "solution", "offer", "provide", "speciali", "expertise"]
        product_keywords = ["product", "item", "shop", "store", "buy", "purchase", "catalog"]
        faq_keywords = ["faq", "question", "answer", "help", "support"]
        about_keywords = ["about", "who we are", "our story", "mission", "vision", "team"]
        
        for url, page in all_data["pages"].items():
            url_lower = url.lower()
            
            # Aggregate contacts
            contact = page.get("contact_info", {})
            for key, val in contact.items():
                if key not in all_contacts:
                    all_contacts[key] = val
                elif isinstance(val, list) and isinstance(all_contacts[key], list):
                    all_contacts[key] = list(dict.fromkeys(all_contacts[key] + val))
                elif isinstance(val, dict):
                    all_contacts[key].update(val)
            
            # Extract services from service-related pages
            if any(kw in url_lower for kw in service_keywords):
                for heading in page.get("headings", []):
                    if heading["level"] in ["h2", "h3"]:
                        all_services.append(heading["text"])
                for lst in page.get("lists", []):
                    all_services.extend(lst[:10])
            
            # Extract products
            if any(kw in url_lower for kw in product_keywords):
                for heading in page.get("headings", []):
                    if heading["level"] in ["h2", "h3"]:
                        all_products.append(heading["text"])
            
            # Extract FAQ
            if any(kw in url_lower for kw in faq_keywords):
                for i, heading in enumerate(page.get("headings", [])):
                    if "?" in heading["text"]:
                        all_faqs.append({"q": heading["text"], "a": ""})
            
            # Extract about
            if any(kw in url_lower for kw in about_keywords):
                paras = page.get("paragraphs", [])
                if paras:
                    about_texts.append(" ".join(paras[:3]))
            
            # Location from address
            contact_info = page.get("contact_info", {})
            if "address" in contact_info:
                locations.extend(contact_info["address"])
        
        # Also mine home page headings for services
        home_page = all_data["pages"].get(all_data["base_url"], {})
        for heading in home_page.get("headings", []):
            text = heading["text"]
            if any(kw in text.lower() for kw in ["service", "solution", "offer"]):
                all_services.append(text)
        
        all_data["contact"] = all_contacts
        all_data["services"] = list(dict.fromkeys(all_services))[:20]
        all_data["products"] = list(dict.fromkeys(all_products))[:20]
        all_data["faq"] = all_faqs[:15]
        all_data["about"] = about_texts[0] if about_texts else home_page.get("paragraphs", [""])[0]
        all_data["location"] = locations[0] if locations else ""
        all_data["social_links"] = all_contacts.get("social", {})

    def _count_data_points(self, data: dict) -> int:
        count = 0
        if data["title"]: count += 1
        if data["description"]: count += 1
        if data["contact"]: count += len(data["contact"])
        count += len(data["services"])
        count += len(data["products"])
        count += len(data["faq"])
        if data["about"]: count += 1
        if data["location"]: count += 1
        count += len(data["social_links"])
        return count
