import argparse
import os
import re
import sys
import zipfile
from xml.etree import ElementTree as ET

W_NS = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def _text_from_runs(elem):
    parts = []
    for r in elem.findall(f'.//{W_NS}r'):
        # line breaks
        for br in r.findall(f'.//{W_NS}br'):
            parts.append('\n')
        # normal text
        for t in r.findall(f'.//{W_NS}t'):
            parts.append(t.text or '')
    # Remove spurious multiple newlines
    text = ''.join(parts)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _heading_level(p):
    pPr = p.find(f'{W_NS}pPr')
    if pPr is None:
        return None
    pStyle = pPr.find(f'{W_NS}pStyle')
    if pStyle is not None:
        val = pStyle.attrib.get(f'{W_NS}val') or pStyle.attrib.get('w:val')
        if val:
            # Match common English and Polish heading style names
            m = re.search(r'(Heading|Nag|Tytul|Title)(\d+)', val, re.IGNORECASE)
            if m:
                try:
                    lvl = int(m.group(2))
                    return max(1, min(6, lvl))
                except ValueError:
                    pass
    # Some documents store outline level
    outline = pPr.find(f'{W_NS}outlineLvl')
    if outline is not None:
        try:
            lvl = int(outline.attrib.get(f'{W_NS}val', '0')) + 1
            return max(1, min(6, lvl))
        except ValueError:
            return None
    return None


def _list_info(p):
    pPr = p.find(f'{W_NS}pPr')
    if pPr is None:
        return None, 0
    numPr = pPr.find(f'{W_NS}numPr')
    if numPr is None:
        return None, 0
    ilvl = numPr.find(f'{W_NS}ilvl')
    level = 0
    if ilvl is not None:
        try:
            level = int(ilvl.attrib.get(f'{W_NS}val', '0'))
        except ValueError:
            level = 0
    # We won't distinguish ordered/unordered without numbering.xml; use bullets
    return 'ul', level


def _table_to_md(tbl):
    rows = []
    for tr in tbl.findall(f'{W_NS}tr'):
        cells = []
        for tc in tr.findall(f'{W_NS}tc'):
            txt = _text_from_runs(tc)
            # collapse whitespace inside cells
            txt = re.sub(r'\s+', ' ', txt).strip()
            cells.append(txt)
        rows.append(cells)
    if not rows:
        return []
    # Determine column count
    cols = max((len(r) for r in rows), default=0)
    out = []
    # Normalize rows to same length
    norm = [(r + [''] * (cols - len(r))) for r in rows]
    # Header = first row
    header = '| ' + ' | '.join(norm[0]) + ' |'
    sep = '| ' + ' | '.join(['---'] * cols) + ' |'
    out.append(header)
    out.append(sep)
    for r in norm[1:]:
        out.append('| ' + ' | '.join(r) + ' |')
    return out


def docx_to_markdown(docx_path):
    if not zipfile.is_zipfile(docx_path):
        raise ValueError('Not a valid .docx file')
    with zipfile.ZipFile(docx_path) as z:
        with z.open('word/document.xml') as f:
            xml = f.read()
    root = ET.fromstring(xml)
    body = root.find(f'{W_NS}body')
    if body is None:
        return ''
    lines = []
    for elem in body:
        tag = elem.tag
        if tag == f'{W_NS}p':
            text = _text_from_runs(elem)
            if not text:
                continue
            # Heading
            lvl = _heading_level(elem)
            if lvl:
                lines.append('#' * lvl + ' ' + text)
                continue
            # List item
            list_type, level = _list_info(elem)
            if list_type:
                indent = '  ' * level
                lines.append(f'{indent}- {text}')
                continue
            # Normal paragraph
            lines.append(text)
        elif tag == f'{W_NS}tbl':
            lines.extend(_table_to_md(elem))
        # Other elements ignored
    # Ensure spacing between blocks
    out_lines = []
    prev = ''
    for ln in lines:
        if ln.startswith('#') and prev and prev.strip():
            out_lines.append('')
        out_lines.append(ln)
        prev = ln
    return '\n\n'.join(out_lines).strip() + '\n'


def main():
    parser = argparse.ArgumentParser(description='Convert .docx to Markdown (best-effort).')
    parser.add_argument('input', help='Path to .docx file')
    parser.add_argument('output', help='Path to output .md file')
    args = parser.parse_args()

    md = docx_to_markdown(args.input)
    out_dir = os.path.dirname(os.path.abspath(args.output))
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(md)
    print(f'Wrote Markdown to {args.output}')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)

