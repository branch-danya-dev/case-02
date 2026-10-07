"""Воспроизводимая сборка контрактов, схем, доски и краткого PDF. Без доступа к данным пользователя."""
from pathlib import Path
import json
import sys
import subprocess
import html
import xml.etree.ElementTree as E
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from stand.api import app
from stand.models import Workout,Estimate
import runpy

def write(path,text):
    p=ROOT/path; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(text,encoding='utf-8')

def dump(path,value): write(path,json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def diagrams():
    common='graph [bgcolor="white",pad="0.25",ranksep="0.5"]; node [shape=box,style="rounded,filled",fillcolor="#EDF4F8",fontname="DejaVu Sans",fontsize=14,margin="0.18,0.12"]; edge [fontname="DejaVu Sans",fontsize=11,color="#466079"];'
    graphs={
      'architecture':'''digraph G { rankdir=TB; %s
        subgraph cluster_local {label="УСТРОЙСТВО ВЛАДЕЛЬЦА";fontname="DejaVu Sans";color="#9DB4C5";
        ui[label="Интерфейс приложения"]; calc[label="Дневник и расчёты\\nЛокальные версии данных"]; model[label="3D-визуализация\\nФото только на устройстве"];ui->calc;calc->model;}
        subgraph cluster_server {label="СЕРВЕР ДОСТУПА";fontname="DejaVu Sans";color="#9DB4C5";
        api[label="Регистрация и подписка"];db[label="PostgreSQL\\nАккаунты, платежи, периоды",shape=cylinder];api->db;}
        pay[label="Внешний платёжный сервис\\nВ стенде — имитатор"];ui->api[label="Вход и право доступа\\nБез дневника и фото"];api->pay[label="Создание и сверка оплаты"];pay->api[label="Уведомление",style=dashed];}'''%common,
      'server-er':'''digraph G {rankdir=TB;%s
        a[label="accounts\\nid PK; email UNIQUE"];s[label="sessions\\nid PK; account_id FK"];p[label="payments\\nid PK; account_id FK\\nUNIQUE(account_id, idempotency_key)"];r[label="subscription_periods\\npayment_id PK/FK\\nstarts_at; ends_at; revoked"];e[label="provider_events\\nid PK; payment_id FK"];t[label="plans\\ncode PK; amount_minor\\nduration_seconds"];c[label="challenges\\nid PK; email; expires_at\\nattempts; used"];
        a->s[label="1 : 0..*"];a->p[label="1 : 0..*"];t->p[label="1 : 0..*"];p->r[label="1 : 0..1"];p->e[label="1 : 0..*"];c->a[label="Подтверждение входа\\nне FK",style=dashed];}'''%common,
      'payment-states':'''digraph G {rankdir=LR;%s
        a[label="creating\\nИсход создания неизвестен"];p[label="pending\\nОплата не подтверждена"];s[label="succeeded\\nУспех подтверждён"];c[label="canceled\\nОтмена"];r[label="refunded\\nПолный возврат"];
        a->p[label="Создание подтверждено"];a->a[label="Повтор с тем же ключом"];p->s[label="Доверенная сверка"];p->c[label="Отмена подтверждена"];s->r[label="Возврат подтверждён"];a->s[style=dashed,label="Сверка после потери ответа"];a->c[style=dashed];p->r[style=dashed,label="Пропущен успех"];a->r[style=dashed];}'''%common}
    for name,text in graphs.items():
        write('diagrams/'+name+'.dot',text)
        for ext in ('svg','png'):
            subprocess.run(['dot','-T'+ext,str(ROOT/'diagrams'/f'{name}.dot'),'-o',str(ROOT/'diagrams'/f'{name}.{ext}')],check=True)
    sequence()
    bpmn()

def sequence():
    labels=['Клиент','Сервер API','PostgreSQL','Провайдер'];xs=[75,275,470,685]
    messages=[(0,1,'Создать платёж',False),(1,2,'Сохранить creating',False),(1,3,'Создать: стабильный ID',False),
              (3,1,'pending',True),(1,0,'202: paymentId',True),(3,1,'Уведомление',False),
              (1,3,'Проверить статус и сумму',False),(3,1,'Подтверждённые данные',True),
              (1,2,'Событие + период: транзакция',False),(0,1,'Права: второе устройство',False),(1,0,'Доступ до endsAt',True)]
    out=['<svg xmlns="http://www.w3.org/2000/svg" width="760" height="610" viewBox="0 0 760 610"><rect width="760" height="610" fill="white"/><defs><marker id="arr" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6" fill="none" stroke="#28445b"/></marker></defs>']
    for x,label in zip(xs,labels):
        out.append(f'<rect x="{x-65}" y="15" width="130" height="38" rx="3" fill="#edf4f8" stroke="#466079"/><text x="{x}" y="40" text-anchor="middle" font-family="DejaVu Sans" font-size="17">{label}</text><line x1="{x}" y1="53" x2="{x}" y2="540" stroke="#789" stroke-dasharray="5,5"/>')
    puml=['@startuml','title Проверка оплаты и доступа','participant Клиент as C','participant "Сервер API" as A','database PostgreSQL as D','participant Провайдер as P']
    aliases=['C','A','D','P']
    for i,(a,b,text,reply) in enumerate(messages):
        y=88+i*42
        dash=' stroke-dasharray="5,4"' if reply else ''
        out.append(f'<line x1="{xs[a]}" y1="{y}" x2="{xs[b]}" y2="{y}" stroke="#28445b"{dash} marker-end="url(#arr)"/><text x="{(xs[a]+xs[b])/2}" y="{y-8}" text-anchor="middle" font-family="DejaVu Sans" font-size="14">{html.escape(text)}</text>')
        puml.append(aliases[a]+(' --> ' if reply else ' -> ')+aliases[b]+': '+text)
    note='Повтор уведомления не создаёт второй оплаченный период.'
    out.append(f'<rect x="20" y="555" width="720" height="38" fill="#edf4f8"/><text x="380" y="580" text-anchor="middle" font-family="DejaVu Sans" font-size="16">{note}</text></svg>')
    puml+=['note over A,D: '+note,'@enduml']
    write('diagrams/payment-sequence.svg',''.join(out));write('diagrams/payment-sequence.puml','\n'.join(puml))
    import fitz
    with fitz.open(str(ROOT/'diagrams/payment-sequence.svg')) as doc:
        pdf=fitz.open('pdf',doc.convert_to_pdf());pdf[0].get_pixmap(matrix=fitz.Matrix(2,2)).save(str(ROOT/'diagrams/payment-sequence.png'));pdf.close()

def bpmn():
    ns={'b':'http://www.omg.org/spec/BPMN/20100524/MODEL','bd':'http://www.omg.org/spec/BPMN/20100524/DI','dc':'http://www.omg.org/spec/DD/20100524/DC','di':'http://www.omg.org/spec/DD/20100524/DI'}
    for key,url in ns.items(): E.register_namespace(key,url)
    def el(parent,prefix,tag,attrs={},text=None):
        item=E.SubElement(parent,'{'+ns[prefix]+'}'+tag,attrs)
        if text: item.text=text
        return item
    root=E.Element('{'+ns['b']+'}definitions',{'id':'DefWorkout','targetNamespace':'urn:case02:workout'})
    proc=el(root,'b','process',{'id':'WorkoutProcess','isExecutable':'false'})
    lanes=el(proc,'b','laneSet',{'id':'Lanes'})
    lu=el(lanes,'b','lane',{'id':'UserLane','name':'Пользователь'});ls=el(lanes,'b','lane',{'id':'AppLane','name':'Приложение на устройстве'})
    nodes=[('Start','startEvent','Начало',80,90,32,32,lu),('Choose','task','Выбрать тренировку',150,65,155,70,lu),
      ('Enter','task','Указать факт',350,65,140,70,lu),('Validate','task','Проверить ввод',350,230,140,70,ls),
      ('Valid','exclusiveGateway','Данные верны?',560,240,50,50,ls),('Fix','task','Исправить ввод',720,65,150,70,lu),
      ('Calculate','task','Рассчитать оценку',700,230,160,70,ls),('Save','task','Сохранить запись',900,230,155,70,ls),('End','endEvent','Сохранено',1110,250,32,32,ls)]
    for id_,typ,name,x,y,w,h,lane in nodes:
        el(proc,'b',typ,{'id':id_,'name':name});el(lane,'b','flowNodeRef',text=id_)
    edges=[('Start','Choose',''),('Choose','Enter',''),('Enter','Validate',''),('Validate','Valid',''),
      ('Valid','Fix','Нет'),('Fix','Validate',''),('Valid','Calculate','Да'),('Calculate','Save',''),('Save','End','')]
    paths=[[(112,106),(150,106)],[(305,100),(350,100)],[(420,135),(420,230)],[(490,265),(560,265)],
      [(585,240),(585,165),(795,165),(795,135)],[(720,100),(640,100),(640,205),(420,205),(420,230)],
      [(610,265),(700,265)],[(860,265),(900,265)],[(1055,265),(1110,265)]]
    for i,(a,b,label) in enumerate(edges): el(proc,'b','sequenceFlow',{'id':f'Flow{i}','sourceRef':a,'targetRef':b,'name':label})
    col=el(root,'b','collaboration',{'id':'Collab'});el(col,'b','participant',{'id':'Pool','name':'Локальная запись тренировки','processRef':'WorkoutProcess'})
    dg=el(root,'bd','BPMNDiagram',{'id':'Diagram'});plane=el(dg,'bd','BPMNPlane',{'id':'Plane','bpmnElement':'Collab'})
    for id_,x,y,w,h in [('Pool',0,0,1200,370),('UserLane',30,0,1170,190),('AppLane',30,190,1170,180)]+[(n[0],*n[3:7]) for n in nodes]:
        sh=el(plane,'bd','BPMNShape',{'id':'Shape'+id_,'bpmnElement':id_});el(sh,'dc','Bounds',dict(x=str(x),y=str(y),width=str(w),height=str(h)))
    for i,pts in enumerate(paths):
        edge=el(plane,'bd','BPMNEdge',{'id':'Edge'+str(i),'bpmnElement':f'Flow{i}'})
        for x,y in pts: el(edge,'di','waypoint',{'x':str(x),'y':str(y)})
    E.indent(root);write('diagrams/workout.bpmn',E.tostring(root,encoding='unicode'))
    out=['<svg xmlns="http://www.w3.org/2000/svg" width="1220" height="410" viewBox="-10 -10 1220 410"><rect x="0" y="0" width="1200" height="370" fill="white" stroke="#345"/><line x1="0" y1="190" x2="1200" y2="190" stroke="#345"/><text x="40" y="30" font-family="DejaVu Sans" font-size="17">Пользователь</text><text x="40" y="220" font-family="DejaVu Sans" font-size="17">Приложение на устройстве</text><defs><marker id="barr" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6 z" fill="#345"/></marker></defs>']
    for i,pts in enumerate(paths):
        coords=' '.join(f'{x},{y}' for x,y in pts)
        out.append(f'<polyline points="{coords}" fill="none" stroke="#345" marker-end="url(#barr)"/>')
        label=edges[i][2]
        if label:
            x,y=pts[1];out.append(f'<text x="{x+8}" y="{y-8}" font-family="DejaVu Sans" font-size="16">{label}</text>')
    for id_,typ,name,x,y,w,h,lane in nodes:
        if 'Event' in typ:
            out.append(f'<circle cx="{x+w/2}" cy="{y+h/2}" r="{w/2}" fill="white" stroke="#345" stroke-width="{3 if typ=="endEvent" else 1}"/><text x="{x+w/2}" y="{y+h+24}" text-anchor="middle" font-family="DejaVu Sans" font-size="15">{name}</text>')
        elif typ=='exclusiveGateway':
            out.append(f'<polygon points="{x+w/2},{y} {x+w},{y+h/2} {x+w/2},{y+h} {x},{y+h/2}" fill="white" stroke="#345"/><text x="{x+w/2}" y="{y+h/2+6}" text-anchor="middle" font-size="21">×</text><text x="{x+w/2}" y="{y+h+26}" text-anchor="middle" font-family="DejaVu Sans" font-size="15">{name}</text>')
        else:
            out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="#edf4f8" stroke="#345"/>')
            words=name.split();mid=max(1,len(words)//2)
            for j,line in enumerate([' '.join(words[:mid]),' '.join(words[mid:])]):
                out.append(f'<text x="{x+w/2}" y="{y+29+j*20}" text-anchor="middle" font-family="DejaVu Sans" font-size="16">{line}</text>')
    out.append('</svg>');write('diagrams/workout-bpmn.svg',''.join(out))

def board():
    data=json.loads((ROOT/'planning/backlog.json').read_text(encoding='utf-8'))
    text=['# Доска планируемой разработки','',data['notice'],'','[Главная страница](../README.md) · [Локальная интерактивная версия](board.html)','']
    for col in data['columns']:
        text+=['## '+col,'']
        cards=[i for i in data['items'] if i['status']==col]
        if not cards: text+=['Нет карточек. Разработка в рамках гипотетической команды не заявлена.','']
        for i in cards:
            text+=[f'### {i["id"]}. {i["title"]}',f'Приоритет: {i["priority"]}. Предлагаемый спринт: {i["sprint"] or "позднее"}. Требования: {", ".join(i["requirements"])}.',
                   'Условия приёмки: '+'; '.join(i['acceptance'])+'.',('Препятствие: '+i['reason']+'.') if i['blocked'] else 'Препятствие не отмечено.',f'[Материал](../{i["artifact"]})','']
    write('planning/board.md','\n'.join(text))
    template='''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Кейс 02 — доска</title><style>
body{font:16px/1.5 system-ui;background:#f3f6f8;color:#172a3a;margin:28px}h1{font-size:27px;margin-bottom:6px}.notice{max-width:1000px}button,select{font:inherit;padding:7px;margin:4px;border:1px solid #9baebb;border-radius:5px;background:white}.board{display:flex;gap:16px;align-items:flex-start;overflow-x:auto;margin-top:22px}.column{min-width:280px;width:300px;background:#e5edf2;border-radius:10px;padding:12px}.card{background:white;border:1px solid #cad6de;padding:14px;margin:12px 0;border-radius:8px}.card h3{font-size:17px}.small{font-size:13px;color:#42576b}.blocked{border-left:5px solid #af6621}.alert{font-weight:600;min-height:28px}.tag{display:inline-block;padding:2px 7px;background:#eef3f7;border-radius:4px;font-size:13px}a{color:#17517a}</style>
<h1>Кейс 02 · план разработки</h1><p class="notice">Гипотетическая команда. Начальные статусы — план, не выполненные спринты. Документы и имитатор не означают готовность функций приложения.</p><p class="small">Изменения сохраняются только в этом браузере. GitHub не обновляется. Выгрузка позволяет сохранить отдельный сценарий работы с доской.</p><button id="reset">Сбросить локальные изменения</button><button id="export">Выгрузить состояние JSON</button><div id="alert" class="alert" role="status"></div><main class="board" id="board"></main><script>
const initial=__DATA__;const key='case02-kanban-v1';let data;try{data=JSON.parse(localStorage.getItem(key))||structuredClone(initial)}catch(e){data=structuredClone(initial)}
function el(tag,text,cls){const e=document.createElement(tag);if(text)e.textContent=text;if(cls)e.className=cls;return e}
function save(){try{localStorage.setItem(key,JSON.stringify(data))}catch(e){document.querySelector('#alert').textContent='Браузер не сохранил изменения. Используйте выгрузку.'}}
function render(){const root=document.querySelector('#board');root.replaceChildren();for(const col of data.columns){const items=data.items.filter(x=>x.status===col);const wrap=el('section',null,'column');wrap.append(el('h2',col),el('p',`${items.length} карточек${data.wip[col]?' · предел '+data.wip[col]:''}`,'small'));for(const item of items){const c=el('article',null,'card'+(item.blocked?' blocked':''));c.append(el('span',item.id,'tag'),el('h3',item.title),el('p','Спринт: '+(item.sprint||'позднее')+' · приоритет '+item.priority,'small'),el('p',item.requirements.join(', '),'small'));for(const a of item.acceptance)c.append(el('p','Условие: '+a,'small'));if(item.blocked)c.append(el('p','Препятствие: '+item.reason,'small'));const select=el('select');select.setAttribute('aria-label','Состояние '+item.id);for(const target of data.columns){const opt=el('option',target);opt.value=target;opt.selected=target===item.status;select.append(opt)}select.onchange=()=>{const target=select.value;const count=data.items.filter(x=>x.status===target).length;if(data.wip[target]&&count>=data.wip[target]){document.querySelector('#alert').textContent='Предел незавершённой работы достигнут. Сначала завершите начатое.';render();return}if(target==='Завершено'&&!confirm('Это только ваш сценарий доски. Условия приёмки действительно выполнены?')){render();return}item.status=target;document.querySelector('#alert').textContent='Сохранено локально; репозиторий не менялся.';save();render()};c.append(select);wrap.append(c)}root.append(wrap)}}
document.querySelector('#reset').onclick=()=>{if(confirm('Сбросить только локальные изменения доски?')){data=structuredClone(initial);save();render()}};
document.querySelector('#export').onclick=()=>{const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=el('a');a.href=url;a.download='case02-board-scenario.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};render();</script></html>'''
    write('planning/board.html',template.replace('__DATA__',json.dumps(data,ensure_ascii=False).replace('<','\\u003c')))

def portfolio():
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Image
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.colors import HexColor
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.pagesizes import A4
    import fitz
    font=Path('/usr/share/fonts/truetype/dejavu')
    pdfmetrics.registerFont(TTFont('CaseRegular',str(font/'DejaVuSans.ttf')))
    pdfmetrics.registerFont(TTFont('CaseBold',str(font/'DejaVuSans-Bold.ttf')))
    title=ParagraphStyle('title',fontName='CaseBold',fontSize=23,leading=29,textColor=HexColor('#142e43'),spaceAfter=12)
    sub=ParagraphStyle('sub',fontName='CaseRegular',fontSize=10,leading=14,textColor=HexColor('#4f697a'),spaceAfter=20)
    heading=ParagraphStyle('heading',fontName='CaseBold',fontSize=12,leading=16,spaceBefore=10,spaceAfter=5)
    para=ParagraphStyle('body',fontName='CaseRegular',fontSize=10.5,leading=15,spaceAfter=9)
    linkstyle=ParagraphStyle('link',parent=para,fontSize=9,leading=13,textColor=HexColor('#215d88'))
    pages=json.loads((ROOT/'portfolio/pages.json').read_text(encoding='utf-8'))
    story=[];md=['# Краткое представление кейса','\n[Главная страница](../README.md) · [PDF](Рогулин-Даниил-кейс-02.pdf)\n']
    for i,page in enumerate(pages):
        story+=[Paragraph(page['title'],title),Paragraph(page['subtitle'],sub)]
        md+=['## '+page['title'],'']
        if page.get('image'):
            img=Image(str(ROOT/page['image']));img._restrictSize(490,260 if i==1 else 285);story+=[img,Spacer(1,10)]
            md += [f'![Схема](../{page["image"]})','']
        for s in page['sections']:
            story+=[Paragraph(s['heading'],heading),Paragraph(html.escape(s['text']),para)]
            md+=['### '+s['heading'],s['text'],'']
        story.append(Spacer(1,8))
        for name,path in page['links']:
            url='https://github.com/branch-danya-dev/case-02/blob/main/'+path
            story.append(Paragraph(f'<link href="{url}" color="#215d88">{html.escape(name)}</link>',linkstyle))
            md+=[f'[{name}](../{path})','']
        if i<len(pages)-1: story.append(PageBreak())
    target=ROOT/'portfolio/Рогулин-Даниил-кейс-02.pdf'
    def footer(c,doc):
        c.setStrokeColor(HexColor('#c7d5df'));c.line(44,43,551,43)
        c.setFont('CaseRegular',8);c.setFillColor(HexColor('#4f697a'));c.drawString(44,29,'Даниил Рогулин · проектное решение · case-02');c.drawRightString(551,29,str(doc.page))
    doc=SimpleDocTemplate(str(target),pagesize=A4,rightMargin=44,leftMargin=44,topMargin=43,bottomMargin=57,
                          title='Даниил Рогулин — фитнес-приложение и подписка',author='Даниил Рогулин',invariant=1)
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    write('portfolio/case.md','\n'.join(md))
    out=ROOT/'review';out.mkdir(exist_ok=True)
    with fitz.open(target) as pdf:
        if len(pdf)!=6: raise ValueError(f'Ожидалось 6 страниц, получено {len(pdf)}')
        for i,p in enumerate(pdf): p.get_pixmap(matrix=fitz.Matrix(1.4,1.4)).save(str(out/f'page-{i+1}.png'))
        print('PDF:',len(pdf),'страниц; ссылок:',sum(len(p.get_links()) for p in pdf))

def main():
    dump('contracts/openapi.json',app.openapi())
    dump('contracts/workout.schema.json',Workout.model_json_schema())
    dump('contracts/estimate.schema.json',Estimate.model_json_schema())
    data=runpy.run_path(str(ROOT/'tests/test_local.py'))
    dump('contracts/workout.example.json',data['WORKOUT']);dump('contracts/estimate.example.json',data['ESTIMATE'])
    diagrams();board();portfolio()
    print('Созданы контракты, примеры, пять схем, две версии доски и представление.')
if __name__=='__main__': main()
