from flask import Flask, render_template, request, redirect, Response, stream_with_context, abort
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

NYAA_BASE    = "https://nyaa.si"
SUKEBEI_BASE = "https://sukebei.nyaa.si"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

NYAA_CATEGORY_MAP = {
    "0_0": "All Categories",
    "1_0": "Anime",
    "1_1": "Anime - AMV",
    "1_2": "Anime - English",
    "1_3": "Anime - Non-English",
    "1_4": "Anime - Raw",
    "2_0": "Audio",
    "2_1": "Audio - Lossless",
    "2_2": "Audio - Lossy",
    "3_0": "Literature",
    "3_1": "Literature - English",
    "3_2": "Literature - Non-English",
    "3_3": "Literature - Raw",
    "4_0": "Live Action",
    "4_1": "Live Action - English",
    "4_2": "Live Action - Idol/PV",
    "4_3": "Live Action - Non-English",
    "4_4": "Live Action - Raw",
    "5_0": "Pictures",
    "5_1": "Pictures - Graphics",
    "5_2": "Pictures - Photos",
    "6_0": "Software",
    "6_1": "Software - Apps",
    "6_2": "Software - Games",
}

SUKEBEI_CATEGORY_MAP = {
    "0_0": "All Categories",
    "1_0": "Art",
    "1_1": "Art - Anime",
    "1_2": "Art - Doujinshi",
    "1_3": "Art - Games",
    "1_4": "Art - Manga",
    "1_5": "Art - Pictures",
    "2_0": "Real Life",
    "2_1": "Real Life - Photobooks/Pictures",
    "2_2": "Real Life - Videos",
}

FILTER_MAP = {
    "0": "No Filter",
    "1": "No Remakes",
    "2": "Trusted Only",
}

SITES = {
    "nyaa":    {"base": NYAA_BASE,    "label": "nyaa.si",         "categories": NYAA_CATEGORY_MAP},
    "sukebei": {"base": SUKEBEI_BASE, "label": "sukebei.nyaa.si", "categories": SUKEBEI_CATEGORY_MAP},
}


def get_base(site):
    return SITES.get(site, SITES["nyaa"])["base"]


def scrape_list(query="", category="0_0", filter_val="0", page=1, site="nyaa"):
    base = get_base(site)
    params = {"f": filter_val, "c": category, "q": query, "p": page}
    try:
        resp = requests.get(base, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        torrents = []
        table = soup.find("table", class_="torrent-list")
        if not table:
            return [], 1, 1

        rows = table.find("tbody").find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 8:
                continue

            cat_td    = cols[0]
            cat_link  = cat_td.find("a")
            cat_title = cat_link["title"] if cat_link and cat_link.has_attr("title") else "Unknown"

            name_td    = cols[1]
            links      = name_td.find_all("a")
            title      = ""
            torrent_id = None
            for lnk in links:
                if not lnk.has_attr("class"):
                    title = lnk.get_text(strip=True)
                    href  = lnk.get("href", "")
                    m = re.search(r'/view/(\d+)', href)
                    if m:
                        torrent_id = int(m.group(1))
                    break

            link_td    = cols[2]
            magnet_raw = ""
            for a in link_td.find_all("a"):
                href = a.get("href", "")
                if href.startswith("magnet:"):
                    magnet_raw = href

            size      = cols[3].get_text(strip=True)
            date      = cols[4].get_text(strip=True)
            seeders   = cols[5].get_text(strip=True)
            leechers  = cols[6].get_text(strip=True)
            completed = cols[7].get_text(strip=True)

            row_class = row.get("class", [])
            status = "default"
            if "danger"  in row_class: status = "danger"
            elif "success" in row_class: status = "success"
            elif "warning" in row_class: status = "warning"

            torrents.append({
                "id":           torrent_id,
                "category":     cat_title,
                "title":        title,
                "url":          f"/{site}/view/{torrent_id}" if torrent_id else "#",
                "torrent_file": f"/{site}/download/{torrent_id}.torrent" if torrent_id else "",
                "magnet":       f"/{site}/magnet/{torrent_id}" if torrent_id else magnet_raw,
                "size":         size,
                "date":         date,
                "seeders":      seeders,
                "leechers":     leechers,
                "completed":    completed,
                "status":       status,
            })

        pagination   = soup.find("ul", class_="pagination")
        current_page = page
        total_pages  = 1
        if pagination:
            active = pagination.find("li", class_="active")
            if active:
                try:
                    raw = active.get_text(strip=True)
                    current_page = int(re.sub(r'[^0-9]', '', raw) or page)
                except:
                    current_page = page
            for li in pagination.find_all("li"):
                a = li.find("a")
                if a:
                    try:
                        raw = re.sub(r'[^0-9]', '', a.get_text(strip=True))
                        n   = int(raw)
                        if n > total_pages:
                            total_pages = n
                    except:
                        pass

        return torrents, current_page, total_pages

    except Exception as e:
        print(f"[scrape_list] {site}: {e}")
        return [], 1, 1


def scrape_detail(torrent_id, site="nyaa"):
    base = get_base(site)
    url  = f"{base}/view/{torrent_id}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        title_el = soup.find("h3", class_="panel-title")
        title    = title_el.get_text(strip=True) if title_el else "Unknown"

        info_rows = {}
        for row in soup.select(".panel-body .row"):
            divs = row.find_all("div", recursive=False)
            if len(divs) >= 2:
                key     = divs[0].get_text(strip=True).rstrip(":")
                val_div = divs[1]
                links_in_val = val_div.find_all("a")
                if links_in_val:
                    val = ", ".join(a.get_text(strip=True) for a in links_in_val)
                else:
                    val = val_div.get_text(strip=True)
                if key:
                    info_rows[key] = val

        desc        = soup.find(id="torrent-description")
        description = desc.get_text() if desc else ""

        files_div = soup.find(id="files")
        files     = []
        if files_div:
            for li in files_div.find_all("li"):
                files.append(li.get_text(strip=True))

        magnet_raw = ""
        for a in soup.find_all("a"):
            href = a.get("href", "")
            if href.startswith("magnet:") and not magnet_raw:
                magnet_raw = href

        comments = []
        for panel in soup.select(".comment-panel"):
            user_el = panel.select_one(".col-md-2 a") or panel.select_one(".col-md-2")
            user    = user_el.get_text(strip=True) if user_el else "Anonymous"
            body_el = panel.select_one(".comment-body p")
            body    = body_el.get_text(strip=True) if body_el else ""
            ts_el   = panel.select_one(".comment-body small")
            ts      = ts_el.get_text(strip=True) if ts_el else ""
            comments.append({"user": user, "body": body, "timestamp": ts})

        thumbnail = ""
        for img in soup.select(".torrent-description img, #torrent-description img"):
            src = img.get("src", "")
            if src:
                thumbnail = src if src.startswith("http") else base + src
                break

        return {
            "title":        title,
            "info":         info_rows,
            "description":  description,
            "files":        files,
            "magnet":       f"/{site}/magnet/{torrent_id}",
            "magnet_raw":   magnet_raw,
            "torrent_file": f"/{site}/download/{torrent_id}.torrent",
            "comments":     comments,
            "thumbnail":    thumbnail,
        }
    except Exception as e:
        print(f"[scrape_detail] {site}: {e}")
        return None


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index_default():
    return redirect("/browse?site=nyaa")


@app.route("/browse")
def index():
    site = request.args.get("site", "nyaa")
    if site not in SITES:
        site = "nyaa"

    site_info  = SITES[site]
    query      = request.args.get("q", "")
    category   = request.args.get("c", "0_0")
    filter_val = request.args.get("f", "0")
    try:
        page = int(request.args.get("p", 1))
    except:
        page = 1

    torrents, current_page, total_pages = scrape_list(query, category, filter_val, page, site)
    return render_template(
        "index.html",
        torrents=torrents, query=query, category=category,
        filter_val=filter_val, current_page=current_page,
        total_pages=total_pages,
        categories=site_info["categories"],
        filters=FILTER_MAP,
        site=site,
        site_label=site_info["label"],
        sites=SITES,
    )


@app.route("/<site>/view/<int:torrent_id>")
def view(site, torrent_id):
    if site not in SITES:
        abort(404)
    data = scrape_detail(torrent_id, site)
    if not data:
        return render_template("error.html", message="Gagal memuat detail torrent.")
    return render_template(
        "detail.html", data=data, torrent_id=torrent_id,
        site=site, site_label=SITES[site]["label"]
    )


@app.route("/<site>/download/<int:torrent_id>.torrent")
def download_torrent(site, torrent_id):
    if site not in SITES:
        abort(404)
    base     = get_base(site)
    nyaa_url = f"{base}/download/{torrent_id}.torrent"
    try:
        r = requests.get(nyaa_url, headers=HEADERS, timeout=20, stream=True)
        r.raise_for_status()
        headers_out = {
            "Content-Disposition": f'attachment; filename="{torrent_id}.torrent"',
            "Content-Type":        "application/x-bittorrent",
        }
        return Response(
            stream_with_context(r.iter_content(chunk_size=8192)),
            headers=headers_out, status=200,
        )
    except Exception as e:
        print(f"[download] {site}: {e}")
        abort(502)


@app.route("/<site>/magnet/<int:torrent_id>")
def magnet_redirect(site, torrent_id):
    if site not in SITES:
        abort(404)
    base = get_base(site)
    url  = f"{base}/view/{torrent_id}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a"):
            href = a.get("href", "")
            if href.startswith("magnet:"):
                return redirect(href)
        abort(404)
    except Exception as e:
        print(f"[magnet] {site}: {e}")
        abort(502)


@app.route("/<site>/rss")
def rss_proxy(site):
    if site not in SITES:
        abort(404)
    base     = get_base(site)
    query    = request.args.get("q", "")
    category = request.args.get("c", "1_0")
    try:
        resp = requests.get(
            f"{base}/?page=rss&c={category}&q={query}",
            headers=HEADERS, timeout=10
        )
        return resp.content, 200, {"Content-Type": "application/rss+xml"}
    except:
        return "RSS tidak tersedia", 500


# Legacy redirect compat
@app.route("/view/<int:torrent_id>")
def legacy_view(torrent_id):
    return redirect(f"/nyaa/view/{torrent_id}")

@app.route("/download/<int:torrent_id>.torrent")
def legacy_download(torrent_id):
    return redirect(f"/nyaa/download/{torrent_id}.torrent")

@app.route("/magnet/<int:torrent_id>")
def legacy_magnet(torrent_id):
    return redirect(f"/nyaa/magnet/{torrent_id}")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)


# ════════════════════════════════════════════════════════════════
#  SEO — robots.txt
# ════════════════════════════════════════════════════════════════
@app.route("/robots.txt")
def robots_txt():
    lines = [
        "User-agent: *",
        "Allow: /",
        "",
        "# Block raw download/magnet proxy endpoints — no SEO value",
        "Disallow: /nyaa/download/",
        "Disallow: /sukebei/download/",
        "Disallow: /nyaa/magnet/",
        "Disallow: /sukebei/magnet/",
        "Disallow: /nyaa/rss",
        "Disallow: /sukebei/rss",
        "",
        "# Rate-limit friendly crawl delay",
        "Crawl-delay: 2",
        "",
        f"Sitemap: {request.host_url}sitemap.xml",
        f"Sitemap: {request.host_url}sitemap-nyaa.xml",
        f"Sitemap: {request.host_url}sitemap-sukebei.xml",
    ]
    return "\n".join(lines), 200, {"Content-Type": "text/plain; charset=utf-8"}


# ════════════════════════════════════════════════════════════════
#  SEO — XML Sitemaps
# ════════════════════════════════════════════════════════════════
from datetime import datetime

SITEMAP_ENTRY = '<url><loc>{loc}</loc><lastmod>{date}</lastmod><changefreq>{freq}</changefreq><priority>{priority}</priority></url>'
SITEMAP_HEADER = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
SITEMAP_INDEX_HEADER = '<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'

def make_sitemap_xml(entries):
    parts = [SITEMAP_HEADER]
    for e in entries:
        parts.append(SITEMAP_ENTRY.format(**e))
    parts.append("</urlset>")
    return "\n".join(parts)


@app.route("/sitemap.xml")
def sitemap_index():
    """Master sitemap index — points to sub-sitemaps."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    base  = request.host_url.rstrip("/")
    lines = [
        SITEMAP_INDEX_HEADER,
        f'<sitemap><loc>{base}/sitemap-nyaa.xml</loc><lastmod>{today}</lastmod></sitemap>',
        f'<sitemap><loc>{base}/sitemap-sukebei.xml</loc><lastmod>{today}</lastmod></sitemap>',
        "</sitemapindex>",
    ]
    return "\n".join(lines), 200, {"Content-Type": "application/xml; charset=utf-8"}


@app.route("/sitemap-nyaa.xml")
def sitemap_nyaa():
    """Sitemap for nyaa.si mirror pages."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    base  = request.host_url.rstrip("/")

    entries = [
        {"loc": f"{base}/",                  "date": today, "freq": "hourly",  "priority": "1.0"},
        {"loc": f"{base}/browse?site=nyaa",   "date": today, "freq": "hourly",  "priority": "0.9"},
    ]
    for cat_key, cat_label in NYAA_CATEGORY_MAP.items():
        if cat_key == "0_0":
            continue
        priority = "0.8" if "_0" in cat_key else "0.6"
        entries.append({
            "loc":      f"{base}/browse?site=nyaa&c={cat_key}",
            "date":     today,
            "freq":     "daily",
            "priority": priority,
        })

    return make_sitemap_xml(entries), 200, {"Content-Type": "application/xml; charset=utf-8"}


@app.route("/sitemap-sukebei.xml")
def sitemap_sukebei():
    """Sitemap for sukebei.nyaa.si mirror pages."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    base  = request.host_url.rstrip("/")

    entries = [
        {"loc": f"{base}/browse?site=sukebei", "date": today, "freq": "hourly", "priority": "0.9"},
    ]
    for cat_key, cat_label in SUKEBEI_CATEGORY_MAP.items():
        if cat_key == "0_0":
            continue
        priority = "0.7" if "_0" in cat_key else "0.5"
        entries.append({
            "loc":      f"{base}/browse?site=sukebei&c={cat_key}",
            "date":     today,
            "freq":     "daily",
            "priority": priority,
        })

    return make_sitemap_xml(entries), 200, {"Content-Type": "application/xml; charset=utf-8"}
