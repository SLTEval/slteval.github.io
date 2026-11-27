# SLT-Eval website

The HTML uses Jinja layouts and components. GitHub Actions installs Jinja, builds the site, checks it, and deploys it to GitHub Pages on every push to `main`. Pull requests run the build and checks without deploying. You can also start the workflow manually from the Actions tab.

Edit `_content/` for page content, `_components/` for shared elements, `_layouts/` for layouts, and `_data/` for people, dates, navigation, and shared task information. CSS, JavaScript, and images live in `assets/`.

Profile photos are optional. Keep the intended filename in `_data/people.json`; if it is absent from `assets/img/`, the build uses the placeholder avatar. Adding the photo later automatically uses it on the next build. No per-person fallback flag is required.

The footer displays total site visits and the current page's visits. Home retains the original `slteval.github.io` Hits identifier and its 400+ historical baseline. Other pages use independent identifiers, such as `slteval.github.io/about/index.html`. Each page load requests exactly one counting image for that page. The footer reads each page's statistics through a browser-readable Shields badge and adds all page counts to calculate the total; reading statistics does not increment counters. Both displayed values come from the same set of results, so the total cannot be lower than the current page. Statistics can lag a few minutes because of provider caching; errors display an unavailable total rather than a partial sum. Counts include repeat visits. The original baseline counted the whole site before per-page tracking existed; that historical attribution cannot be recovered. The original `/old/` site remains unchanged.

**You do not need to regenerate HTML locally before committing.** Commit and push your source changes; Actions generates the published pages in `_site/`. It does not commit generated files back to the repository or create a build loop. The existing checked-in HTML remains available for previews, but may lag behind template edits until you rebuild locally.

For an optional local preview:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/build_site.py --output _site
.venv/bin/python -m http.server 8765 --directory _site
```

Then visit `http://localhost:8765/`.

The workflow is `.github/workflows/pages.yml`. GitHub Pages must use **GitHub Actions** as its publishing source (repository Settings → Pages → Build and deployment → Source). The workflow deploys only public website files; templates, Python dependencies, and build scripts are excluded from the published artifact.

The original single-page website with the Hyderabad banner is preserved on the `codex/legacy-single-page` branch (starting at `95296a9`). Each deployment checks out that branch and includes its HTML, banner, and assets at `https://slteval.github.io/old/`. The current website continues to use `main`. To publish changes to the old version, push to its branch and then run the workflow on `main` (or push a main-site update).
