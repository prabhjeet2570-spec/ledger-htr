"""Read PAGE layout without retaining account metadata or hosted file URLs."""
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile
from .data import sha256


def read_page_export(archive, source_hash, model_name):
    with ZipFile(archive) as z:
        pages = [n for n in z.namelist() if '/page/' in n and n.endswith('.xml')]
        if len(pages) != 1:
            raise ValueError('Expected exactly one PAGE XML file')
        info = z.getinfo(pages[0])
        if info.file_size > 10_000_000:
            raise ValueError('PAGE XML exceeds size limit')
        document = ET.fromstring(z.read(info))
    ns = {'p': document.tag.split('}')[0][1:]}
    page = document.find('p:Page', ns)
    if page is None:
        raise ValueError('Missing PAGE element')
    creator = document.findtext('p:Metadata/p:Creator', default='', namespaces=ns)
    model_id = re.search(r'model_id=(\d+)', creator)
    version = re.search(r'version=([^:]+)', creator)
    order = {x.attrib['regionRef']: int(x.attrib['index']) for x in page.findall('.//p:RegionRefIndexed', ns)}
    regions = []
    for region in page.findall('p:TextRegion', ns):
        lines = []
        for line in region.findall('p:TextLine', ns):
            index = re.search(r'readingOrder\s*\{index:(\d+);', line.get('custom', ''))
            lines.append({'id': line.get('id'), 'order': int(index[1]) if index else len(lines),
                          'text': line.findtext('p:TextEquiv/p:Unicode', default='', namespaces=ns),
                          'polygon': line.find('p:Coords', ns).get('points')})
        regions.append({'id': region.get('id'), 'order': order.get(region.get('id'), len(regions)),
                        'lines': sorted(lines, key=lambda x: x['order'])})
    return {'provider': 'Transkribus', 'model_name': model_name,
            'model_id': model_id[1] if model_id else None,
            'platform_version': version[1] if version else None,
            'source_image_sha256': source_hash, 'export_archive_sha256': sha256(archive),
            'width': int(page.get('imageWidth')), 'height': int(page.get('imageHeight')),
            'scope': 'Full-page segmentation and recognition; no accuracy score',
            'regions': sorted(regions, key=lambda x: x['order'])}
