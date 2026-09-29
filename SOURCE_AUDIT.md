# Source website review

Reviewed Fleet Fisheries Inc. public pages and their internal links, navigation, footer, forms, source images, embedded video links, downloadable documents, and external destinations. The redesign keeps the original Fleet Fisheries image URLs as the primary image sources and includes optimized local fallback images.

**Routes rebuilt:** 54. **Distinct Wix media assets mapped:** 516. **Local image fallbacks:** 515.

## Page inventory

| Route | Source page title |
|---|---|
| `/` | Fleet Fisheries Inc.  /  Wholesale Scallops, Lobster, Crab, Fish & Other Seafood Distributor - New Bedford, MA |
| `/best-practices/` | BEST PRACTICES |
| `/certifications/` | CERTIFICATIONS |
| `/company-directory/` | COMPANY DIRECTORY |
| `/company-news/` | FLEET NEWS |
| `/contact-us/` | CONTACT US |
| `/crab/` | CRAB |
| `/credit-application/` | CREDIT APPLICATION |
| `/fish/` | WHOLEFISH & FILLETS |
| `/fleet-facilities/` | FLEET FACILITIES |
| `/from-the-sea/` | From The Sea  /  Fleet Fisheries Inc. |
| `/fv-american-eagle/` | F/V AMERICAN EAGLE |
| `/fv-american-viking/` | F/V AMERICAN VIKING |
| `/fv-christian-and-alexa/` | F/V Christian & Alexa - Scallop Vessel  /  Fleet Fisheries Inc. |
| `/fv-eagle/` | F/V EAGLE |
| `/fv-explorer/` | F/V EXPLORER |
| `/fv-freedom/` | F/V FREEDOM |
| `/fv-growler/` | F/V GROWLER |
| `/fv-hedy-brenna/` | F/V Hedy Brenna - Lobster & Crab Vessel  /  Fleet Fisheries Inc. |
| `/fv-liberty/` | F/V LIBERTY |
| `/fv-miss-ella/` | F/V MISS ELLA |
| `/fv-miss-freya/` | F/V MISS FREYA |
| `/fv-ocean-cat/` | F/V Ocean Cat - Scallop Vessel  /  Fleet Fisheries Inc. |
| `/fv-ocean-fox/` | F/V Ocean Fox - Scallop Vessel  /  Fleet Fisheries Inc. |
| `/fv-ocean-hunter/` | F/V Ocean Hunter - Scallop Vessel  /  Fleet Fisheries Inc. |
| `/fv-ocean-leader/` | F/V Ocean Leader - Scallop Vessel  /  Fleet Fisheries Inc. |
| `/fv-ocean-prowler/` | F/V Ocean Prowler - Scallop Vessel  /  Fleet Fisheries Inc. |
| `/fv-ocean-scout/` | F/V OCEAN SCOUT |
| `/fv-pacer/` | F/V Pacer - Scallop Vessel  /  Fleet Fisheries Inc. |
| `/fv-revolution/` | F/V REVOLUTION |
| `/fv-seawolf/` | F/V SEAWOLF |
| `/fv-terri-ann/` | F/V TERRI ANN |
| `/fv-viking-power/` | F/V VIKING POWER |
| `/fv-vindicator/` | F/V VINDICATOR |
| `/fv-william-bowe/` | F/V William Bowe - Lobster & Crab Vessel  /  Fleet Fisheries Inc. |
| `/health-wellness/` | HEALTH & WELLNESS |
| `/list-of-all-fleet-vessels/` | OUR FLEET |
| `/lobster/` | LOBSTER |
| `/meet-our-team/` | MEET TEAM FLEET |
| `/multimedia-gallery/` | MEDIA GALLERY |
| `/our-fleet/` | OUR FLEET |
| `/our-products/` | OUR PRODUCTS |
| `/our-story/` | OUR STORY |
| `/quality-assurance/` | QUALITY ASSURANCE |
| `/sales/` | FLEET SALES TEAM |
| `/sea-scallops/` | SEA SCALLOPS |
| `/shipping/` | SHIPPING |
| `/site-map/` | SITE MAP |
| `/sustainability/` | SUSTAINABILITY |
| `/to-the-shore/` | To The Shore  /  Fleet Fisheries Inc. |
| `/to-your-door/` | To Your Door  /  Fleet Fisheries Inc. |
| `/traceability/` | TRACEABILITY |
| `/vendor-ach-data-aggregation-tool/` | Vendor ACH Data Aggregation Tool  /  Fleet Fisheries Inc. |
| `/vessel-jobs/` | VESSEL JOBS |

## Interactions and user journeys

- Primary navigation includes grouped page links and works with keyboard, touch, and pointer input. The mobile menu expands and collapses.
- Homepage carousel includes previous/next, slide selection, auto-advance, and pause controls; it respects the reduced-motion preference.
- Site search indexes the source page titles, descriptions, and text.
- The fleet index links to all 24 vessel profiles; profiles preserve accessible specifications and source imagery.
- Contact form fields: first name, last name, email, and message. Vessel jobs fields: first and last name, email, phone, position, years of experience, and additional notes.
- Both forms validate and submit to `/api/forms` when the optional Resend environment variables are configured. Without them, the form clearly reports that delivery did not occur and offers a prefilled email link.
- Photo galleries open a keyboard-dismissable lightbox with previous/next controls.
- The media page retains source videos through privacy-enhanced YouTube embeds and links to the Fleet Fisheries YouTube channel.

## External destinations and documents

- Google Maps embed for the source business address at 20 Blackmer Street, New Bedford, MA 02744.
- Existing YouTube, Facebook, X, Instagram, TSA cargo screening, and Fisherman’s Market destinations are retained where identified in the source site.
- Bundled source files: credit application PDF, HACCP certificate PDF, and MSC scope / certification PDF.

## Access notes

- The source sitemap included 53 pages; the navigation also links to `/from-the-sea/`, which was added to the rebuild, for 54 routes total.
- The public `/vendor-ach-data-aggregation-tool/` route did not expose readable instructions. The rebuild preserves the route, states that no public instructions were available, and offers Fleet Fisheries’ existing public contact details.
- One of the 516 distinct source image assets rejected direct downloading. Its original Wix URL is retained as the primary page image source; this asset has no bundled fallback. All other 515 assets have optimized local fallbacks.
- No form delivery credentials or other private third-party credentials were present on the source site. Resend must be configured in Vercel before forms deliver directly; otherwise visitors receive the mail-app fallback.
