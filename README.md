# Fleet Fisheries · 43 Build

A responsive, static-first rebuild of [fleetfisheries.com](https://www.fleetfisheries.com/), ready to deploy on Vercel. The project contains 54 page routes, a serverless form endpoint, the source site's documents, and image assets used by the new pages.

## Deploy without a terminal

1. Unzip `fleet-fisheries-43-build-modern.zip` on your computer.
2. Open GitHub Desktop and create a repository from the unzipped project folder. Use **Publish repository** to send it to your GitHub account. The project contains many image files, so the desktop app is convenient for uploading the complete folder together.
3. In Vercel, choose **Add New → Project**, import that GitHub repository, and deploy it with the **Other** framework preset. Leave the build and install commands blank; the finished HTML pages and assets are already included. Keep the project root as the root directory.
4. To use the existing domain, add `fleetfisheries.com` (and `www.fleetfisheries.com`, if desired) under the Vercel project's **Settings → Domains** and follow the DNS records Vercel presents.

## Contact and vessel-job forms

Both forms validate in the browser and have a working Vercel endpoint at `/api/forms`. To deliver submissions directly, add these environment variables in **Vercel → Project → Settings → Environment Variables**, then redeploy:

- `RESEND_API_KEY`: API key for a Resend account.
- `FLEET_FORMS_FROM`: a sender address verified with Resend, for example `Website <website@your-verified-domain>`.
- `FLEET_FORMS_TO`: optional recipient; defaults to `sales@fleetfisheries.com`.

If direct email delivery is not configured, the page clearly reports that the form did not send and provides a prefilled email link addressed to `sales@fleetfisheries.com`. The page never reports an unsent form as delivered. Crew inquiries include the source site's deckhand application fields and are addressed to the same sales inbox for Fleet Management Group LLC.

## Images, documents, and source notes

- Page images use the corresponding live Fleet Fisheries Wix image URL as their primary `src`. The project also bundles optimized WebP fallbacks and switches to a local copy if a live image URL fails.
- One original source image refused the direct asset download request. Its live URL remains in the page data, and the source access limitation is recorded in `SOURCE_AUDIT.md`.
- The credit application and two certification documents are bundled under `assets/docs/`.
- `SOURCE_AUDIT.md` lists all reviewed pages and summarizes the accessible interactions, external services, and content gaps.

## Project files

- Each public page is a pre-rendered `index.html` in its route folder; the home page is `/index.html`.
- `assets/css/site.css` contains the responsive visual system.
- `assets/js/site.js` implements navigation, page search, the home carousel, image lightbox, image fallbacks, and form feedback.
- `api/forms.js` implements the optional Resend integration.
- `content/pages.json` contains the reviewed source content and image locations; `content/assets.json` maps Wix images to local fallbacks.
- `scripts/build_site.py` renders route pages, search data, the XML sitemap, `robots.txt`, and the 404 page.

There is intentionally no `package-lock.json` and no build dependency to install.
