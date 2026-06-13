from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

description = "Web crawler and structured extractor with depth control, domain guard, and robots.txt checks."
args = {
    "start_url": {"type": "string", "description": "Seed URL to crawl"},
    "max_pages": {"type": "integer", "description": "Maximum pages to visit"},
    "max_depth": {"type": "integer", "description": "Link traversal depth"},
    "extract": {"type": "string", "description": "text | links | tables | metadata"},
    "same_domain_only": {"type": "boolean", "description": "Restrict crawl to start domain"},
    "respect_robots": {"type": "boolean", "description": "Check robots.txt before fetch"},
}
required = ["start_url"]


UA = "SimpleLLM-Crawlee/1.0 (+respect-robots)"


def _allowed_by_robots(url):
    try:
        import urllib.robotparser as robotparser

        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = robotparser.RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(UA, url)
    except Exception:
        return True


def _extract_payload(soup, mode):
    mode = (mode or "text").lower()
    if mode == "links":
        return [a.get("href") for a in soup.select("a[href]")][:200]
    if mode == "tables":
        out = []
        for table in soup.select("table"):
            rows = []
            for tr in table.select("tr"):
                cells = [c.get_text(" ", strip=True) for c in tr.select("th,td")]
                if cells:
                    rows.append(cells)
            if rows:
                out.append(rows)
            if len(out) >= 10:
                break
        return out
    if mode == "metadata":
        title = soup.title.get_text(strip=True) if soup.title else ""
        metas = {}
        for m in soup.select("meta[name],meta[property]"):
            key = (m.get("name") or m.get("property") or "").strip()
            val = (m.get("content") or "").strip()
            if key and val:
                metas[key] = val
        return {"title": title, "meta": metas}
    text = soup.get_text(" ", strip=True)
    return text[:4000]


def main(
    start_url,
    max_pages=5,
    max_depth=1,
    extract="text",
    same_domain_only=True,
    respect_robots=True,
):
    try:
        max_pages = max(1, int(max_pages))
        max_depth = max(0, int(max_depth))
        seed = start_url.strip()
        seed_netloc = urlparse(seed).netloc.lower()

        queue = [(seed, 0)]
        visited = set()
        items = []

        sess = requests.Session()
        sess.headers.update({"User-Agent": UA})

        while queue and len(visited) < max_pages:
            url, depth = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)

            if respect_robots and not _allowed_by_robots(url):
                items.append({"url": url, "skipped": "robots_disallow"})
                continue

            try:
                resp = sess.get(url, timeout=8)
                ctype = resp.headers.get("content-type", "")
                if "text/html" not in ctype:
                    items.append({"url": url, "status": resp.status_code, "skipped": f"content-type:{ctype}"})
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                payload = _extract_payload(soup, extract)
                items.append({"url": url, "status": resp.status_code, "depth": depth, "data": payload})

                if depth < max_depth:
                    for a in soup.select("a[href]"):
                        nxt = urljoin(url, a.get("href"))
                        p = urlparse(nxt)
                        if p.scheme not in ("http", "https"):
                            continue
                        if same_domain_only and p.netloc.lower() != seed_netloc:
                            continue
                        if nxt not in visited:
                            queue.append((nxt, depth + 1))
            except Exception as e:
                items.append({"url": url, "error": str(e)})

        return {
            "start_url": seed,
            "visited_count": len(visited),
            "returned_count": len(items),
            "results": items,
        }
    except Exception as e:
        return {"error": f"crawlee failed: {e}"}
