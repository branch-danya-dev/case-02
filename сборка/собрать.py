"""Точка входа сборки. Векторные схемы отрисовываются с сохранением стрелок и кириллицы."""
from pathlib import Path
import sys
import runpy
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from сборка import материалы as assets
import cairosvg

def main():
    assets.dump('интерфейсы/openapi.json',assets.app.openapi())
    assets.dump('интерфейсы/тренировка.схема.json',assets.Workout.model_json_schema())
    assets.dump('интерфейсы/расчёт.схема.json',assets.Estimate.model_json_schema())
    examples=runpy.run_path(str(ROOT/'проверки/test_локальные_данные.py'))
    assets.dump('интерфейсы/тренировка.пример.json',examples['WORKOUT'])
    assets.dump('интерфейсы/расчёт.пример.json',examples['ESTIMATE'])
    assets.diagrams()
    # Финальная отрисовка: прежний промежуточный PNG не сохранял SVG-маркеры стрелок.
    # Увеличиваем только подписи; сами сообщения и порядок не меняются.
    path=ROOT/'схемы/последовательность-оплаты.svg'
    root=ET.fromstring(path.read_text(encoding='utf-8'))
    ET.register_namespace('','http://www.w3.org/2000/svg')
    for node in root.iter():
        if node.tag.endswith('text'):
            if node.get('font-size')=='14': node.set('font-size','18')
            elif node.get('font-size')=='17': node.set('font-size','19')
    svg=ET.tostring(root,encoding='unicode')
    path.write_text(svg,encoding='utf-8')
    cairosvg.svg2png(bytestring=svg.encode(),write_to=str(ROOT/'схемы/последовательность-оплаты.png'),scale=2)
    assets.board()
    assets.portfolio()
    from стенд.локализация import write_reference
    write_reference(ROOT)
    print('Созданы контракты, локальные примеры, пять схем, две версии доски и PDF.')

if __name__=='__main__': main()
