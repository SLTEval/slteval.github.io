import importlib.util
import json
from html.parser import HTMLParser
from pathlib import Path
import re
import shutil
import tempfile
import unittest
from urllib.parse import parse_qs, unquote, urlsplit

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

    def test_workshop_schema_does_not_publish_parent_conference(self):
        html = self.pages['index.html']
        graph = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', html)[1])['@graph']
        events = [item for item in graph if item['@type'] == 'Event']
        self.assertEqual(len(events), 1)
        self.assertTrue(events[0]['name'].startswith('SLT-Eval 2027:'))
        self.assertNotIn('superEvent', events[0])

    def test_workshop_schema_matches_confirmed_event_details(self):
        graph = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', self.pages['index.html'])[1])['@graph']
        site = json.loads((ROOT / '_data/site.json').read_text())
        event = next(item for item in graph if item['@type'] == 'Event')
        webpage = next(item for item in graph if item['@type'] == 'WebPage')
        organization = next(item for item in graph if item['@type'] == 'Organization')
        self.assertEqual(event['eventAttendanceMode'], 'https://schema.org/MixedEventAttendanceMode')
        self.assertEqual(event['startDate'], site['event']['iso'])
        self.assertEqual(event['endDate'], site['event']['iso'])
        self.assertEqual(event['description'], site['event']['description'])
        self.assertEqual(event['location']['name'], site['event']['location'])
        self.assertEqual(event['organizer']['@id'], organization['@id'])
        self.assertEqual(organization['contactPoint']['email'], site['email'])
        self.assertEqual(webpage['mainEntity']['@id'], event['@id'])
        self.assertEqual(event['mainEntityOfPage']['@id'], webpage['@id'])
        self.assertNotIn('offers', event)
        self.assertNotIn('performer', event)

    def test_structured_data_identifiers_resolve_to_current_routes(self):
        site = json.loads((ROOT / '_data/site.json').read_text())
        definitions, references = {}, set()

        def identifiers(value):
            if isinstance(value, dict):
                if '@id' in value:
                    yield value['@id']
                for item in value.values():
                    yield from identifiers(item)
            elif isinstance(value, list):
                for item in value:
                    yield from identifiers(item)

        for name, html in self.pages.items():
            graph = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', html)[1])['@graph']
            webpage = next(item for item in graph if item['@type'] == 'WebPage')
            organization = next(item for item in graph if item['@type'] == 'Organization')
            self.assertEqual(webpage['@id'], webpage['url'])
            self.assertEqual(organization['@id'], site['organizer']['url'])
            for item in graph:
                identifier = item['@id']
                if identifier in definitions:
                    self.assertEqual(definitions[identifier], item)
                definitions[identifier] = item
            references.update(identifiers(graph))

        self.assertTrue(references <= definitions.keys(), references - definitions.keys())
        for identifier in references:
            if not identifier.startswith(site['url']):
                continue
            url = urlsplit(identifier)
            target = url.path.strip('/')
            target = target + '/index.html' if target else 'index.html'
            with self.subTest(identifier=identifier):
                self.assertIn(target, self.pages)
                if url.fragment:
                    self.assertIn(url.fragment, {attrs.get('id') for _, attrs in Document(self.pages[target]).elements})

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
                            self.assertTrue(target.is_file())
                            if url.fragment and target.suffix == '.html':
                                self.assertIn(unquote(url.fragment), {a.get('id') for _, a in Document(target.read_text()).elements})

    def test_visit_counters_preserve_site_history_and_separate_pages(self):
        page_identifiers = set()
        for name, html in self.pages.items():
            counters = [attrs for tag, attrs in Document(html).elements
                        if tag == 'img' and attrs.get('class') == 'visitor-counter']
            with self.subTest(page=name):
                self.assertEqual(len(counters), 2)
                total, page = (urlsplit(counter['src']) for counter in counters)
                if name == 'index.html':
                    self.assertEqual(total.netloc, 'img.shields.io')
                    self.assertEqual(parse_qs(total.query)['url'],
                                     ['https://hits.sh/api/urns/slteval.github.io'])
                else:
                    self.assertEqual(total.netloc, 'hits.sh')
                    self.assertEqual(total.path, '/slteval.github.io.svg')
                self.assertEqual(page.netloc, 'hits.sh')
                expected = '/slteval.github.io.svg' if name == 'index.html' else '/slteval.github.io/' + name + '.svg'
                self.assertEqual(page.path, expected)
                page_identifiers.add(page.path)
        self.assertEqual(len(page_identifiers), len(self.pages))

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

    def test_missing_photo_uses_placeholder_until_photo_is_added(self):
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            shutil.copytree(ROOT / '_components', fixture / '_components')
            images = fixture / 'assets/img'
            images.mkdir(parents=True)
            shutil.copy2(ROOT / 'assets/img/avatar-placeholder.svg', images)
            template = build.environment(fixture).from_string(
                "{% from '_components/ui.html' import profile with context %}{{ profile(person) }}")
            # No optional fallback flag is required in the person's data.
            person = dict(name='Student Organizer', image='future-photo.jpg', affiliation=[])
            html = template.render(root='../', person=person)
            self.assertIn('src="../assets/img/avatar-placeholder.svg"', html)
            self.assertNotIn('src="../assets/img/future-photo.jpg"', html)
            shutil.copy2(ROOT / 'assets/img/macau-skyline.jpg', images / 'future-photo.jpg')
            html = template.render(root='../', person=person)
            self.assertIn('src="../assets/img/future-photo.jpg"', html)


if __name__ == '__main__':
    unittest.main()
