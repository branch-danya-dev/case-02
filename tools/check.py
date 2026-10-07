"""Структурные проверки опубликованного комплекта. Не заменяют визуальный просмотр."""
from pathlib import Path
import json,re,sys
import xml.etree.ElementTree as E
from urllib.parse import unquote
ROOT=Path(__file__).resolve().parents[1]
errors=[];links=0
for p in ROOT.rglob('*.md'):
    if 'review' in p.parts: continue
    text=p.read_text(encoding='utf-8')
    for link in re.findall(r'\[[^\]\n]*\]\(([^)\n]+)\)',text):
        if link.startswith(('http:','https:','mailto:','#')):continue
        dest=(p.parent/unquote(link.split('#')[0])).resolve();links+=1
        if not dest.is_relative_to(ROOT) or not dest.is_file():errors.append(f'{p.relative_to(ROOT)}: {link}')
board=json.loads((ROOT/'planning/backlog.json').read_text(encoding='utf-8'))
assert len({i['id'] for i in board['items']})==len(board['items'])
for i in board['items']:
    assert i['status'] in board['columns'] and (ROOT/i['artifact']).is_file()
    assert i['status'] not in ('В работе','Проверка','Завершено'),'Не выдумывать историю разработки'
    assert i['acceptance'] and (not i['blocked'] or i['reason'])
xml=E.parse(ROOT/'diagrams/workout.bpmn')
ids={x.attrib['id'] for x in xml.iter() if 'id' in x.attrib}
for x in xml.iter():
    for attr in ('sourceRef','targetRef','bpmnElement','processRef'):
        if attr in x.attrib:assert x.attrib[attr] in ids
    if x.tag.endswith('flowNodeRef'):assert x.text in ids
import fitz
with fitz.open(ROOT/'portfolio/Рогулин-Даниил-кейс-02.pdf') as pdf:
    assert len(pdf)==6
    for p in pdf:
        assert len(p.get_text())>200
        for block in p.get_text('blocks'):
            assert block[0]>=0 and block[1]>=0 and block[2]<=p.rect.width+1 and block[3]<=p.rect.height+1
if errors:
    print('\n'.join(errors));sys.exit(1)
print(f'Внутренних ссылок: {links}; карточек: {len(board["items"])}. Ссылки, исходная доска, XML-связи BPMN и PDF проверены.')
