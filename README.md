# SLT-Eval website

The HTML uses Jinja layouts and components. GitHub Actions installs Jinja, builds the site, checks it, and deploys it to GitHub Pages on every push to `main`. Pull requests run the build and checks without deploying. You can also start the workflow manually from the Actions tab.

Edit `_content/` for page content, `_components/` for shared elements, `_layouts/` for layouts, and `_data/` for people, dates, navigation, and shared task information. CSS, JavaScript, and images live in `assets/`.

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
