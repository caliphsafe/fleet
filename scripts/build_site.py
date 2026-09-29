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
BY_SLUG = {p["slug"]: p for p in PAGES}
BASE_URL = "https://www.fleetfisheries.com"

NAV_GROUPS = [
    {
        "label": "From the Sea", "href": "/from-the-sea/", "lead": "Seafood, fleet and stewardship",
        "links": [
            ("Our Fleet", "/our-fleet/"), ("Sea Scallops", "/sea-scallops/"),
            ("Lobster", "/lobster/"), ("Crab", "/crab/"), ("Wholefish & Fillets", "/fish/"),
            ("Best Practices", "/best-practices/"), ("Health & Wellness", "/health-wellness/"),
            ("Sustainability", "/sustainability/"),
        ],
    },
    {
        "label": "Our Fleet", "href": "/our-fleet/", "lead": "Fishing vessels and crew opportunities",
        "links": [("See All Vessels", "/our-fleet/"), ("Vessel List", "/list-of-all-fleet-vessels/"), ("Vessel Jobs", "/vessel-jobs/")],
    },
    {
        "label": "To the Shore", "href": "/to-the-shore/", "lead": "Facilities, quality and traceability",
        "links": [("Fleet Facilities", "/fleet-facilities/"), ("Certifications", "/certifications/"), ("Quality Assurance", "/quality-assurance/"), ("Traceability", "/traceability/")],
    },
    {
        "label": "To Your Door", "href": "/to-your-door/", "lead": "Products, shipping and customer accounts",
        "links": [("Our Products", "/our-products/"), ("Shipping", "/shipping/"), ("Credit Application", "/credit-application/"), ("Fisherman's Market", "https://www.fishmanmkt.com/")],
    },
    {
        "label": "About", "href": "/our-story/", "lead": "People, company news and contact details",
        "links": [("Our Story", "/our-story/"), ("Meet Our Team", "/meet-our-team/"), ("Fleet Sales Team", "/sales/"), ("Company Directory", "/company-directory/"), ("Fleet News", "/company-news/"), ("Media Gallery", "/multimedia-gallery/"), ("Contact Us", "/contact-us/")],
    },
]

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

def esc(value):
    return html.escape(str(value or ""), quote=True)

def clean(value):
    return " ".join(str(value or "").replace("\u200b", "").split())

def image_key(image):
    return image.get("key", "")

def image_remote(image, width=1500):
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
    return page.get("description") or lead_text(page) or f"Fleet Fisheries Inc. — {short_title(page)}."

def header_html(active_slug=""):
    logo_key="e54456_76784bf0d07a4b919d1e043ec5f5af70~mv2.png"
    logo={"key":logo_key,"src":"https://static.wixstatic.com/media/"+quote(logo_key,safe="~._-"),"fallback":ASSETS.get(logo_key,{}).get("file", ""),"alt":"Fleet Fisheries Inc."}
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
      <div class="utility-bar"><div class="utility-bar__inner"><span>Over 30 years in business</span><span class="utility-bar__address">20 Blackmer Street · New Bedford, MA 02744</span><div class="utility-bar__actions"><a href="tel:+15089963742">Call (508) 996-3742</a><span>Fax (508) 996-3785</span><a href="mailto:info@fleetfisheries.com">Email Fleet Fisheries</a></div></div></div>
      <header class="site-header"><div class="site-header__inner">
        <a class="brand" href="/" aria-label="Fleet Fisheries home">{logo_img}</a>
        <button class="menu-toggle" type="button" aria-expanded="false" aria-controls="primary-nav" data-menu-toggle><span></span><span></span><span></span><span class="sr-only">Open navigation</span></button>
        <nav class="primary-nav" id="primary-nav" aria-label="Primary navigation">
          <a class="nav-home" href="/">Home</a>{''.join(groups)}
          <a class="nav-contact" href="/contact-us/">Contact <span aria-hidden="true">↗</span></a>
          <div class="nav-search"><label class="sr-only" for="site-search">Search Fleet Fisheries</label><input id="site-search" type="search" placeholder="Search" autocomplete="off" aria-controls="search-results" aria-expanded="false"><div id="search-results" class="search-results" role="listbox" hidden></div></div>
        </nav>
      </div></header>'''

def footer_html():
    quick1=''.join(link_html(label,href,'footer-link') for label,href in [("Our Fleet","/our-fleet/"),("Vessel List","/list-of-all-fleet-vessels/"),("Vessel Jobs","/vessel-jobs/"),("Our Products","/our-products/"),("Shipping","/shipping/")])
    quick2=''.join(link_html(label,href,'footer-link') for label,href in [("Fleet Facilities","/fleet-facilities/"),("Certifications","/certifications/"),("Quality Assurance","/quality-assurance/"),("Traceability","/traceability/"),("Sustainability","/sustainability/")])
    quick3=''.join(link_html(label,href,'footer-link') for label,href in [("Our Story","/our-story/"),("Meet Our Team","/meet-our-team/"),("Company Directory","/company-directory/"),("Fleet News","/company-news/"),("Contact Us","/contact-us/"),("Site Map","/site-map/")])
    socials=[("YouTube","https://www.youtube.com/channel/UCdHBCTiyboBVrBAjgt7dXdg"),("Facebook","https://www.facebook.com/oceansfleet/"),("X","https://twitter.com/fleetfisheries"),("Instagram","https://www.instagram.com/fleetfisheriesinc/")]
    social_html=''.join(link_html(label,href,'social-link') for label,href in socials)
    return f'''<footer class="site-footer"><div class="footer-main"><div class="footer-brand"><a href="/" class="footer-logo">Fleet Fisheries<span>INC.</span></a><p>From the sea, to the shore, to your door.<br>Sourced by our own fishing fleet.</p><p class="footer-address">20 Blackmer Street<br>New Bedford, MA 02744</p><a class="footer-phone" href="tel:+15089963742">(508) 996-3742</a><a class="footer-email" href="mailto:sales@fleetfisheries.com">sales@fleetfisheries.com</a></div><div class="footer-column"><h2>Seafood & fleet</h2>{quick1}</div><div class="footer-column"><h2>Quality & operations</h2>{quick2}</div><div class="footer-column"><h2>About Fleet</h2>{quick3}</div></div><div class="footer-bottom"><span>Fleet Fisheries Inc. · New Bedford, Massachusetts</span><div class="footer-socials" aria-label="Social media">{social_html}</div><span>© <span data-current-year>2026</span> Fleet Fisheries Inc.</span></div></footer>'''

def breadcrumbs_html(page):
    if not page.get("slug"): return ""
    label=short_title(page)
    return f'<nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/">Home</a><span aria-hidden="true">/</span><span aria-current="page">{esc(label)}</span></nav>'

def page_hero(page, image=None, class_name="page-hero", lead=None):
    title=short_title(page)
    image=image or (meaningful_images(page)[0] if meaningful_images(page) else None)
    media=(f'<div class="page-hero__media">{image_tag(image,"page-hero__image",loading="eager",width=1800)}</div>' if image and image.get("src") else '<div class="page-hero__media page-hero__media--abstract" aria-hidden="true"></div>')
    title_slug=page.get("slug","")
    group="Our Fleet" if title_slug.startswith("fv-") or title_slug in ("our-fleet","list-of-all-fleet-vessels","vessel-jobs") else "From the Sea" if title_slug in ("from-the-sea","sea-scallops","lobster","crab","fish","best-practices","health-wellness","sustainability") else "To the Shore" if title_slug in ("to-the-shore","certifications","fleet-facilities","quality-assurance","traceability") else "To Your Door" if title_slug in ("to-your-door","our-products","shipping","credit-application") else "Fleet Fisheries"
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

def render_blocks(page, skip_hero=None, skip_lead=True, skip_first_heading=True):
    blocks=page.get("blocks",[])
    first_heading=True; first_para=skip_lead; hero_key=image_key(skip_hero) if skip_hero else ""
    output=[]; image_buffer=[]
    def flush_images():
        nonlocal image_buffer
        if image_buffer:
            output.append(render_photo_group(image_buffer))
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
    return ''.join(output)

def standard_page(page, extra="", hero=None, lead=None, after_intro=""):
    hero=hero or (meaningful_images(page)[0] if meaningful_images(page) else None)
    lead=lead if lead is not None else lead_text(page)
    intro=page_hero(page,hero,lead=lead)
    body=render_blocks(page,skip_hero=hero)
    return f'{breadcrumbs_html(page)}{intro}<div class="page-content"><div class="content-width">{after_intro}{extra}{body}</div></div>'

def home_html():
    home=BY_SLUG.get("")
    h=home.get("images",[]) if home else []
    slides=[
        ("From the Sea", "Fresh seafood from the sea, to the shore, to your door. Sourced by our own fishing fleet.", "/from-the-sea/", h[0] if h else page_image("our-fleet")),
        ("Our Products", "Fresh, quality seafood direct from the source.", "/our-products/", page_image("our-products")),
        ("To the Shore", "Our strategically located New Bedford facilities support efficiency and quality.", "/to-the-shore/", page_image("fleet-facilities")),
        ("Sea Scallops", "Fresh scallops direct from our own fleet.", "/sea-scallops/", page_image("sea-scallops")),
        ("To Your Door", "From the sea to the shore to your door is what we do best.", "/to-your-door/", page_image("shipping")),
        ("Live Lobsters & Crabs", "North American lobster and crab.", "/lobster/", page_image("lobster")),
        ("Fish Department", "Swordfish, tuna, halibut and more.", "/fish/", page_image("fish")),
        ("New Bedford", "20 Blackmer Street, New Bedford, Massachusetts.", "/contact-us/", page_image("fleet-facilities")),
        ("Sustainability", "We understand how important it is to keep our industry sustainable for generations to come.", "/sustainability/", page_image("sustainability")),
    ]
    slide_html=[]
    for i,(title,desc,href,img) in enumerate(slides):
        slide_html.append(f'''<article class="hero-slide{' is-active' if i==0 else ''}" data-slide="{i}" aria-hidden="{'false' if i==0 else 'true'}">
          <div class="hero-slide__image">{image_tag(img,"hero-slide__photo",loading="eager" if i==0 else "lazy",width=2000)}</div>
          <div class="hero-slide__veil"></div><div class="hero-slide__content"><p class="eyebrow">Fleet Fisheries Inc. · New Bedford, MA</p><h1>{esc(title)}</h1><p class="hero-slide__copy">{esc(desc)}</p><div class="hero-slide__actions">{link_html("Explore "+title,href,"button button--light")}<a class="hero-phone" href="tel:+15089963742">Call (508) 996-3742</a></div></div>
        </article>''')
    dots=''.join(f'<button type="button" data-slide-to="{i}" aria-label="Show {esc(title)} slide" aria-current="{"true" if i==0 else "false"}"></button>' for i,(title,_,__,___) in enumerate(slides))
    hero=f'''<section class="home-hero" aria-roledescription="carousel" aria-label="Fleet Fisheries introduction"><div class="home-hero__slides">{"".join(slide_html)}</div><div class="home-hero__controls"><button type="button" data-slide-prev aria-label="Previous slide">←</button><div class="hero-dots">{dots}</div><button type="button" data-slide-next aria-label="Next slide">→</button><button type="button" class="hero-pause" data-slide-pause aria-label="Pause slideshow">Ⅱ</button></div><a class="hero-scroll" href="#journey">Scroll to explore <span aria-hidden="true">↓</span></a></section>'''
    step_cards=[
        ("01", "From the sea", "Our own fishing fleet harvests scallops, lobster, crab, and fish.", "/from-the-sea/", page_image("our-fleet")),
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
    lead=lead_text(page)
    cards=current_fleet_cards()
    groups=[]
    for category in ["Fleet Scallop Vessels","Fleet Lobster & Crab Vessels"]:
        section=[c for c in cards if c["group"]==category]
        if not section: continue
        card_html=[]
        for c in section:
            cta=link_html("View vessel profile",c["href"],"arrow-link") if c["href"] else '<span class="eyebrow">Vessel information</span>'
            card_html.append(f'''<article class="vessel-card"><div class="vessel-card__photo">{image_tag(c['image'],"",loading="lazy",width=1000)}</div><div class="vessel-card__body"><span class="eyebrow">{esc(category.replace('Fleet ',''))}</span><h3>{esc(c['name'])}</h3><p>{esc(c['description'])}</p>{cta}</div></article>''')
        groups.append(f'<section class="fleet-category"><div class="section-heading section-heading--compact"><p class="eyebrow">{esc(category)}</p><h2>{esc(category)}</h2></div><div class="vessel-grid">{"".join(card_html)}</div></section>')
    videos=video_cards(page)
    legacy=[]; after=False
    for b in page.get("blocks",[]):
        if b.get("type")=="heading" and "MISCELLANEOUS" in b.get("text",""): after=True
        elif b.get("type")=="image" and after: legacy.append(b)
    legacy_html=render_photo_group(legacy,"photo-grid photo-grid--archive")
    return f'''{breadcrumbs_html(page)}{page_hero(page,meaningful_images(page)[0] if meaningful_images(page) else None,lead=lead)}
      <div class="page-content"><div class="content-width"><div class="fleet-intro">{paragraph_html({'text':'See our modern fleet of commercial fishing vessels.'},'body-copy body-copy--large')}{link_html('View all vessel profiles','/list-of-all-fleet-vessels/','button button--dark')}</div>{''.join(groups)}
        <section class="video-section"><div class="section-heading section-heading--compact"><p class="eyebrow">On the water</p><h2>Fleet Fisheries videos</h2></div><div class="video-card-grid">{videos}</div></section>
        <section class="archive-section"><div class="section-heading section-heading--compact"><p class="eyebrow">Fleet history</p><h2>From the archives</h2></div>{legacy_html}{link_html('See all vessel profiles','/list-of-all-fleet-vessels/','button button--outline')}</section>
      </div></div>'''

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
    images=meaningful_images(page)
    return title,subtitle,spec,registry,images

def render_vessel(page):
    title,subtitle,spec,registry,images=vessel_data(page)
    hero=images[0] if images else None
    gallery=render_photo_group(images[1:],"photo-grid photo-grid--vessel")
    spec_html=''.join(f'<div class="spec-item"><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>' for k,v in spec.items())
    identity=f'<div class="vessel-id"><span>Vessel ID</span><strong>{esc(registry)}</strong></div>' if registry else ''
    other=[p for p in PAGES if p["slug"].startswith("fv-") and p["slug"]!=page["slug"]]
    other_cards=[]
    for item in other[:4]:
        im=meaningful_images(item)[0] if meaningful_images(item) else None
        other_cards.append(f'<a class="mini-vessel" href="{esc(item["path"])}"><div>{image_tag(im,"",loading="lazy",width=600) if im else ""}</div><span>{esc(short_title(item))}</span></a>')
    body=render_blocks(page,skip_hero=hero,skip_lead=False)
    return f'''{breadcrumbs_html(page)}{page_hero(page,hero,lead=subtitle or lead_text(page))}<div class="vessel-overview"><div class="content-width"><div class="vessel-overview__top"><div><p class="eyebrow">Fleet vessel profile</p><h2>{esc(title)}</h2></div>{identity}</div>{f'<dl class="spec-grid">{spec_html}</dl>' if spec_html else ''}</div></div><div class="page-content"><div class="content-width">{body}{'<section class="archive-section"><div class="section-heading section-heading--compact"><p class="eyebrow">Explore more</p><h2>Other vessel profiles</h2></div><div class="mini-vessel-grid">'+''.join(other_cards)+'</div></section>' if other_cards else ''}</div></div>'''

def render_all_vessels():
    page=BY_SLUG["list-of-all-fleet-vessels"]
    vessels=[p for p in PAGES if p["slug"].startswith("fv-")]
    scallop=[]; shellfish=[]
    for p in vessels:
        if "lobster" in p.get("title","").lower() or "crab" in p.get("title","").lower(): shellfish.append(p)
        else: scallop.append(p)
    def cards(items):
        out=[]
        for p in items:
            image=meaningful_images(p)[0] if meaningful_images(p) else None
            out.append(f'<a class="vessel-card vessel-card--link" href="{esc(p["path"])}"><div class="vessel-card__photo">{image_tag(image,"",loading="lazy",width=900) if image else ""}</div><div class="vessel-card__body"><span class="eyebrow">{esc("Lobster & crab" if p in shellfish else "Scallop vessel")}</span><h3>{esc(short_title(p))}</h3><span class="arrow-link">Vessel profile <span aria-hidden="true">↗</span></span></div></a>')
        return ''.join(out)
    return f'''{breadcrumbs_html(page)}{page_hero(page,meaningful_images(page)[0] if meaningful_images(page) else None,lead=lead_text(page))}<div class="page-content"><div class="content-width"><section class="fleet-category"><div class="section-heading section-heading--compact"><p class="eyebrow">Scallop vessels</p><h2>Scallop vessel profiles</h2></div><div class="vessel-grid">{cards(scallop)}</div></section><section class="fleet-category"><div class="section-heading section-heading--compact"><p class="eyebrow">Lobster &amp; crab</p><h2>Lobster and crab vessel profiles</h2></div><div class="vessel-grid">{cards(shellfish)}</div></section></div></div>'''

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
    return f'''{breadcrumbs_html(page)}{intro}<div class="page-content"><div class="content-width">{f'<div class="people-grid">{"".join(cards)}</div>' if cards else render_blocks(page,skip_hero=hero)}</div></div>'''

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
    body=render_blocks(page,skip_hero=hero)
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

def render_stage(page):
    slug=page["slug"]
    hero=meaningful_images(page)[0] if meaningful_images(page) else None
    title=short_title(page)
    blocks=page.get("blocks",[])
    cards=[]
    for i,b in enumerate(blocks):
        if b.get("type")!="link" or not b.get("href","").startswith("/"): continue
        if b.get("href").strip("/") in ("from-the-sea","to-the-shore","to-your-door"): continue
        text=b.get("text","")
        if text.upper() in ("WATCH VIDEO","APPLY NOW"): continue
        img=None; copy=""
        for previous in reversed(blocks[max(0,i-5):i]):
            if previous.get("type")=="image" and not is_decorative(previous): img=previous; break
        for following in blocks[i+1:i+4]:
            if following.get("type")=="paragraph": copy=following.get("text",""); break
        if not copy:
            target=b.get("href","").strip("/")
            copy=lead_text(BY_SLUG[target]) if target in BY_SLUG else ""
        if not img:
            target=b.get("href","").strip("/")
            img=page_image(target) if target in BY_SLUG else page_image(slug)
        if not any(c["href"]==b["href"] for c in cards): cards.append({"title":text,"href":b["href"],"image":img,"copy":copy})
    card_html=''.join(f'<a class="journey-card" href="{esc(c["href"])}"><div class="journey-card__photo">{image_tag(c["image"],"",loading="lazy",width=1000)}</div><div class="journey-card__copy"><span class="eyebrow">{esc(title)}</span><h3>{esc(c["title"].title())}</h3><p>{esc(c["copy"])}</p><span class="arrow-link">Explore <span aria-hidden="true">↗</span></span></div></a>' for c in cards)
    body=render_blocks(page,skip_hero=hero)
    return f'''{breadcrumbs_html(page)}{page_hero(page,hero,lead=lead_text(page))}<div class="page-content"><div class="content-width">{f'<div class="journey-grid">{card_html}</div>' if cards else ''}<div class="stage-copy">{body}</div></div></div>'''

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
    other=[p for p in PAGES if p["slug"] and not p["slug"].startswith("fv-") and p["slug"] not in {x[1].strip("/") for g in NAV_GROUPS for x in [(g["label"],g["href"])] + g["links"]}]
    other_links=''.join(link_html(short_title(p),p["path"],"sitemap-link") for p in other)
    hero=meaningful_images(page)[0] if meaningful_images(page) else None
    return f'''{breadcrumbs_html(page)}{page_hero(page,hero,lead="Browse Fleet Fisheries pages.")}<div class="page-content"><div class="content-width"><div class="sitemap-grid">{"".join(groups)}<section class="sitemap-group"><h2>Vessel profiles</h2><div>{vessel_links}</div></section><section class="sitemap-group"><h2>More pages</h2><div>{other_links}</div></section></div></div></div>'''

def page_body(page):
    slug=page["slug"]
    if slug=="": return home_html()
    if slug=="our-fleet": return render_fleet()
    if slug=="list-of-all-fleet-vessels": return render_all_vessels()
    if slug.startswith("fv-"): return render_vessel(page)
    if slug in ("meet-our-team","sales"): return render_people(page)
    if slug=="contact-us": return render_contact(page)
    if slug=="vessel-jobs": return render_jobs(page)
    if slug=="credit-application": return render_credit(page)
    if slug=="certifications": return render_certifications(page)
    if slug=="company-directory": return render_directory(page)
    if slug=="multimedia-gallery": return render_gallery(page)
    if slug=="site-map": return render_site_map(page)
    if slug in ("from-the-sea","to-the-shore","to-your-door"): return render_stage(page)
    if slug=="vendor-ach-data-aggregation-tool":
        return f'''{breadcrumbs_html(page)}{page_hero(page,None,lead="Vendor ACH Data Aggregation Tool")}<div class="page-content"><div class="content-width empty-page"><p class="eyebrow">Vendor information</p><h2>No public instructions are published here.</h2><p>For questions about vendor payments, contact Fleet Fisheries at <a href="mailto:info@fleetfisheries.com">info@fleetfisheries.com</a> or call <a href="tel:+15089963742">(508) 996-3742</a>.</p></div></div>'''
    if slug=="our-products":
        return render_products_page(page)
    return standard_page(page)

def render_products_page(page):
    hero=meaningful_images(page)[0] if meaningful_images(page) else None
    source_imgs=page.get("images",[])
    cards=[]
    for label,title,slug,copy in PRODUCTS:
        im=next((x for x in source_imgs if label.lower().split()[0] in (x.get("alt","")+" "+x.get("src","")).lower()),page_image(slug))
        cards.append(f'<a class="product-card" href="/{slug}/"><div class="product-card__photo">{image_tag(im,"",loading="lazy",width=950)}</div><div class="product-card__body"><span class="eyebrow">{esc(label)}</span><h2>{esc(title)}</h2><p>{esc(copy)}</p><span class="arrow-link">Explore <span aria-hidden="true">↗</span></span></div></a>')
    body=render_blocks(page,skip_hero=hero)
    return f'''{breadcrumbs_html(page)}{page_hero(page,hero,lead=lead_text(page))}<div class="page-content"><div class="content-width"><div class="product-grid">{"".join(cards)}</div>{body}<section class="product-cta"><p class="eyebrow">Wholesale seafood</p><h2>Talk with a Fleet Fisheries sales associate.</h2><p>Contact one of our seafood experts about placing wholesale seafood orders.</p>{link_html("Contact the sales team","/sales/","button button--dark")}</section></div></div>'''

def html_page(page):
    title=page.get("title") or short_title(page)
    description=page_description(page)[:300]
    canonical=BASE_URL+page.get("path","/")
    lead_image=meaningful_images(page)[0] if meaningful_images(page) else page_image("our-fleet")
    og=image_remote(lead_image,width=1200) if lead_image else ""
    schema={"@context":"https://schema.org","@graph":[
        {"@type":"Organization","name":"Fleet Fisheries Inc.","url":BASE_URL,"email":"info@fleetfisheries.com","telephone":"+1-508-996-3742","address":{"@type":"PostalAddress","streetAddress":"20 Blackmer Street","addressLocality":"New Bedford","addressRegion":"MA","postalCode":"02744","addressCountry":"US"}},
        {"@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"name":"Home","item":BASE_URL+"/"}]+([] if not page.get("slug") else [{"@type":"ListItem","position":2,"name":short_title(page),"item":canonical}])}
    ]}
    body=page_body(page)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="theme-color" content="#0c2733"><title>{esc(title)}</title><meta name="description" content="{esc(description)}"><link rel="canonical" href="{esc(canonical)}"><meta property="og:type" content="website"><meta property="og:site_name" content="Fleet Fisheries Inc."><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{esc(canonical)}"><meta property="og:image" content="{esc(og)}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{esc(title)}"><meta name="twitter:description" content="{esc(description)}"><meta name="twitter:image" content="{esc(og)}"><link rel="icon" href="/assets/images/asset-0209.webp" type="image/webp"><link rel="stylesheet" href="/assets/css/site.css"><script type="application/ld+json">{json.dumps(schema,ensure_ascii=False)}</script><script defer src="/assets/js/site.js"></script></head>
<body data-page="{esc(page.get('slug',''))}">{header_html(page.get('slug',''))}<main id="main">{body}</main>{footer_html()}<dialog class="lightbox" data-lightbox-dialog aria-label="Image viewer"><button type="button" data-lightbox-close class="lightbox__close" aria-label="Close image">×</button><button type="button" data-lightbox-prev class="lightbox__arrow lightbox__arrow--prev" aria-label="Previous image">‹</button><figure><img data-lightbox-image alt=""><figcaption data-lightbox-caption></figcaption></figure><button type="button" data-lightbox-next class="lightbox__arrow lightbox__arrow--next" aria-label="Next image">›</button></dialog></body></html>'''

def generate():
    # Keep the checked-in source content and static routes in sync.
    for p in PAGES:
        dest=ROOT if not p["slug"] else ROOT/p["slug"]
        dest.mkdir(parents=True,exist_ok=True)
        (dest/"index.html").write_text(html_page(p),encoding="utf-8")
    search=[{"title":short_title(p),"path":p["path"],"description":page_description(p),"text":p.get("search_text","")} for p in PAGES]
    (ROOT/"assets/data/search-index.json").write_text(json.dumps(search,ensure_ascii=False),encoding="utf-8")
    urls=[]
    for p in PAGES:
        urls.append(f'<url><loc>{esc(BASE_URL+p["path"])}</loc><changefreq>monthly</changefreq></url>')
    sitemap='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(urls)+'</urlset>'
    (ROOT/"sitemap.xml").write_text(sitemap,encoding="utf-8")
    (ROOT/"robots.txt").write_text("User-agent: *\nAllow: /\nSitemap: https://www.fleetfisheries.com/sitemap.xml\n",encoding="utf-8")
    (ROOT/"404.html").write_text(f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Page not found | Fleet Fisheries</title><link rel="stylesheet" href="/assets/css/site.css"></head><body>{header_html()}<main class="not-found"><p class="eyebrow">404 · Fleet Fisheries</p><h1>We can’t find that page.</h1><p>Return to the home page or browse the site map.</p><a class="button button--dark" href="/">Fleet Fisheries home</a> {link_html("Site map","/site-map/","text-link")}</main>{footer_html()}</body></html>''',encoding="utf-8")
    print(f"Rendered {len(PAGES)} static routes into {ROOT}")

if __name__=="__main__": generate()
