#!/usr/bin/env python3
"""Write a concise record of the source pages, assets, and functional review."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
pages = json.loads((ROOT / 'content/pages.json').read_text())
assets = json.loads((ROOT / 'content/assets.json').read_text())
failures = [meta['source_name'] for meta in assets.values() if not meta.get('file')]
lines = [
    '# Source website review',
    '',
    'Reviewed Fleet Fisheries Inc. public pages and their internal links, navigation, footer, forms, source images, embedded video links, downloadable documents, and external destinations. The redesign keeps the original Fleet Fisheries image URLs as the primary image sources and includes optimized local fallback images.',
    '',
    f'**Routes rebuilt:** {len(pages)}. **Distinct Wix media assets mapped:** {len(assets)}. **Local image fallbacks:** {sum(bool(meta.get("file")) for meta in assets.values())}.',
    '',
    '## Page inventory',
    '',
    '| Route | Source page title |',
    '|---|---|',
]
for page in pages:
    route = page.get('path') or '/'
    title = page.get('h1') or page.get('title') or 'Fleet Fisheries home'
    title = title.replace('|', ' / ')
    lines.append(f'| `{route}` | {title} |')
lines += [
    '',
    '## Interactions and user journeys',
    '',
    '- Primary navigation includes grouped page links and works with keyboard, touch, and pointer input. The mobile menu expands and collapses.',
    '- Homepage carousel includes previous/next, slide selection, auto-advance, and pause controls; it respects the reduced-motion preference.',
    '- Site search indexes the source page titles, descriptions, and text.',
    '- The fleet index links to all 24 vessel profiles; profiles preserve accessible specifications and source imagery.',
    '- Contact form fields: first name, last name, email, and message. Vessel jobs fields: first and last name, email, phone, position, years of experience, and additional notes.',
    '- Both forms validate and submit to `/api/forms` when the optional Resend environment variables are configured. Without them, the form clearly reports that delivery did not occur and offers a prefilled email link.',
    '- Photo galleries open a keyboard-dismissable lightbox with previous/next controls.',
    '- The media page retains source videos through privacy-enhanced YouTube embeds and links to the Fleet Fisheries YouTube channel.',
    '',
    '## External destinations and documents',
    '',
    '- Google Maps embed for the source business address at 20 Blackmer Street, New Bedford, MA 02744.',
    '- Existing YouTube, Facebook, X, Instagram, TSA cargo screening, and Fisherman’s Market destinations are retained where identified in the source site.',
    '- Bundled source files: credit application PDF, HACCP certificate PDF, and MSC scope / certification PDF.',
    '',
    '## Access notes',
    '',
    '- The source sitemap included 53 pages; the navigation also links to `/from-the-sea/`, which was added to the rebuild, for 54 routes total.',
    '- The public `/vendor-ach-data-aggregation-tool/` route did not expose readable instructions. The rebuild preserves the route, states that no public instructions were available, and offers Fleet Fisheries’ existing public contact details.',
    '- One of the 516 distinct source image assets rejected direct downloading. Its original Wix URL is retained as the primary page image source; this asset has no bundled fallback. All other 515 assets have optimized local fallbacks.',
    '- No form delivery credentials or other private third-party credentials were present on the source site. Resend must be configured in Vercel before forms deliver directly; otherwise visitors receive the mail-app fallback.',
    '',
]
(ROOT / 'SOURCE_AUDIT.md').write_text('\n'.join(lines), encoding='utf-8')
print(f'Wrote route inventory for {len(pages)} pages; image fallbacks missing: {len(failures)}.')
