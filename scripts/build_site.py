#!/usr/bin/env python3
"""Render the static Fleet Fisheries site from the reviewed source content."""
from pathlib import Path
from urllib.parse import quote, urlparse, parse_qs
import html
import json
import re
import shutil
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "pages.json"
ASSET_MAP = ROOT / "content" / "assets.json"
PAGES = json.loads(CONTENT.read_text(encoding="utf-8"))
ASSETS = json.loads(ASSET_MAP.read_text(encoding="utf-8")) if ASSET_MAP.exists() else {}
SEAFOOD_GALLERIES = json.loads((ROOT / "content" / "seafood-galleries.json").read_text(encoding="utf-8"))
BY_SLUG = {p["slug"]: p for p in PAGES}
BASE_URL = "https://www.fleetfisheries.com"

NAV_GROUPS = [
    {
        "label": "Seafood", "href": "/our-products/", "lead": "Wholesale seafood from our fleet",
        "links": [
            ("Sea Scallops", "/sea-scallops/"), ("Lobster", "/lobster/"),
            ("Crab", "/crab/"), ("Wholefish & Fillets", "/fish/"),
        ],
    },
    {
        "label": "Our Fleet", "href": "/our-fleet/", "lead": "Commercial fishing vessels from New Bedford",
        "links": [("Scallop vessels", "/our-fleet/#scallop-vessels"), ("Lobster & crab vessels", "/our-fleet/#lobster-crab-vessels"), ("Vessel jobs", "/vessel-jobs/")],
    },
    {
        "label": "Quality & Sourcing", "href": "/to-the-shore/", "lead": "From the catch through handling and delivery",
        "links": [("Facilities", "/fleet-facilities/"), ("Quality assurance", "/quality-assurance/"), ("Certifications", "/certifications/"), ("Traceability", "/traceability/"), ("Sustainability", "/sustainability/"), ("Best practices", "/best-practices/")],
    },
    {
        "label": "For Buyers", "href": "/to-your-door/", "lead": "Wholesale orders, shipping and account setup",
        "links": [("Shipping", "/shipping/"), ("Credit application", "/credit-application/"), ("Company directory", "/company-directory/"), ("Fisherman's Market", "https://www.fishmanmkt.com/")],
    },
    {
        "label": "About", "href": "/our-story/", "lead": "Our people, history and company updates",
        "links": [("Our story", "/our-story/"), ("Our team", "/meet-our-team/"), ("News archive", "/company-news/"), ("Photos & videos", "/multimedia-gallery/")],
    },
]

ROUTE_ALIASES = {
    "from-the-sea": "/our-products/",
    "list-of-all-fleet-vessels": "/our-fleet/",
}

PDFS = {
    "e54456_17d8a3ed1c324e9a81d117c934ec327f.pdf": "/assets/docs/credit-application.pdf",
    "e54456_3391066e6fae4484b5aa5db0144a344b.pdf": "/assets/docs/certification-scope-1.pdf",
    "e54456_a0a03a2e573d4840ba05d43813431366.pdf": "/assets/docs/certification-scope-2.pdf",
}

PRODUCTS = [
    ("SEA SCALLOPS", "Sea Scallops", "sea-scallops", "Fresh scallops direct from our own fleet."),
    ("LOBSTER", "North American lobster", "lobster", "Ask about lobster products from Fleet Fisheries."),
    ("CRAB", "Crab", "crab", "Ask about our crab products today."),
    ("FRESH FISH", "Wholefish & fillets", "fish", "Swordfish, tuna, halibut and other products from the fish department."),
]

SEAFOOD_PAGE_COPY = {
    "sea-scallops": {
        "eyebrow": "From our own fleet",
        "quality_heading": "Quality checks follow every lot.",
        "quality_copy": "Every lot of Fleet Fisheries scallops is examined by the quality control team. In addition to organoleptic testing, the review includes moisture content, raw and cooked texture, size and color uniformity, and screening for extraneous material.",
        "quality_points": ["Organoleptic testing", "Moisture content", "Raw and cooked texture", "Size and color uniformity", "Extraneous material screening"],
        "fleet_label": "See our scallopers",
        "fleet_href": "/our-fleet/#scallop-vessels",
    },
    "lobster": {
        "eyebrow": "Live North Atlantic lobster",
        "quality_heading": "Live product care at our New Bedford facilities.",
        "quality_copy": "Fleet Fisheries' facilities include a 40,000 lb. lobster pool and a live drip system that can hold an additional 60,000 lb. of live lobster and crab. The system filters the water, supports inventory and grading, and is designed to help decrease mortality.",
        "quality_points": ["Live lobster pool", "Filtered live holding system", "Grading and inventory support"],
        "fleet_label": "See our lobster boats",
        "fleet_href": "/our-fleet/#lobster-crab-vessels",
    },
    "crab": {
        "eyebrow": "Crab products",
        "quality_heading": "Live handling supported by our shore facilities.",
        "quality_copy": "Fleet Fisheries' live drip system is designed for lobster and crab. It can hold an additional 60,000 lb. of live product, filter the water, support inventory and grading, and help decrease mortality.",
        "quality_points": ["Live lobster and crab system", "Filtered water", "Inventory and grading support"],
        "fleet_label": "See our lobster and crab boats",
        "fleet_href": "/our-fleet/#lobster-crab-vessels",
    },
    "fish": {
        "eyebrow": "Wholefish & fillets",
        "quality_heading": "Quality continues through handling and delivery.",
        "quality_copy": "Fleet Fisheries tracks seafood temperature in its coolers, refrigerated trucks and freezers, as well as during freight air travel. Time-temperature indicators support that monitoring from the plant to delivery.",
        "quality_points": ["Swordfish", "Tuna", "Halibut", "Other fish department products"],
        "fleet_label": "See our fishing fleet",
        "fleet_href": "/our-fleet/",
    },
}

SEAFOOD_DESCRIPTIONS = {
    "sea-scallops": "Fresh sea scallops sourced directly from Fleet Fisheries' own commercial fishing fleet. Learn about the lot-by-lot quality checks and contact the sales team.",
    "lobster": "Live North Atlantic lobster from Fleet Fisheries. Explore lobster photos, live handling information and wholesale sales contacts.",
    "crab": "Crab products from Fleet Fisheries, supported by live holding, grading and inventory systems at the New Bedford facilities.",
    "fish": "Wholefish and fillets including swordfish, tuna, halibut and other products from Fleet Fisheries' fish department.",
}

def esc(value):
    return html.escape(str(value or ""), quote=True)

def clean(value):
    return " ".join(str(value or "").replace("\u200b", "").split())

def image_key(image):
    return image.get("key", "")

def image_remote(image, width=1500):
    if image.get("remote_src"):
        return image["remote_src"]
    key = image_key(image)
    if key:
        encoded = quote(key, safe="~._-")
        return f"https://static.wixstatic.com/media/{encoded}/v1/fit/w_{width},h_1200,al_c,q_80/{encoded}"
    return image.get("src", "")

def image_fallback(image):
    key = image_key(image)
    if key and key in ASSETS:
        return ASSETS[key].get("file", "")
    return image.get("fallback", "")

def image_alt(image):
    alt = clean(image.get("alt"))
    if alt and not alt.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
        return alt
    if alt and alt.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
        return alt.rsplit(".", 1)[0].replace("-", " ").replace("_", " ").title()
    key = image_key(image)
    source_name = ASSETS.get(key, {}).get("source_name", "")
    if source_name:
        parts = source_name.split("_")
        return "Fleet Fisheries photo" if len(parts) > 2 else source_name.rsplit(".", 1)[0].replace("-", " ").title()
    return "Fleet Fisheries photo"

def image_tag(image, css="", loading="lazy", width=1500, decorative=False):
    src = image_remote(image, width=width)
    fallback = image_fallback(image)
    original = image.get("src", "")
    alt = "" if decorative else image_alt(image)
    attrs = [f'src="{esc(src)}"', f'alt="{esc(alt)}"', f'loading="{loading}"', 'decoding="async"']
    if css: attrs.append(f'class="{esc(css)}"')
    if fallback: attrs.append(f'data-fallback="{esc(fallback)}"')
    if original and original != src: attrs.append(f'data-original-src="{esc(original)}"')
    return "<img " + " ".join(attrs) + ">"

def image_figure(image, css="", loading="lazy"):
    remote = image_remote(image, width=1800)
    fallback = image_fallback(image)
    alt = image_alt(image)
    target = fallback or remote
    return (f'<figure class="photo-card {esc(css)}"><a class="photo-link" href="{esc(remote)}" data-lightbox '
            f'data-fallback-href="{esc(fallback)}" aria-label="View larger image: {esc(alt)}">'
            f'{image_tag(image, "photo-card__image", loading=loading, width=1500)}</a>'
            f'<figcaption>{esc(alt)}</figcaption></figure>')

def internal_href(href):
    href = html.unescape(str(href or ""))
    for filename, local in PDFS.items():
        if filename in href:
            return local
    if href.startswith("/_files/"):
        return href
    return href

def is_external(href):
    return urlparse(href).scheme in ("http", "https")

def link_html(text, href, css="text-link", extra=""):
    href = internal_href(href)
    if not href: return esc(text)
    target = ' target="_blank" rel="noopener noreferrer"' if is_external(href) else ""
    return f'<a class="{esc(css)}" href="{esc(href)}"{target} {extra}>{esc(text)}</a>'

def fragments_html(fragments, fallback_text=""):
    if not fragments:
        return esc(fallback_text)
    out=[]
    for part in fragments:
        if part.get("type") == "link":
            out.append(link_html(part.get("text", ""), part.get("href", ""), "inline-link"))
        else:
            out.append(esc(part.get("text", "")))
    return " ".join(out)

def short_title(page):
    slug=page["slug"]
    route_titles={"our-products":"Seafood", "to-the-shore":"Quality & Sourcing", "to-your-door":"For Buyers", "sales":"Talk to Sales", "company-news":"News Archive"}
    if slug in route_titles: return route_titles[slug]
    if slug.startswith("fv-"):
        raw=page.get("h1") or page.get("title", "").split(" - ")[0]
        raw=raw.replace("OUR FLEET OF VESSELS", "").strip()
        return raw.title().replace("F/V", "F/V")
    if page.get("h1"):
        value=page["h1"]
    else:
        value=page.get("title", "Fleet Fisheries").split("|")[0].strip()
    special={
        "WHOLEFISH & FILLETS":"Wholefish & Fillets", "HEALTH & WELLNESS":"Health & Wellness",
        "FLEET FACILITIES":"Fleet Facilities", "FLEET SALES TEAM":"Fleet Sales Team",
        "MEET TEAM FLEET":"Meet Team Fleet", "MEDIA GALLERY":"Media Gallery",
        "CREDIT APPLICATION":"Credit Application", "COMPANY DIRECTORY":"Company Directory",
        "BEST PRACTICES":"Best Practices", "QUALITY ASSURANCE":"Quality Assurance",
        "SEA SCALLOPS":"Sea Scallops", "SITE MAP":"Site Map", "FLEET NEWS":"Fleet News",
    }
    if value in special: return special[value]
    if value == value.upper():
        words=value.title()
        words=re.sub(r"\bFda\b", "FDA", words)
        words=re.sub(r"\bMsc\b", "MSC", words)
        words=re.sub(r"\bHaccp\b", "HACCP", words)
        words=re.sub(r"\bIqf\b", "IQF", words)
        return words
    return value

def lead_text(page):
    for block in page.get("blocks", []):
        if block.get("type") == "paragraph" and block.get("text"):
            txt=block["text"]
            if len(txt)>220:
                return txt[:217].rsplit(" ",1)[0]+"…"
            return txt
    return page.get("description", "")

def meaningful_images(page):
    seen=set(); out=[]
    for image in page.get("images", []):
        alt=(image.get("alt") or "").lower()
        key=image_key(image) or image.get("src", "")
        if not key or key in seen or not (image_key(image) or image.get("src")): continue
        if any(x in alt for x in ("v shape", "fleet-background", "just-boat-favicon", "instagram", "sailor", "exclamation", "arrow", "chevron")):
            continue
        seen.add(key); out.append(image)
    return out

def page_image(slug, contains=None, default=0):
    page=BY_SLUG.get(slug)
    if not page: return {"src":"","key":"","fallback":"","alt":"Fleet Fisheries photo"}
    images=meaningful_images(page)
    if contains:
        for image in images:
            test=(image.get("alt", "")+" "+image.get("src", "")).lower()
            if contains.lower() in test: return image
    return images[default] if len(images)>default else (images[0] if images else {"src":"","key":"","fallback":"","alt":"Fleet Fisheries photo"})

def page_description(page):
    if page.get("slug") in SEAFOOD_DESCRIPTIONS:
        return SEAFOOD_DESCRIPTIONS[page["slug"]]
    return page.get("description") or lead_text(page) or f"Fleet Fisheries Inc. — {short_title(page)}."

def header_html(active_slug=""):
    logo_key="e54456_2aa41b75b37943b1b490bf2466166ca4~mv2_d_4000_1283_s_2.png"
    logo={"key":logo_key,"src":"https://static.wixstatic.com/media/"+quote(logo_key,safe="~._-"),"remote_src":"https://static.wixstatic.com/media/e54456_2aa41b75b37943b1b490bf2466166ca4~mv2_d_4000_1283_s_2.png/v1/fill/w_524,h_168,al_c,q_85,usm_0.66_1.00_0.01,enc_avif,quality_auto/NEW-Fleet-Fisheries-Logo-White-Horizonta.png","fallback":ASSETS.get(logo_key,{}).get("file", ""),"alt":"Fleet Fisheries Inc."}
    logo_img=image_tag(logo,"brand-logo",loading="eager",width=620)
    groups=[]
    for i,group in enumerate(NAV_GROUPS):
        items="".join(link_html(label,href,"mega-menu__link") for label,href in group["links"])
        groups.append(f'''<div class="nav-group">
          <button class="nav-trigger" type="button" aria-expanded="false" aria-controls="nav-panel-{i}" data-nav-trigger>
            <span>{esc(group['label'])}</span><svg aria-hidden="true" viewBox="0 0 12 8"><path d="m1 1 5 5 5-5"/></svg>
          </button>
          <div class="mega-menu" id="nav-panel-{i}" hidden>
            <div class="mega-menu__intro"><span class="eyebrow">{esc(group['lead'])}</span>{link_html('Explore '+group['label'],group['href'],'mega-menu__featured')}</div>
            <div class="mega-menu__links">{items}</div>
          </div>
        </div>''')
    return f'''<a class="skip-link" href="#main">Skip to content</a>
      <div class="utility-bar"><div class="utility-bar__inner"><span class="utility-bar__address">20 Blackmer Street · New Bedford, MA 02744</span><div class="utility-bar__actions"><a href="tel:+15089963742">Call (508) 996-3742</a></div></div></div>
      <header class="site-header"><div class="site-header__inner">
        <a class="brand" href="/" aria-label="Fleet Fisheries home">{logo_img}</a>
        <button class="menu-toggle" type="button" aria-expanded="false" aria-controls="primary-nav" data-menu-toggle><span></span><span></span><span></span><span class="sr-only">Open navigation</span></button>
        <nav class="primary-nav" id="primary-nav" aria-label="Primary navigation">
          <a class="nav-home" href="/">Home</a>{''.join(groups)}
          <a class="nav-contact" href="/sales/">Talk to Sales <span aria-hidden="true">↗</span></a>
          <div class="nav-search"><label class="sr-only" for="site-search">Search Fleet Fisheries</label><input id="site-search" type="search" placeholder="Search" autocomplete="off" aria-controls="search-results" aria-expanded="false"><div id="search-results" class="search-results" role="region" aria-label="Search results" hidden></div></div>
        </nav>
      </div></header>'''

def footer_html():
    quick1=''.join(link_html(label,href,'footer-link') for label,href in [("Seafood","/our-products/"),("Our Fleet","/our-fleet/"),("Vessel Jobs","/vessel-jobs/"),("Talk to Sales","/sales/")])
    quick2=''.join(link_html(label,href,'footer-link') for label,href in [("Quality & Sourcing","/to-the-shore/"),("Facilities","/fleet-facilities/"),("Certifications","/certifications/"),("Traceability","/traceability/"),("Shipping","/shipping/"),("Credit Application","/credit-application/"),("Vendor Payment Support","/vendor-ach-data-aggregation-tool/")])
    quick3=''.join(link_html(label,href,'footer-link') for label,href in [("Our Story","/our-story/"),("Our Team","/meet-our-team/"),("Company Directory","/company-directory/"),("News Archive","/company-news/"),("Photos & Videos","/multimedia-gallery/"),("Contact Us","/contact-us/"),("Site Map","/site-map/")])
    socials=[("YouTube","https://www.youtube.com/channel/UCdHBCTiyboBVrBAjgt7dXdg"),("Facebook","https://www.facebook.com/oceansfleet/"),("X","https://twitter.com/fleetfisheries"),("Instagram","https://www.instagram.com/fleetfisheriesinc/")]
    social_html=''.join(link_html(label,href,'social-link') for label,href in socials)
    return f'''<footer class="site-footer"><div class="footer-main"><div class="footer-brand"><a href="/" class="footer-logo">Fleet Fisheries<span>INC.</span></a><p>From the sea, to the shore, to your door.<br>Sourced by our own fishing fleet.</p><p class="footer-address">20 Blackmer Street<br>New Bedford, MA 02744</p><a class="footer-phone" href="tel:+15089963742">(508) 996-3742</a><a class="footer-email" href="mailto:sales@fleetfisheries.com">sales@fleetfisheries.com</a></div><div class="footer-column"><h2>Seafood & fleet</h2>{quick1}</div><div class="footer-column"><h2>Quality & buyer resources</h2>{quick2}</div><div class="footer-column"><h2>Company</h2>{quick3}</div></div><div class="footer-bottom"><span>Fleet Fisheries Inc. · New Bedford, Massachusetts</span><div class="footer-socials" aria-label="Social media">{social_html}</div><span>© <span data-current-year>2026</span> Fleet Fisheries Inc.</span></div></footer>'''

def breadcrumbs_html(page):
    if not page.get("slug"): return ""
    label=short_title(page)
    return f'<nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/">Home</a><span aria-hidden="true">/</span><span aria-current="page">{esc(label)}</span></nav>'

def page_hero(page, image=None, class_name="page-hero", lead=None):
    title=short_title(page)
    image=image or (meaningful_images(page)[0] if meaningful_images(page) else None)
    if page.get("slug")=="meet-our-team":
        image={"src":"/assets/images/asset-0416.webp","fallback":"","key":"","alt":"Fleet Fisheries team at work"}
    elif page.get("slug")=="quality-assurance":
        quality_image=page_image("quality-assurance",contains="scallops-in-blue-gloved-hands")
        image={"src":image_fallback(quality_image),"fallback":"","key":"","alt":"Sea scallops inspected by Fleet Fisheries quality staff"}
    media=(f'<div class="page-hero__media">{image_tag(image,"page-hero__image",loading="eager",width=1800)}</div>' if image and image.get("src") else '<div class="page-hero__media page-hero__media--abstract" aria-hidden="true"></div>')
    title_slug=page.get("slug","")
    group="Our Fleet" if title_slug.startswith("fv-") or title_slug in ("our-fleet","list-of-all-fleet-vessels","vessel-jobs") else "Seafood" if title_slug in ("from-the-sea","our-products","sea-scallops","lobster","crab","fish","health-wellness") else "Quality & Sourcing" if title_slug in ("to-the-shore","certifications","fleet-facilities","quality-assurance","traceability","best-practices","sustainability") else "For Buyers" if title_slug in ("to-your-door","shipping","credit-application","company-directory","sales") else "Fleet Fisheries"
    return f'''<section class="{esc(class_name)}"><div class="page-hero__shade"></div>{media}<div class="page-hero__content"><p class="eyebrow">{esc(group)} · New Bedford, Massachusetts</p><h1>{esc(title)}</h1>{f'<p class="page-hero__lead">{esc(lead)}</p>' if lead else ''}</div></section>'''

def is_decorative(image):
    alt=(image.get("alt","")+" "+image.get("src","")).lower()
    return any(x in alt for x in ("v shape", "fleet-background", "just-boat-favicon", "instagram.png", "sailor", "exclamation", "arrow", "chevron"))

def render_photo_group(images, class_name="photo-grid"):
    filtered=[]; seen=set()
    for img in images:
        k=image_key(img) or img.get("src","")
        if is_decorative(img) or not k or k in seen: continue
        seen.add(k); filtered.append(img)
    if not filtered: return ""
    figures=''.join(image_figure(img) for img in filtered)
    return f'<div class="{esc(class_name)}">{figures}</div>'

def render_image_grid(images, class_name="photo-grid"):
    """Render a clean, caption-free image grid with accessible lightbox links."""
    filtered=[]; seen=set()
    for image in images:
        key=image_key(image) or image.get("src","")
        if is_decorative(image) or not key or key in seen: continue
        seen.add(key); filtered.append(image)
    if not filtered: return ""
    figures=[]
    for image in filtered:
        remote=image_remote(image,width=1800)
        fallback=image_fallback(image)
        alt=image_alt(image)
        figures.append(
            f'<figure class="photo-card photo-card--quiet"><a class="photo-link" href="{esc(remote)}" data-lightbox '
            f'data-fallback-href="{esc(fallback)}" aria-label="View larger image: {esc(alt)}">'
            f'{image_tag(image,"photo-card__image",loading="lazy",width=1400)}</a></figure>'
        )
    return f'<div class="{esc(class_name)}">{"".join(figures)}</div>'

def paragraph_html(block, css="body-copy"):
    return f'<p class="{esc(css)}">{fragments_html(block.get("fragments"),block.get("text",""))}</p>'

def table_cell(value):
    value=clean(value)
    if re.search(r"^[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}$",value):
        return f'<a href="mailto:{esc(value)}">{esc(value)}</a>'
    if re.search(r"(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}",value):
        digits=re.sub(r"\D", "", value)
        if len(digits)==10: digits="1"+digits
        return f'<a href="tel:+{digits}">{esc(value)}</a>'
    return esc(value)

def render_table(block):
    rows=block.get("rows",[])
    if not rows: return ""
    headers=rows[0]
    th=''.join(f'<th scope="col">{esc(x)}</th>' for x in headers)
    trs=[]
    for row in rows[1:]:
        cells=''.join(f'<td data-label="{esc(headers[i] if i<len(headers) else "Details")}">{table_cell(v)}</td>' for i,v in enumerate(row))
        trs.append(f'<tr>{cells}</tr>')
    return f'<div class="table-wrap" tabindex="0" aria-label="Scrollable contact table"><table><thead><tr>{th}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'

def block_html(block):
    kind=block.get("type")
    if kind=="heading":
        level=block.get("level",2)
        if level==1: level=2
        return f'<h{level} class="content-heading">{esc(block.get("text",""))}</h{level}>'
    if kind=="paragraph": return paragraph_html(block)
    if kind=="list":
        tag="ol" if block.get("ordered") else "ul"
        items=''.join(f'<li>{fragments_html(x.get("fragments"),x.get("text",""))}</li>' for x in block.get("items",[]))
        return f'<{tag} class="content-list">{items}</{tag}>'
    if kind=="table": return render_table(block)
    if kind=="link":
        href=internal_href(block.get("href",""))
        if "youtube.com/watch" in href or "youtu.be/" in href:
            return link_html(block.get("text","Watch video"),href,"pill-link pill-link--outline")
        return link_html(block.get("text","Learn more"),href,"inline-cta")
    if kind=="video":
        src=block.get("src","")
        parsed=urlparse(src)
        if "youtube" in (parsed.netloc or "") or "youtu.be" in (parsed.netloc or ""):
            q=parse_qs(parsed.query)
            vid=q.get("v",[""])[0]
            if "youtu.be" in (parsed.netloc or ""): vid=parsed.path.strip("/").split("/")[0]
            if "/embed/" in parsed.path: vid=parsed.path.split("/embed/",1)[1].split("/",1)[0]
            if vid: src=f"https://www.youtube-nocookie.com/embed/{esc(vid)}?rel=0"
        title=block.get("title") or "Fleet Fisheries video"
        return f'<div class="video-frame"><iframe src="{esc(src)}" title="{esc(title)}" loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe></div>'
    return ""

def render_blocks(page, skip_hero=None, skip_lead=True, skip_first_heading=True, image_limit=6):
    blocks=page.get("blocks",[])
    first_heading=True; first_para=skip_lead; hero_key=image_key(skip_hero) if skip_hero else ""
    output=[]; image_buffer=[]; image_count=0; overflow_images=[]
    def flush_images():
        nonlocal image_buffer, image_count
        if image_buffer:
            available=max(0,image_limit-image_count)
            visible=image_buffer[:available]
            hidden=image_buffer[available:]
            if visible: output.append(render_photo_group(visible))
            image_count+=len(visible)
            overflow_images.extend(hidden)
            image_buffer=[]
    for block in blocks:
        kind=block.get("type")
        if kind=="heading" and first_heading and skip_first_heading and block.get("level")==1:
            first_heading=False; continue
        if kind=="heading" and block.get("level")==1 and first_heading:
            first_heading=False
        if kind=="paragraph" and first_para:
            first_para=False
            continue
        if kind=="image":
            key=image_key(block)
            if is_decorative(block) or not (key or block.get("src")) or (hero_key and key==hero_key): continue
            image_buffer.append(block); continue
        flush_images()
        if kind=="paragraph" and block.get("text")=="Thanks for submitting!": continue
        if kind=="heading" and block.get("text")=="THANK YOU.": continue
        html_block=block_html(block)
        if html_block: output.append(html_block)
    flush_images()
    if overflow_images:
        output.append(f'<details class="gallery-more"><summary>View {len(overflow_images)} more photos</summary>{render_photo_group(overflow_images)}</details>')
    return ''.join(output)

def standard_page(page, extra="", hero=None, lead=None, after_intro="", image_limit=6):
    hero=hero or (meaningful_images(page)[0] if meaningful_images(page) else None)
    lead=lead if lead is not None else lead_text(page)
    intro=page_hero(page,hero,lead=lead)
    body=render_blocks(page,skip_hero=hero,image_limit=image_limit)
    return f'{breadcrumbs_html(page)}{intro}<div class="page-content"><div class="content-width">{after_intro}{extra}{body}</div></div>'

def home_html():
    home=BY_SLUG.get(""); h=home.get("images",[]) if home else []
    image=h[0] if h else page_image("our-fleet")
    hero=f'''<section class="home-hero home-hero--static"><div class="home-hero__image">{image_tag(image,"home-hero__photo",loading="eager",width=2200)}</div><div class="home-hero__veil"></div><div class="home-hero__content"><p class="eyebrow">New Bedford, Massachusetts</p><h1>Seafood from our own fleet.</h1><p>Commercial fishing and wholesale seafood, handled from source.</p><div class="button-row">{link_html("Explore our seafood","/our-products/","button button--light")}{link_html("Talk to Sales","/sales/","button button--outline")}</div></div><a class="hero-scroll" href="#journey">Explore Fleet Fisheries <span aria-hidden="true">↓</span></a></section>'''
    step_cards=[
        ("01", "From the sea", "Our own fishing fleet harvests scallops, lobster, crab, and fish.", "/our-products/", page_image("our-fleet")),
        ("02", "To the shore", "Fleet Fisheries’ shore-side facilities are located in historic New Bedford, Massachusetts.", "/to-the-shore/", page_image("fleet-facilities")),
        ("03", "To your door", "Fleet Fisheries works with carriers including DSL, FedEx, American Airlines and others.", "/to-your-door/", page_image("shipping")),
    ]
    steps=''.join(f'''<a class="journey-card" href="{href}"><div class="journey-card__photo">{image_tag(img,"",loading="lazy",width=850)}</div><div class="journey-card__copy"><span class="journey-number">{num}</span><h3>{esc(title)}</h3><p>{esc(copy)}</p><span class="arrow-link">Explore <span aria-hidden="true">↗</span></span></div></a>''' for num,title,copy,href,img in step_cards)
    product_cards=[]
    for label,title,slug,copy in PRODUCTS:
        source_page=BY_SLUG.get("our-products")
        candidate=None
        if source_page:
            for image in source_page.get("images",[]):
                if label.lower().split()[0] in (image.get("alt","")+" "+image.get("src","")).lower():
                    candidate=image; break
        if not candidate: candidate=page_image(slug)
        product_cards.append(f'''<a class="product-card" href="/{slug}/"><div class="product-card__photo">{image_tag(candidate,"",loading="lazy",width=900)}</div><div class="product-card__body"><span class="eyebrow">{esc(label)}</span><h3>{esc(title)}</h3><p>{esc(copy)}</p><span class="arrow-link">View product <span aria-hidden="true">↗</span></span></div></a>''')
    home_images=home.get("images",[]) if home else []
    brand_images=[i for i in home_images if any(w in (i.get("alt","")+" "+i.get("src","")).lower() for w in ("brand","scallop","crab-logo"))][-4:]
    brand_grid=''.join(f'<div class="brand-mark">{image_tag(i,"",loading="lazy",width=520)}</div>' for i in brand_images)
    facilities=BY_SLUG.get("fleet-facilities",{}).get("search_text","")
    stats=[("20,000 sq ft", "Individual Quick Frozen (IQF) plant"),("45,000 sq ft", "Fresh processing plant"),("60+", "Production associates across both facilities"),("40,000 lb", "Capacity lobster pool")]
    stat_html=''.join(f'<div class="stat-card"><strong>{esc(num)}</strong><span>{esc(label)}</span></div>' for num,label in stats)
    return f'''{hero}
      <section class="section section--paper" id="journey"><div class="section-heading"><p class="eyebrow">From the sea, to the shore, to your door</p><h2>One seafood journey.<br><em>Our own fishing fleet.</em></h2><p>Fleet Fisheries is a New Bedford seafood company sourcing fresh seafood through its own fishing fleet.</p></div><div class="journey-grid">{steps}</div></section>
      <section class="section section--dark"><div class="section-heading section-heading--light"><p class="eyebrow">Our products</p><h2>Fresh from the source.</h2><p>Sea scallops · North Atlantic lobster · crab · whole fish · fish fillets &amp; more</p></div><div class="product-grid">{"".join(product_cards)}</div><div class="section-action">{link_html("Explore all products","/our-products/","button button--light")}</div></section>
      <section class="section section--sea"><div class="split-feature"><div class="split-feature__image">{image_tag(page_image("our-fleet"),"",loading="lazy",width=1500)}</div><div class="split-feature__copy"><p class="eyebrow">A fleet built in New Bedford</p><h2>Meet the vessels behind the catch.</h2><p>See Fleet Fisheries’ commercial fishing vessels, fleet history and vessel profiles.</p><div class="button-row">{link_html("See our fleet","/our-fleet/","button button--dark")}{link_html("View vessel list","/list-of-all-fleet-vessels/","text-link text-link--light")}</div></div></div></section>
      <section class="section section--paper"><div class="section-heading"><p class="eyebrow">To the shore</p><h2>Facilities in historic<br><em>New Bedford.</em></h2><p>Fleet Fisheries’ facilities include an IQF plant, a fresh processing plant, cooler space and a live lobster and crab system.</p></div><div class="stats-grid">{stat_html}</div><div class="section-action">{link_html("Explore our facilities","/fleet-facilities/","button button--dark")}</div></section>
      <section class="credit-callout"><div class="credit-callout__image">{image_tag(home_images[6] if len(home_images)>6 else page_image("credit-application"),"",loading="lazy",width=1500)}</div><div class="credit-callout__copy"><p class="eyebrow">Working with Fleet Fisheries</p><h2>Begin your journey with Fleet today.</h2><p>Download the credit application to get started.</p>{link_html("Credit application","/credit-application/","button button--light")}</div></section>
      {f'<section class="section section--paper section--brands"><div class="section-heading section-heading--compact"><p class="eyebrow">Brands</p><h2>Fleet Fisheries products</h2></div><div class="brand-grid">{brand_grid}</div></section>' if brand_grid else ''}'''

def current_fleet_cards():
    page=BY_SLUG.get("our-fleet",{}); blocks=page.get("blocks",[])
    group="Fleet Scallop Vessels"; cards=[]; last_image=None
    for block in blocks:
        if block.get("type")=="heading":
            if "Scallop" in block.get("text",""): group="Fleet Scallop Vessels"
            elif "Lobster" in block.get("text","") or "Crab" in block.get("text",""): group="Fleet Lobster & Crab Vessels"
        if block.get("type")=="image" and not is_decorative(block): last_image=block
        if block.get("type")=="paragraph" and block.get("text","").startswith("F/V "):
            name=block["text"]
            href=next((x.get("href") for x in block.get("fragments",[]) if x.get("type")=="link" and x.get("href","").startswith("/fv-")),"")
            next_text=""
            # The vessel type and any captain name follow the name in the source page.
            idx=blocks.index(block)
            for nxt in blocks[idx+1:idx+4]:
                if nxt.get("type")=="paragraph":
                    next_text += " "+nxt.get("text","")
            img=last_image or page_image("our-fleet")
            if href:
                slug=href.strip("/").split("/")[0]
                detail=BY_SLUG.get(slug)
                if detail and meaningful_images(detail): img=meaningful_images(detail)[0]
            cards.append({"name":name,"href":href,"group":group,"description":clean(next_text),"image":img})
            last_image=None
    return cards

def render_fleet():
    page=BY_SLUG["our-fleet"]
    vessels=[p for p in PAGES if p["slug"].startswith("fv-")]
    groups=[]
    for category,anchor in [("Scallop fishing vessels","scallop-vessels"),("Lobster & crab fishing vessels","lobster-crab-vessels")]:
        section=[p for p in vessels if vessel_category(p)==category]
        if not section: continue
        groups.append(f'<section class="fleet-category fleet-category--directory" id="{anchor}" data-vessel-group="{esc(category)}"><div class="fleet-category__heading"><p class="eyebrow">{len(section)} vessels</p><h2>{esc(category)}</h2><p>Open a profile for vessel specifications and photographs.</p></div><div class="vessel-grid">{"".join(render_vessel_card(p) for p in section)}</div></section>')
    hero=meaningful_images(page)[0] if meaningful_images(page) else None
    return f'''{breadcrumbs_html(page)}{page_hero(page,hero,lead="Browse the vessels by fishery, then open a profile to see its specifications and photos.")}
      <div class="page-content"><div class="content-width fleet-directory"><div class="fleet-tools"><label for="vessel-search">Find a vessel</label><input id="vessel-search" type="search" placeholder="Search vessel names" autocomplete="off"><div class="fleet-filters" role="group" aria-label="Filter vessels"><button type="button" data-vessel-filter="all" aria-pressed="true">All vessels</button><button type="button" data-vessel-filter="Scallop fishing vessels" aria-pressed="false">Scallop</button><button type="button" data-vessel-filter="Lobster &amp; crab fishing vessels" aria-pressed="false">Lobster &amp; crab</button></div><p class="fleet-result-count" aria-live="polite">Showing {len(vessels)} vessels</p></div>{''.join(groups)}<p class="fleet-no-results" hidden>No vessels match that search.</p><section class="fleet-media-link"><p class="eyebrow">Fleet Fisheries media</p><h2>See the fleet at work.</h2><p>Explore videos and photographs from the Fleet Fisheries archive.</p>{link_html('Open photos & videos','/multimedia-gallery/','button button--outline')}</section></div></div>'''

def vessel_category(page, subtitle="", spec=None):
    spec=spec or {}
    source=" ".join([subtitle, str(spec.get("Fishery Type","")), page.get("title",""), page.get("h1","")]).lower()
    if "scallop" in source: return "Scallop fishing vessels"
    if "lobster" in source or "crab" in source: return "Lobster & crab fishing vessels"
    return "Commercial fishing vessels"

def vessel_images(page):
    title=short_title(page)
    slug_tokens=[x for x in re.findall(r"[a-z0-9]+",page.get("slug","").lower().replace("fv-","",1)) if x not in ("and","the")]
    images=page.get("images",[])
    product_only=("naked-catch", "live-lobster", "lobster-istock", "big-boy-premium-scallops", "scallops-in-blue-gloved-hands", "crab-on-ice", "crate-of-crabs", "swordfish-on-ice", "logo", "tops-of-boats")
    def description(image):
        return " ".join([str(image.get("alt","")), str(image.get("src","")), str(ASSETS.get(image_key(image),{}).get("source_name",""))]).lower().replace("%20"," ")
    def eligible(image, index):
        text=description(image)
        if is_decorative(image) or any(term in text for term in product_only): return False
        if text.strip() in ("sub", "submarine"): return False
        if index==0: return True
        if not clean(image.get("alt")): return True
        return slug_tokens and all(token in text for token in slug_tokens)
    selected=[]; seen=set()
    for index,image in enumerate(images):
        key=image_key(image) or image.get("src","")
        if not key or key in seen or not eligible(image,index): continue
        seen.add(key)
        item=dict(image)
        if not clean(item.get("alt")):
            item["alt"]=f"{title} vessel photo"
        selected.append(item)
    return selected

def vessel_data(page):
    title=short_title(page)
    subtitle=""
    for b in page.get("blocks",[]):
        if b.get("type")=="paragraph" and any(x in b.get("text","").upper() for x in ("FISHING VESSEL","SCALLOP","CRAB")):
            subtitle=b["text"]; break
    full=" ".join(b.get("text","") for b in page.get("blocks",[]) if b.get("type")=="paragraph")
    spec={}
    labels=["Year Built","Year of Completion","Hull Type","Hailing Port","Hauling Port","Gross / Net Tonnage","Gross Tonnage","Gross / Net","Gross / Net Tonnage","Tonnage","Length","Beam / Breadth","Breadth","Beam","Draft Depth","Origin of Build","Fishery Type","Vessel’s Captain","Vessel's Captain","Captains","Builder","Engine"]
    pattern=re.compile(r"("+"|".join(re.escape(x) for x in sorted(set(labels),key=len,reverse=True))+r")\s*:\s*",re.I)
    matches=list(pattern.finditer(full))
    for i,m in enumerate(matches):
        value=full[m.end():matches[i+1].start() if i+1<len(matches) else len(full)].strip(" |;")
        if value: spec[m.group(1).rstrip(":")]=value
    registry=""
    for b in page.get("blocks",[]):
        if b.get("type")=="heading" and b.get("text","").isdigit(): registry=b["text"]
    images=vessel_images(page)
    return title,subtitle,spec,registry,images

def vessel_card_facts(spec):
    facts=[]
    year=spec.get("Year Built") or spec.get("Year of Completion")
    length=spec.get("Length")
    port=spec.get("Hailing Port") or spec.get("Hauling Port")
    for label,value in (("Built",year),("Length",length),("Home port",port)):
        if value: facts.append((label,value))
    return facts

def render_vessel_card(page):
    title,subtitle,spec,registry,photos=vessel_data(page)
    image=photos[0] if photos else None
    category=vessel_category(page,subtitle,spec)
    facts="".join(f'<div><dt>{esc(label)}</dt><dd>{esc(value)}</dd></div>' for label,value in vessel_card_facts(spec))
    registry_html=f'<span class="vessel-card__registry">Vessel No. {esc(registry)}</span>' if registry else ""
    return f'''<a class="vessel-card vessel-card--profile" href="{esc(page['path'])}"><div class="vessel-card__photo">{image_tag(image,"",loading="lazy",width=1000) if image else ''}<span class="vessel-card__type">{esc(category.replace(' vessels',''))}</span></div><div class="vessel-card__body"><h3>{esc(title)}</h3>{registry_html}<dl class="vessel-card__facts">{facts}</dl><span class="arrow-link">Open vessel profile <span aria-hidden="true">↗</span></span></div></a>'''

def render_vessel(page):
    title,subtitle,spec,registry,images=vessel_data(page)
    hero=images[0] if images else None
    category=vessel_category(page,subtitle,spec).replace(" vessels","")
    label=subtitle or spec.get("Fishery Type") or "Commercial fishing vessel"
    hero_html=(f'<div class="vessel-profile-hero__media">{image_tag(hero,"vessel-profile-hero__image",loading="eager",width=2200)}</div>' if hero else '<div class="vessel-profile-hero__media vessel-profile-hero__media--empty"></div>')
    identity=f'<div class="vessel-profile-hero__number"><span>Vessel number</span><strong>{esc(registry)}</strong></div>' if registry else ""
    spec_html=''.join(f'<div class="vessel-spec-item"><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>' for k,v in spec.items())
    gallery_images=images[1:]
    gallery=render_image_grid(gallery_images[:6],"photo-grid photo-grid--vessel-profile")
    if len(gallery_images)>6:
        gallery+=f'<details class="gallery-more"><summary>View all {len(gallery_images)} vessel photographs</summary>{render_image_grid(gallery_images[6:],"photo-grid photo-grid--vessel-profile")}</details>'
    return f'''{breadcrumbs_html(page)}<section class="vessel-profile-hero">{hero_html}<div class="vessel-profile-hero__shade"></div><div class="vessel-profile-hero__content"><p class="eyebrow">{esc(category)}</p><h1>{esc(title)}</h1><p class="vessel-profile-hero__lead">{esc(label)}</p>{identity}{link_html("View all vessels","/our-fleet/","button button--light")}</div></section>
      <section class="vessel-specs-section"><div class="content-width"><div class="vessel-section-heading"><p class="eyebrow">Fleet vessel profile</p><h2>Vessel specifications</h2></div>{f'<dl class="vessel-spec-grid">{spec_html}</dl>' if spec_html else '<p>Vessel specifications are not available on the public source page.</p>'}</div></section>
      {f'<section class="vessel-gallery-section"><div class="content-width"><div class="vessel-section-heading"><p class="eyebrow">On the water</p><h2>{esc(title)} photographs</h2></div>{gallery}</div></section>' if gallery else ''}
      <section class="vessel-profile-footer"><div class="content-width"><p class="eyebrow">Fleet Fisheries Inc.</p><h2>Explore the full fishing fleet.</h2>{link_html("Browse all vessel profiles","/our-fleet/","button button--light")}</div></section>'''

def render_all_vessels():
    page=BY_SLUG["list-of-all-fleet-vessels"]
    vessels=[p for p in PAGES if p["slug"].startswith("fv-")]
    hero=meaningful_images(page)[0] if meaningful_images(page) else None
    groups=[]
    for category,anchor in [("Scallop fishing vessels","scallop-vessels"),("Lobster & crab fishing vessels","lobster-crab-vessels"),("Commercial fishing vessels","other-vessels")]:
        section=[p for p in vessels if vessel_category(p)==category]
        if section:
            groups.append(f'<section class="fleet-category fleet-category--directory" id="{anchor}"><div class="fleet-category__heading"><p class="eyebrow">{len(section)} vessels</p><h2>{esc(category)}</h2><p>Open a profile for vessel specifications and photographs.</p></div><div class="vessel-grid">{"".join(render_vessel_card(p) for p in section)}</div></section>')
    return f'''{breadcrumbs_html(page)}{page_hero(page,hero,lead="Browse every public vessel profile, organized by fishery.")}<div class="page-content"><div class="content-width fleet-directory">{"".join(groups)}</div></div>'''

def possible_name(text):
    text=clean(text)
    if not text or len(text)>65 or re.search(r"\d|@|:|\$",text): return False
    if text.lower().startswith(("main", "direct", "ext", "cell", "executive assistant", "fleet fisheries", "looking for", "contact", "thank")): return False
    words=text.replace("&"," ").replace("."," ").split()
    return 2<=len(words)<=6 and any(w[:1].isupper() for w in words)

def person_cards(page):
    blocks=page.get("blocks",[]); candidates=[]
    for i,b in enumerate(blocks):
        if b.get("type")!="image" or is_decorative(b): continue
        # Headshots are followed by a person's name; cover images and decorative backgrounds are not.
        name_index=None
        for j in range(i+1,min(i+7,len(blocks))):
            nxt=blocks[j]
            if nxt.get("type")=="heading": break
            if nxt.get("type")=="image" and is_decorative(nxt): continue
            if nxt.get("type")=="paragraph" and possible_name(nxt.get("text","")):
                name_index=j; break
        if name_index is not None:
            candidates.append((i,name_index,b))
    people=[]
    for n,(img_i,name_i,img) in enumerate(candidates):
        end=candidates[n+1][1] if n+1<len(candidates) else len(blocks)
        texts=[b.get("text","") for b in blocks[name_i:end] if b.get("type")=="paragraph" and b.get("text")]
        if not texts: continue
        # Email or telephone labels remain available as working links.
        people.append({"name":texts[0],"role":texts[1] if len(texts)>1 else "","details":texts[2:],"image":img})
    # Deduplicate image/name pairs created by repeated Wix background layers.
    seen=set(); unique=[]
    for person in people:
        k=(person["name"],image_key(person["image"]))
        if k in seen: continue
        seen.add(k); unique.append(person)
    return unique

def detail_line(text):
    text=clean(text)
    email=re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}",text)
    phone=re.search(r"(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}",text)
    if email:
        before=text[:email.start()]; after=text[email.end():]
        return esc(before)+f'<a href="mailto:{esc(email.group())}">{esc(email.group())}</a>'+esc(after)
    if phone:
        digits=re.sub(r"\D","",phone.group())
        if len(digits)==10: digits="1"+digits
        return esc(text[:phone.start()])+f'<a href="tel:+{digits}">{esc(phone.group())}</a>'+esc(text[phone.end():])
    return esc(text)

def render_people(page):
    people=person_cards(page)
    hero=meaningful_images(page)[0] if meaningful_images(page) else None
    # The first unlabeled image may be a page cover; keep the people portraits in the card list only.
    cards=[]
    for person in people:
        details=''.join(f'<p>{detail_line(x)}</p>' for x in person["details"])
        cards.append(f'''<article class="person-card"><div class="person-card__photo">{image_tag(person['image'],"",loading="lazy",width=850)}</div><div class="person-card__content"><h2>{esc(person['name'])}</h2>{f'<p class="person-role">{esc(person["role"])}</p>' if person['role'] else ''}<div class="person-details">{details}</div></div></article>''')
    intro=page_hero(page,hero,lead=lead_text(page))
    team_tools='<div class="people-tools"><label for="people-search">Find a team member</label><input id="people-search" type="search" placeholder="Search by name or role" autocomplete="off"><p class="people-result-count" aria-live="polite"></p></div>' if page.get("slug")=="meet-our-team" else ""
    return f'''{breadcrumbs_html(page)}{intro}<div class="page-content"><div class="content-width">{team_tools}{f'<div class="people-grid">{"".join(cards)}</div>' if cards else render_blocks(page,skip_hero=hero)}</div></div>'''

def video_cards(page):
    blocks=page.get("blocks",[]); cards=[]; last_title=""
    seen=set()
    for b in blocks:
        if b.get("type")=="paragraph" and b.get("text"):
            text=b["text"]
            if "youtube.com/@" not in text and "WATCH VIDEO" not in text.upper(): last_title=text
        elif b.get("type")=="link" and any(host in b.get("href","") for host in ("youtube.com/watch", "youtu.be/")):
            href=b["href"]
            if href in seen: continue
            seen.add(href)
            title=last_title or b.get("text") or "Fleet Fisheries video"
            if title.startswith("www.youtube.com"): title=b.get("text") or "Fleet Fisheries video"
            parsed=urlparse(href); vid=parse_qs(parsed.query).get("v",[""])[0]
            if "youtu.be" in (parsed.netloc or ""): vid=parsed.path.strip("/").split("/")[0]
            if not vid: continue
            cards.append({"title":title,"href":href,"src":f"https://www.youtube-nocookie.com/embed/{esc(vid)}?rel=0"})
    out=[]
    for v in cards:
        out.append(f'''<article class="video-card"><div class="video-frame"><iframe src="{v['src']}" title="{esc(v['title'])}" loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe></div><div class="video-card__copy"><h3>{esc(v['title'])}</h3>{link_html('Watch on YouTube',v['href'],'text-link')}</div></article>''')
    return ''.join(out)

def render_contact(page):
    hero=meaningful_images(page)[0] if meaningful_images(page) else None
    close=next((b.get("text","") for b in page.get("blocks",[]) if b.get("type")=="paragraph" and "#1 priority" in b.get("text", "")),"")
    return f'''{breadcrumbs_html(page)}{page_hero(page,hero,lead="Get in touch with Fleet Fisheries Inc.")}<div class="page-content"><div class="content-width contact-layout"><section class="contact-details"><p class="eyebrow">Talk to our team</p><h2>Get in touch</h2><address>20 Blackmer Street<br>New Bedford, MA 02744</address><p><span class="contact-label">Phone</span><a href="tel:+15089963742">(508) 996-3742</a></p><p><span class="contact-label">Fax</span><span>(508) 996-3785</span></p><p><span class="contact-label">Sales</span><a href="mailto:sales@fleetfisheries.com">sales@fleetfisheries.com</a></p><p class="jobs-note">Looking for work on the fleet? <a href="/vessel-jobs/">Visit vessel jobs</a>.</p><div class="contact-map"><iframe title="Map to Fleet Fisheries at 20 Blackmer Street, New Bedford" loading="lazy" referrerpolicy="no-referrer-when-downgrade" src="https://maps.google.com/maps?q=20%20Blackmer%20Street%2C%20New%20Bedford%2C%20MA%2002744&t=&z=14&ie=UTF8&iwloc=&output=embed"></iframe></div></section>
      <section class="form-card"><p class="eyebrow">Send a message</p><h2>How can we help?</h2><form data-site-form="contact" novalidate><div class="form-row"><label>First name<input name="firstName" autocomplete="given-name" required></label><label>Last name<input name="lastName" autocomplete="family-name" required></label></div><label>Email<input type="email" name="email" autocomplete="email" required></label><label>Message<textarea name="message" rows="6" required></textarea></label><div class="form-honeypot" aria-hidden="true"><label>Company website<input name="companyWebsite" tabindex="-1" autocomplete="off"></label></div><button class="button button--dark" type="submit">Send message <span aria-hidden="true">→</span></button><p class="form-status" aria-live="polite" role="status"></p><p class="form-note">If direct delivery is unavailable, a prefilled email option will be shown.</p></form></section></div>{f'<div class="contact-close">{esc(close)}</div>' if close else ''}</div>'''

def render_jobs(page):
    hero=meaningful_images(page)[0] if meaningful_images(page) else None
    return f'''{breadcrumbs_html(page)}{page_hero(page,hero,lead="Think you’ve got what it takes to become a fisherman working on one of the Fleet Fisheries vessels? Apply here.")}<div class="page-content"><div class="content-width jobs-layout"><section class="jobs-intro"><p class="eyebrow">Vessel jobs</p><h2>Want to apply for a deckhand position?</h2><p>All of our captains hire their own fishing crews. We will do our best to print out your application and leave it for our boat captains.</p><p>All fishing vessels are managed by Fleet Management Group LLC.</p><address>20 Blackmer Street<br>New Bedford, MA 02744</address><a href="mailto:sales@fleetfisheries.com">sales@fleetfisheries.com</a></section><section class="form-card"><p class="eyebrow">Application</p><h2>Come work with us</h2><form data-site-form="crew-application" novalidate><div class="form-row"><label>First name<input name="firstName" autocomplete="given-name" required></label><label>Last name<input name="lastName" autocomplete="family-name" required></label></div><label>Email<input type="email" name="email" autocomplete="email" required></label><div class="form-row"><label>Phone number<input type="tel" name="phone" autocomplete="tel" required></label><label>Position of interest<input name="position" placeholder="e.g. Deckhand" required></label></div><label>Years of experience<input type="number" name="experience" min="0" max="70" step="1" placeholder="# of years"></label><label>Additional notes<textarea name="notes" rows="5" placeholder="Describe your experience or other pertinent details."></textarea></label><div class="form-honeypot" aria-hidden="true"><label>Company website<input name="companyWebsite" tabindex="-1" autocomplete="off"></label></div><button class="button button--dark" type="submit">Submit application <span aria-hidden="true">→</span></button><p class="form-status" aria-live="polite" role="status"></p><p class="form-note">If direct delivery is unavailable, a prefilled email option will be shown to contact Fleet Management Group LLC via sales@fleetfisheries.com.</p></form></section></div></div>'''

def render_credit(page):
    hero=meaningful_images(page)[0] if meaningful_images(page) else None
    return f'''{breadcrumbs_html(page)}{page_hero(page,hero,lead="Begin your journey with Fleet today.")}<div class="page-content"><div class="content-width document-panel"><div class="document-panel__mark" aria-hidden="true">PDF</div><div><p class="eyebrow">Credit application</p><h2>Download the application</h2><p>Complete the credit application and return it to Fleet Fisheries to begin the process.</p><a class="button button--dark" href="/assets/docs/credit-application.pdf" download>Download PDF <span aria-hidden="true">↓</span></a><p class="document-note">PDF · OceansFleet Fisheries Credit Application</p></div></div><div class="content-width related-links">{link_html("View shipping information","/shipping/","text-link")}{link_html("Contact Fleet Fisheries","/contact-us/","text-link")}</div></div>'''

def render_certifications(page):
    hero=meaningful_images(page)[0] if meaningful_images(page) else None
    body=render_blocks(page,skip_hero=hero,image_limit=2)
    documents='''<section class="documents-section"><div class="section-heading section-heading--compact"><p class="eyebrow">Documents</p><h2>Certificates &amp; scope</h2></div><div class="document-grid"><a class="document-card" href="/assets/docs/certification-scope-1.pdf" target="_blank"><span class="document-card__type">PDF</span><strong>HACCP Certificate of Compliance</strong><span>View certificate ↗</span></a><a class="document-card" href="/assets/docs/certification-scope-2.pdf" target="_blank"><span class="document-card__type">PDF</span><strong>MSC Scope &amp; Certification</strong><span>View scope ↗</span></a></div></section>'''
    return f'''{breadcrumbs_html(page)}{page_hero(page,hero,lead=lead_text(page))}<div class="page-content"><div class="content-width">{documents}{body}</div></div>'''

def render_directory(page):
    hero=meaningful_images(page)[0] if meaningful_images(page) else None
    body=render_blocks(page,skip_hero=hero)
    return f'''{breadcrumbs_html(page)}{page_hero(page,hero,lead=lead_text(page))}<div class="page-content"><div class="content-width directory-intro"><p class="eyebrow">Company directory</p><h2>Reach the right team</h2><p>Call (508) 996-3742 or email sales@fleetfisheries.com to speak with one of our seafood experts about placing wholesale seafood orders.</p>{body}</div></div>'''

def render_gallery(page):
    hero=meaningful_images(page)[0] if meaningful_images(page) else None
    vids=video_cards(page)
    images=meaningful_images(page)
    # Keep images from the source media page in a lightbox gallery, including its channel cover.
    grid=render_photo_group(images[1:] if images and images[0]==hero else images,"photo-grid photo-grid--gallery")
    return f'''{breadcrumbs_html(page)}{page_hero(page,hero,lead=lead_text(page))}<div class="page-content"><div class="content-width"><section class="video-section"><div class="section-heading section-heading--compact"><p class="eyebrow">Fleet Fisheries on YouTube</p><h2>Videos from the fleet</h2><p>Watch Fleet Fisheries videos and vessel features.</p></div><div class="video-card-grid">{vids or '<p>Visit the Fleet Fisheries YouTube channel for videos.</p>'}</div><a class="button button--dark" href="https://www.youtube.com/@fleetfisheriesinc" target="_blank" rel="noopener noreferrer">Visit our YouTube channel</a></section><section class="archive-section"><div class="section-heading section-heading--compact"><p class="eyebrow">Photos</p><h2>Fleet Fisheries photo gallery</h2></div>{grid}</section></div></div>'''

def render_company_news(page):
    hero=meaningful_images(page)[0] if meaningful_images(page) else None
    body=render_blocks(page,skip_hero=hero)
    return f'''{breadcrumbs_html(page)}{page_hero(page,hero,lead="Company news and stories from the Fleet Fisheries archive.")}<div class="page-content"><div class="content-width"><aside class="archive-note"><p class="eyebrow">Company archive</p><p>This page contains past company news and features. Dates and event timing are presented where included in the original article text.</p></aside><div class="company-news-content">{body}</div></div></div>'''

def render_stage(page):
    slug=page["slug"]
    hero=meaningful_images(page)[0] if meaningful_images(page) else None
    if slug=="to-the-shore":
        title="Quality & Sourcing"; lead="See how Fleet Fisheries handles seafood from catch through processing, traceability and delivery."
        links=[("Fleet facilities","fleet-facilities"),("Quality assurance","quality-assurance"),("Certifications","certifications"),("Traceability","traceability"),("Sustainability","sustainability"),("Best practices","best-practices")]
        kicker="Catch to customer"; intro="Fleet Fisheries connects its commercial fishing fleet with New Bedford shore operations and quality practices. Explore the facilities, standards and information behind that work."
    else:
        title="For Buyers"; lead="Wholesale seafood, shipping information and account resources from Fleet Fisheries."
        links=[("Explore seafood","our-products"),("Talk to Sales","sales"),("Shipping","shipping"),("Credit application","credit-application"),("Company directory","company-directory"),("Contact Fleet Fisheries","contact-us")]
        kicker="Wholesale buyer resources"; intro="Browse seafood, speak with the sales team about products and availability, then review shipping and account resources."
    title_html=esc(title)
    cards=[]
    for label,target in links:
        target_page=BY_SLUG.get(target,{})
        text=lead_text(target_page) if target_page else ""
        img=page_image(target) if target in BY_SLUG and meaningful_images(BY_SLUG[target]) else None
        photo=f'<div class="hub-card__image">{image_tag(img,"",loading="lazy",width=900)}</div>' if img else ''
        cards.append(f'<a class="hub-card" href="/{target}/">{photo}<div class="hub-card__copy"><p class="eyebrow">{esc(kicker)}</p><h2>{esc(label)}</h2><p>{esc(text)}</p><span class="arrow-link">Explore <span aria-hidden="true">↗</span></span></div></a>')
    body=render_blocks(page,skip_hero=hero)
    return f'''{breadcrumbs_html(page)}{page_hero(page,hero,lead=lead)}<div class="page-content"><div class="content-width hub-page"><section class="hub-intro"><p class="eyebrow">{esc(kicker)}</p><h2>{title_html}</h2><p>{esc(intro)}</p></section><div class="hub-grid">{"".join(cards)}</div><div class="stage-copy">{body}</div></div></div>'''

def render_site_map(page):
    groups=[]
    for group in NAV_GROUPS:
        links=[(group["label"],group["href"])] + group["links"]
        unique=[]; seen=set()
        for name,href in links:
            if href in seen: continue
            seen.add(href); unique.append(link_html(name,href,"sitemap-link"))
        groups.append(f'<section class="sitemap-group"><h2>{esc(group["label"])}</h2><div>{"".join(unique)}</div></section>')
    vessels=[p for p in PAGES if p["slug"].startswith("fv-")]
    vessel_links=''.join(link_html(short_title(p),p["path"],"sitemap-link") for p in vessels)
    other=[p for p in PAGES if p["slug"] and p["slug"] not in ROUTE_ALIASES and not p["slug"].startswith("fv-") and p["slug"] not in {x[1].split("#",1)[0].strip("/") for g in NAV_GROUPS for x in [(g["label"],g["href"])] + g["links"]}]
    other_links=''.join(link_html(short_title(p),p["path"],"sitemap-link") for p in other)
    hero=meaningful_images(page)[0] if meaningful_images(page) else None
    return f'''{breadcrumbs_html(page)}{page_hero(page,hero,lead="Browse Fleet Fisheries pages.")}<div class="page-content"><div class="content-width"><div class="sitemap-grid">{"".join(groups)}<section class="sitemap-group"><h2>Vessel profiles</h2><div>{vessel_links}</div></section><section class="sitemap-group"><h2>More pages</h2><div>{other_links}</div></section></div></div></div>'''

def page_body(page):
    slug=page["slug"]
    if slug=="": return home_html()
    if slug in ROUTE_ALIASES: return f'<section class="page-content"><div class="content-width"><h1>Page moved</h1><p>This page has moved. <a href="{esc(ROUTE_ALIASES[slug])}">Continue to {esc(short_title(BY_SLUG[ROUTE_ALIASES[slug].strip("/")]))}</a>.</p></div></section>'
    if slug=="our-fleet": return render_fleet()
    if slug=="list-of-all-fleet-vessels": return render_all_vessels()
    if slug.startswith("fv-"): return render_vessel(page)
    if slug in SEAFOOD_PAGE_COPY: return render_seafood_page(page)
    if slug in ("meet-our-team","sales"): return render_people(page)
    if slug=="contact-us": return render_contact(page)
    if slug=="vessel-jobs": return render_jobs(page)
    if slug=="credit-application": return render_credit(page)
    if slug=="certifications": return render_certifications(page)
    if slug=="company-directory": return render_directory(page)
    if slug=="multimedia-gallery": return render_gallery(page)
    if slug=="company-news": return render_company_news(page)
    if slug=="site-map": return render_site_map(page)
    if slug in ("to-the-shore","to-your-door"): return render_stage(page)
    if slug=="vendor-ach-data-aggregation-tool":
        return f'''{breadcrumbs_html(page)}{page_hero(page,None,lead="Vendor ACH Data Aggregation Tool")}<div class="page-content"><div class="content-width empty-page"><p class="eyebrow">Vendor information</p><h2>No public instructions are published here.</h2><p>For questions about vendor payments, contact Fleet Fisheries at <a href="mailto:info@fleetfisheries.com">info@fleetfisheries.com</a> or call <a href="tel:+15089963742">(508) 996-3742</a>.</p></div></div>'''
    if slug=="our-products":
        return render_products_page(page)
    image_limit={"quality-assurance":2,"shipping":4,"fleet-facilities":4,"health-wellness":3,"traceability":3,"best-practices":4,"sustainability":3,"our-story":4}.get(slug,6)
    return standard_page(page,image_limit=image_limit)

def render_products_page(page):
    hero=meaningful_images(page)[0] if meaningful_images(page) else None
    cards=[]
    for label,title,slug,copy in PRODUCTS:
        im=seafood_hero_image(BY_SLUG[slug])
        cards.append(f'<a class="market-card" href="/{slug}/"><div class="market-card__photo">{image_tag(im,"",loading="lazy",width=1100)}</div><div class="market-card__body"><span class="eyebrow">{esc(label)}</span><h2>{esc(title)}</h2><p>{esc(copy)}</p><span class="arrow-link">View seafood details <span aria-hidden="true">↗</span></span></div></a>')
    exact_intro=next((b.get("text","") for b in page.get("blocks",[]) if b.get("type")=="paragraph" and "your #1 source" in b.get("text","").lower()),"")
    source_tagline=next((b.get("text","") for b in page.get("blocks",[]) if b.get("type")=="paragraph" and "fresh, quality seafood" in b.get("text","").lower()),"Fresh, quality seafood direct from the source.")
    return f'''{breadcrumbs_html(page)}{page_hero(page,hero,lead=source_tagline)}<div class="page-content"><div class="content-width market-index">{f'<div class="market-index__intro"><p>{esc(exact_intro)}</p></div>' if exact_intro else ''}<div class="market-grid">{"".join(cards)}</div><section class="market-quality"><div><p class="eyebrow">Quality &amp; handling</p><h2>Seafood backed by our own fleet and shore operations.</h2><p>Learn about Fleet Fisheries' quality assurance, traceability, facilities and shipping.</p></div><div class="market-quality__links">{link_html("Quality assurance","/quality-assurance/","text-link")}{link_html("Traceability","/traceability/","text-link")}{link_html("Fleet facilities","/fleet-facilities/","text-link")}{link_html("Shipping","/shipping/","text-link")}</div></section><section class="product-cta"><p class="eyebrow">Wholesale seafood</p><h2>Talk with a Fleet Fisheries sales associate.</h2><p>Contact one of our sales associates to discuss products and wholesale orders.</p><div class="button-row">{link_html("Contact the sales team","/sales/","button button--dark")}<a class="button button--outline" href="tel:+15089963742">Call (508) 996-3742</a></div></section></div></div>'''

def seafood_hero_image(page):
    slug=page["slug"]
    match={
        "sea-scallops":lambda: page_image(slug,contains="scallops"),
        "lobster":lambda: page_image(slug,contains="live-lobster-in-hand"),
        "crab":lambda: page_image(slug,contains="naked-catch-crab"),
        "fish":lambda: page_image(slug,contains="swordfish-on-ice"),
    }
    image=match.get(slug,lambda:None)()
    return image or page_image(slug)

def seafood_gallery(slug, hero):
    label={"sea-scallops":"Sea scallops","lobster":"Lobster","crab":"Crab","fish":"Fish"}[slug]
    hero_key=image_key(hero) if hero else ""
    images=[]
    for key in SEAFOOD_GALLERIES.get(slug,[]):
        if key==hero_key: continue
        images.append({"key":key,"alt":label})
    return images

def render_seafood_page(page):
    slug=page["slug"]
    copy=SEAFOOD_PAGE_COPY[slug]
    hero=seafood_hero_image(page)
    lead=lead_text(page)
    gallery_images=seafood_gallery(slug,hero)
    gallery=render_image_grid(gallery_images[:8],"photo-grid photo-grid--seafood")
    if len(gallery_images)>8:
        gallery+=f'<details class="gallery-more"><summary>View all {len(gallery_images)} {esc(short_title(page).lower())} photos</summary>{render_image_grid(gallery_images[8:],"photo-grid photo-grid--seafood")}</details>'
    exact_scallop_line=""
    call_heading=next((b.get("text","") for b in page.get("blocks",[]) if b.get("type")=="heading" and "Call us today" in b.get("text","").lower()),"")
    if call_heading: exact_scallop_line=f'<p class="seafood-hero__note">{esc(call_heading)}</p>'
    product_links=[]
    for label,title,target,copy_text in PRODUCTS:
        if target==slug: continue
        product_links.append(link_html(title,f"/{target}/","seafood-switcher__link"))
    source_vessels=link_html(copy["fleet_label"],copy["fleet_href"],"button button--outline")
    quality_points=''.join(f'<li>{esc(text)}</li>' for text in copy["quality_points"])
    main_cta=link_html("Contact the sales team","/sales/","button button--dark")
    phone='<a class="button button--outline" href="tel:+15089963742">Call (508) 996-3742</a>'
    credit_heading=next((b.get("text","") for b in page.get("blocks",[]) if b.get("type")=="heading" and "Begin Your Journey" in b.get("text","")),"Begin Your Journey with Fleet Fisheries Today...")
    return f'''{breadcrumbs_html(page)}<section class="seafood-hero seafood-hero--{esc(slug)}"><div class="seafood-hero__media">{image_tag(hero,"seafood-hero__image",loading="eager",width=2200)}</div><div class="seafood-hero__shade"></div><div class="seafood-hero__content"><p class="eyebrow">From the sea · {esc(copy['eyebrow'])}</p><h1>{esc(short_title(page))}</h1><p class="seafood-hero__lead">{esc(lead)}</p>{exact_scallop_line}<div class="button-row">{main_cta}{phone}</div></div></section>
      <section class="seafood-story"><div class="content-width seafood-story__grid"><div class="seafood-story__copy"><p class="eyebrow">Quality &amp; sourcing</p><h2>{esc(copy['quality_heading'])}</h2><p>{esc(copy['quality_copy'])}</p>{source_vessels}</div><ul class="seafood-proof">{quality_points}</ul></div></section>
      <section class="seafood-gallery-section"><div class="content-width"><div class="seafood-section-heading"><p class="eyebrow">Fleet Fisheries · New Bedford, Massachusetts</p><h2>{esc(short_title(page))} from every angle.</h2><p>Product photographs from Fleet Fisheries.</p></div>{gallery}</div></section>
      <section class="seafood-switcher"><div class="content-width"><div><p class="eyebrow">Our products</p><h2>Explore more seafood.</h2></div><nav class="seafood-switcher__links" aria-label="More seafood products">{"".join(product_links)}</nav></div></section>
      <section class="seafood-wholesale"><div class="content-width"><div><p class="eyebrow">Wholesale seafood</p><h2>Ask about current products and availability.</h2><p>Speak with the Fleet Fisheries sales team about product details and wholesale orders.</p></div><div class="button-row">{link_html("Contact sales","/sales/","button button--light")}<a class="button button--outline" href="tel:+15089963742">Call (508) 996-3742</a></div></div></section>
      '''

def render_from_the_sea(page):
    hero=meaningful_images(page)[0] if meaningful_images(page) else None
    cards=[]
    for label,title,slug,copy in PRODUCTS:
        image=seafood_hero_image(BY_SLUG[slug])
        cards.append(f'<a class="market-card" href="/{slug}/"><div class="market-card__photo">{image_tag(image,"",loading="lazy",width=1000)}</div><div class="market-card__body"><span class="eyebrow">{esc(label)}</span><h2>{esc(title)}</h2><p>{esc(copy)}</p><span class="arrow-link">Explore product <span aria-hidden="true">↗</span></span></div></a>')
    stewardship=[]
    for slug,label,description in [("our-fleet","Our fleet","Take a look at our fleet of commercial fishing vessels."),("sustainability","Sustainability","We understand how important it is to keep our industry sustainable for generations to come."),("health-wellness","Health & wellness","Seafood is a healthy source of protein and nutrients."),("best-practices","Best practices","Fleet Fisheries works with agencies and industry groups to manage fisheries and protect ocean ecology.")]:
        stewardship.append(link_html(label,f"/{slug}/","seafood-switcher__link"))
    return f'''{breadcrumbs_html(page)}{page_hero(page,hero,lead="Explore seafood sourced by Fleet Fisheries and the fishing fleet behind it.")}<div class="page-content"><div class="content-width market-index"><div class="market-index__heading"><p class="eyebrow">From the sea</p><h2>Choose your seafood.</h2><p>Open a product page for its photos, sourcing information and quality details.</p></div><div class="market-grid">{"".join(cards)}</div><section class="seafood-switcher seafood-switcher--landing"><div><p class="eyebrow">More from the sea</p><h2>Fleet, stewardship and best practices.</h2></div><nav class="seafood-switcher__links" aria-label="More from the sea">{"".join(stewardship)}</nav></section></div></div>'''

def html_page(page):
    title=("Fleet Fisheries | Commercial Fishing & Wholesale Seafood" if not page.get("slug") else f"{short_title(page)} | Fleet Fisheries Inc.")
    description=page_description(page)[:300]
    canonical=BASE_URL+page.get("path","/")
    if page.get("slug") in ROUTE_ALIASES: canonical=BASE_URL+ROUTE_ALIASES[page["slug"]]
    robots_meta='<meta name="robots" content="noindex,follow">' if page.get("slug") in ROUTE_ALIASES else ''
    lead_image=meaningful_images(page)[0] if meaningful_images(page) else page_image("our-fleet")
    og=image_remote(lead_image,width=1200) if lead_image else ""
    schema={"@context":"https://schema.org","@graph":[
        {"@type":"Organization","name":"Fleet Fisheries Inc.","url":BASE_URL,"email":"info@fleetfisheries.com","telephone":"+1-508-996-3742","address":{"@type":"PostalAddress","streetAddress":"20 Blackmer Street","addressLocality":"New Bedford","addressRegion":"MA","postalCode":"02744","addressCountry":"US"}},
        {"@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"name":"Home","item":BASE_URL+"/"}]+([] if not page.get("slug") else [{"@type":"ListItem","position":2,"name":short_title(page),"item":canonical}])}
    ]}
    body=page_body(page)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="theme-color" content="#0c2733"><title>{esc(title)}</title><meta name="description" content="{esc(description)}">{robots_meta}<link rel="canonical" href="{esc(canonical)}"><meta property="og:type" content="website"><meta property="og:site_name" content="Fleet Fisheries Inc."><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{esc(canonical)}"><meta property="og:image" content="{esc(og)}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{esc(title)}"><meta name="twitter:description" content="{esc(description)}"><meta name="twitter:image" content="{esc(og)}"><link rel="icon" href="/assets/images/asset-0209.webp" type="image/webp"><link rel="stylesheet" href="/assets/css/site.css?v=ux-20261022"><script type="application/ld+json">{json.dumps(schema,ensure_ascii=False)}</script><script defer src="/assets/js/site.js?v=ux-20261022"></script></head>
<body data-page="{esc(page.get('slug',''))}">{header_html(page.get('slug',''))}<main id="main">{body}</main>{footer_html()}<dialog class="lightbox" data-lightbox-dialog aria-label="Image viewer"><button type="button" data-lightbox-close class="lightbox__close" aria-label="Close image">×</button><button type="button" data-lightbox-prev class="lightbox__arrow lightbox__arrow--prev" aria-label="Previous image">‹</button><figure><img data-lightbox-image alt=""><figcaption data-lightbox-caption></figcaption></figure><button type="button" data-lightbox-next class="lightbox__arrow lightbox__arrow--next" aria-label="Next image">›</button></dialog></body></html>'''

def generate():
    # Keep the checked-in source content and static routes in sync.
    for p in PAGES:
        dest=ROOT if not p["slug"] else ROOT/p["slug"]
        dest.mkdir(parents=True,exist_ok=True)
        (dest/"index.html").write_text(html_page(p),encoding="utf-8")
    search=[{"title":short_title(p),"path":p["path"],"description":page_description(p),"text":p.get("search_text","")} for p in PAGES if p.get("slug") not in ROUTE_ALIASES]
    (ROOT/"assets/data/search-index.json").write_text(json.dumps(search,ensure_ascii=False),encoding="utf-8")
    urls=[]
    for p in PAGES:
        if p.get("slug") in ROUTE_ALIASES: continue
        urls.append(f'<url><loc>{esc(BASE_URL+p["path"])}</loc><changefreq>monthly</changefreq></url>')
    sitemap='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(urls)+'</urlset>'
    (ROOT/"sitemap.xml").write_text(sitemap,encoding="utf-8")
    (ROOT/"robots.txt").write_text("User-agent: *\nAllow: /\nSitemap: https://www.fleetfisheries.com/sitemap.xml\n",encoding="utf-8")
    (ROOT/"404.html").write_text(f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Page not found | Fleet Fisheries</title><link rel="stylesheet" href="/assets/css/site.css?v=ux-20261022"></head><body>{header_html()}<main class="not-found"><p class="eyebrow">404 · Fleet Fisheries</p><h1>We can’t find that page.</h1><p>Return to the home page or browse the site map.</p><a class="button button--dark" href="/">Fleet Fisheries home</a> {link_html("Site map","/site-map/","text-link")}</main>{footer_html()}</body></html>''',encoding="utf-8")
    print(f"Rendered {len(PAGES)} static routes into {ROOT}")

if __name__=="__main__": generate()
