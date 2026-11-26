import importlib.util
import json
from html.parser import HTMLParser
from pathlib import Path
import re
import shutil
import tempfile
import unittest
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_site', ROOT / 'scripts/build_site.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class Document(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.elements = []
        self.feed(html)

    def handle_starttag(self, tag, attributes):
        self.elements.append((tag, dict(attributes)))

    def handle_startendtag(self, tag, attributes):
        self.handle_starttag(tag, attributes)


class SiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs = build.build_outputs()
        cls.pages = {name: html for name, html in cls.outputs.items() if name.endswith('.html')}

    def test_routes_metadata_and_navigation(self):
        self.assertEqual(len(self.pages), 8)
        for name, html in self.pages.items():
            with self.subTest(page=name):
                elements = Document(html).elements
                self.assertEqual(sum(tag == 'h1' for tag, _ in elements), 1)
                active = [attrs for tag, attrs in elements
                          if tag == 'a' and attrs.get('aria-current') == 'page']
                self.assertEqual(len(active), 1)
                expected = './' if name == 'index.html' else '../' + name.split('/')[0] + '/'
                self.assertEqual(active[0]['href'], expected)
                ids = [attrs['id'] for _, attrs in elements if 'id' in attrs]
                self.assertEqual(len(ids), len(set(ids)))
                for key in ('description', 'og:title', 'og:description', 'og:image', 'twitter:card'):
                    metas = [attrs for tag, attrs in elements if tag == 'meta' and
                             (attrs.get('name') == key or attrs.get('property') == key)]
                    self.assertEqual(len(metas), 1, key)
                    self.assertTrue(metas[0]['content'])
                    if key == 'og:description':
                        self.assertLessEqual(len(metas[0]['content']), 125)
                graph = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', html)[1])['@graph']
                self.assertTrue(any(item['@type'] == 'WebPage' for item in graph))

    def test_deployment_artifact_and_local_links(self):
        # Build into a disposable project child, exactly as the Actions output step does.
        with tempfile.TemporaryDirectory(prefix='_site-test-', dir=ROOT) as folder:
            artifact = Path(folder)
            build.write_site(artifact)
            self.assertTrue((artifact / '.nojekyll').is_file())
            self.assertTrue((artifact / 'favicon.ico').is_file())
            self.assertTrue((artifact / 'google4ae70a0e97dede06.html').is_file())
            for private in ('_content', '_data', '_layouts', '_components', 'scripts', '.git', 'requirements.txt'):
                self.assertFalse((artifact / private).exists(), private)
            for name, html in self.pages.items():
                self.assertEqual((artifact / name).read_text(), html)
                for tag, attrs in Document(html).elements:
                    for key in ('href', 'src', 'data-fallback'):
                        value = attrs.get(key)
                        if not value:
                            continue
                        url = urlsplit(value)
                        if url.scheme or url.netloc:
                            continue
                        target = (artifact / name).parent / unquote(url.path) if url.path else artifact / name
                        if target.is_dir():
                            target /= 'index.html'
                        with self.subTest(page=name, link=value):
                            if tag == 'img' and key == 'src' and not target.is_file() and attrs.get('data-fallback'):
                                self.assertTrue(((artifact / name).parent / attrs['data-fallback']).is_file())
                                continue
                            self.assertTrue(target.is_file())
                            if url.fragment and target.suffix == '.html':
                                self.assertIn(unquote(url.fragment), {a.get('id') for _, a in Document(target.read_text()).elements})

    def test_footer_is_shared_by_every_route(self):
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            for directory in ('_data', '_components', '_layouts', '_content'):
                shutil.copytree(ROOT / directory, fixture / directory)
            footer = fixture / '_components/footer.html'
            footer.write_text(footer.read_text().replace('Stay in touch', 'Contact the workshop'))
            outputs = build.build_outputs(fixture)
            for name in self.pages:
                self.assertEqual(outputs[name].count('Contact the workshop'), 1)

    def test_profile_text_is_escaped(self):
        template = build.environment().from_string(
            "{% from '_components/ui.html' import profile with context %}{{ profile(person) }}")
        html = template.render(root='../', person=dict(name='<script>example</script>',
                               image='missing.jpg', affiliation=['A & B'], fallback=True))
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('A &amp; B', html)
        self.assertIn('data-fallback="../assets/img/avatar-placeholder.svg"', html)


if __name__ == '__main__':
    unittest.main()
