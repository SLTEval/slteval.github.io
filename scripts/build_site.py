#!/usr/bin/env python3
"""Build the static Jinja site locally or into a GitHub Pages artifact directory."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import shutil
from xml.etree.ElementTree import Element, SubElement, tostring

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from markupsafe import Markup

ROOT = Path(__file__).resolve().parents[1]


def environment(root=ROOT):
    env = Environment(loader=FileSystemLoader(root),
                      autoescape=select_autoescape(('html', 'svg')),
                      undefined=StrictUndefined, keep_trailing_newline=True)

    def profile_image(filename):
        if filename and Path(filename).name != filename:
            raise ValueError('Profile images must be filenames within assets/img')
        if filename and (root / 'assets/img' / filename).is_file():
            return filename
        return 'avatar-placeholder.svg'

    env.filters['profile_image'] = profile_image
    return env


def structured_data(site, page, canonical):
    url = site['url']
    organization = {'@type': 'Organization', '@id': url + '#organizer',
                    'name': site['organizer']['full_name'], 'url': site['organizer']['url']}
    website = {'@type': 'WebSite', '@id': url + '#website', 'url': url,
               'name': site['name'] + ' ' + site['year'], 'inLanguage': 'en',
               'publisher': {'@id': organization['@id']}}
    webpage = {'@type': 'WebPage', '@id': canonical + '#webpage', 'url': canonical,
               'name': page['title'], 'description': page['description'], 'inLanguage': 'en',
               'isPartOf': {'@id': website['@id']}, 'about': {'@id': url + '#event'},
               'primaryImageOfPage': {'@type': 'ImageObject', 'url': url + site['social_image'],
                                      'width': 1200, 'height': 630}}
    graph = [organization, website, webpage]
    if page['route'] == 'home':
        graph.append({'@type': 'Event', '@id': url + '#event',
                      'name': site['name'] + ' ' + site['year'] + ': ' + site['workshop_name'],
                      'description': page['description'], 'url': url,
                      'image': [url + site['social_image']],
                      'startDate': site['event']['iso'], 'endDate': site['event']['iso'],
                      'eventStatus': 'https://schema.org/EventScheduled',
                      'location': {'@type': 'Place', 'name': site['event']['location'],
                                   'address': {'@type': 'PostalAddress',
                                               'addressLocality': site['event']['city'],
                                               'addressCountry': site['event']['country_code']}},
                      'organizer': {'@id': organization['@id']},
                      'superEvent': {'@type': 'Event', 'name': site['conference']['name'],
                                     'url': site['conference']['url']}})
    return Markup(json.dumps({'@context': 'https://schema.org', '@graph': graph},
                             ensure_ascii=False).replace('<', '\\u003c'))


def build_outputs(root=ROOT):
    data = {path.stem: json.loads(path.read_text()) for path in (root / '_data').glob('*.json')}
    env = environment(root)
    site, pages = data['site'], data['pages']
    submission = next(row for row in data['dates']['papers'] if row.get('id') == 'submission')
    date = datetime.strptime(submission['date'], '%b %d, %Y').date()
    deadline = {'iso': date.isoformat(), 'long': f'{date:%B} {date.day}, {date.year}'}
    outputs, routes = {}, set()
    for page in pages:
        route = page['route']
        if route in routes or not route.isidentifier():
            raise ValueError(f'Invalid or repeated route: {route}')
        routes.add(route)
        if len(page['social_description']) > 125:
            raise ValueError(f'Social description is too long: {route}')
        canonical = site['url'] + ('' if route == 'home' else route + '/')
        context = dict(data, page=page, paper_deadline=deadline,
                       root='./' if route == 'home' else '../', canonical=canonical,
                       social_image=site['url'] + site['social_image'],
                       structured_data=structured_data(site, page, canonical))
        result = env.get_template(f'_content/{route}.html').render(context)
        target = 'index.html' if route == 'home' else route + '/index.html'
        outputs[target] = '\n'.join(line.rstrip() for line in result.splitlines()).lstrip() + '\n'
    sitemap = Element('urlset', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
    for page in pages:
        SubElement(SubElement(sitemap, 'url'), 'loc').text = (
            site['url'] + ('' if page['route'] == 'home' else page['route'] + '/'))
    outputs['sitemap.xml'] = tostring(sitemap, encoding='utf-8', xml_declaration=True).decode()
    outputs['robots.txt'] = ('User-agent: *\nAllow: /\nDisallow: /v0/\n\nSitemap: ' +
                              site['url'] + 'sitemap.xml\n')
    return outputs


def write_site(output, root=ROOT):
    output = output.resolve()
    if output != root.resolve() and (root.resolve() not in output.parents):
        raise ValueError('Build output must be inside the project directory')
    outputs = build_outputs(root)
    output.mkdir(parents=True, exist_ok=True)
    for name, content in outputs.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    if output != root.resolve():
        shutil.copytree(root / 'assets', output / 'assets', dirs_exist_ok=True)
        public_files = [root / 'favicon.ico', root / 'CNAME']
        public_files += list(root.glob('google*.html'))
        for extension in ('jpg', 'jpeg', 'png', 'svg', 'webp'):
            public_files += list(root.glob('*.' + extension))
        for source in public_files:
            if source.is_file():
                shutil.copy2(source, output / source.name)
        (output / '.nojekyll').touch()
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT,
                        help='Output directory (use _site for deployment)')
    parser.add_argument('--check', action='store_true', help='Check output without rewriting files')
    args = parser.parse_args()
    if args.check:
        stale = [name for name, text in build_outputs().items()
                 if not (args.output / name).is_file() or (args.output / name).read_text() != text]
        if stale:
            parser.exit(1, 'Files need rebuilding: ' + ', '.join(stale) + '\n')
        print('Generated pages are up to date.')
        return
    outputs = write_site(args.output)
    print(f'Built {len(outputs) - 2} pages in {args.output.resolve()}.')


if __name__ == '__main__':
    main()
