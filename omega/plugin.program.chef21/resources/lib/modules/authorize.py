import json
from os import path
import xbmc
from .addonvar import texts_path, addon_icon, addon_fanart
from .utils import add_dir
from .colors import colors

COLOR1 = colors.color_text1
COLOR2 = colors.color_text2

AUTH_FILE = path.join(texts_path, 'authorize.json')
SEP = "|||"

def open_file(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()

def authorize_menu():
    file = json.loads(open_file(AUTH_FILE))
    add_dir(COLOR1('<><> [B]Authorize Services[/B] <><>'), '', '...', addon_icon, addon_fanart, COLOR1('***Authorize Services***'))
    for key in file.keys():
        add_dir(COLOR2(key), '', 27, file[key]['icon'], file[key]['icon'], COLOR2(key), name2=key)

def _strip_bb(s: str) -> str:
    import re
    if not s:
        return ''
    return re.sub(r'\[(?:/?B|/?COLOR[^\]]*)\]', '', s).strip()

def _match_by_name(items, seg):
    seg_clean = _strip_bb(seg)
    for it in items or []:
        if _strip_bb(it.get('name', '')) == seg_clean:
            return it
    return None

def _resolve_node(struct, chain):
    node = struct
    if not chain:
        return None
    top = chain[0]
    if top not in node:
        return None
    node = node[top]
    for seg in chain[1:]:
        found = None
        for it in node.get('items', []):
            if it.get('name') == seg:
                found = it
                break
        if not found:
            return None
        node = found
    return node

def _resolve_node_flexible(struct, chain):
    if chain and chain[0] in struct:
        node = _resolve_node(struct, chain)
        if node:
            return node
    if not chain:
        return None
    seg0 = chain[0]
    for _top_key, top_node in struct.items():
        cand = _match_by_name(top_node.get('items', []), seg0)
        if not cand:
            continue
        node = cand
        for seg in chain[1:]:
            node = _match_by_name(node.get('items', []), seg)
            if not node:
                break
        if node:
            return node
    return None

def _split_chain(name: str):
    """Split the incoming name path safely. Prefer our SEP; fall back to '/' for legacy."""
    if not name:
        return []
    if SEP in name:
        parts = [p.strip() for p in name.split(SEP) if p.strip()]
        xbmc.log(f'[chef21] split_chain using SEP parts={parts}', xbmc.LOGINFO)
        return parts
    # fallback: legacy slash. Beware of [/B] in BBCode; strip bracketed closers first
    legacy = name.replace('[/B]', ']').replace('[/COLOR]', ']')
    parts = [p.strip() for p in legacy.split('/') if p.strip()]
    xbmc.log(f'[chef21] split_chain legacy parts={parts}', xbmc.LOGINFO)
    return parts

def  authorize_submenu(name, icon):
    file = json.loads(open_file(AUTH_FILE))
    chain = _split_chain(name)
    xbmc.log(f'[chef21] authorize_submenu name="{name}" chain={chain}', xbmc.LOGINFO)

    node = _resolve_node_flexible(file, chain) if chain else None
    if not node:
        # Fallback to Step 2 root
        step_keys = [k for k in file.keys() if k.startswith('Step 2')]
        node = file.get(step_keys[0]) if step_keys else None
    if not node:
        xbmc.log('[chef21] authorize_submenu: node not found', xbmc.LOGINFO)
        return

    items = node.get('items', [])
    xbmc.log(f'[chef21] authorize_submenu resolved items={len(items)}', xbmc.LOGINFO)

    # Determine the top key to prefix into paths
    if chain and chain[0] in file:
        top_key = chain[0]
        base_chain = chain
    else:
        step2_keys = [k for k in file.keys() if k.startswith('Step 2')]
        top_key = step2_keys[0] if step2_keys else ''
        base_chain = [top_key]

    for item in items:
        if 'items' in item:
            next_chain = base_chain + [item['name']]
            next_name2 = SEP.join(next_chain)
            add_dir(COLOR2(item['name']), '', 27, icon, icon, item['name'],
                    name2=next_name2, isFolder=True)
        else:
            url = item.get('url', '')
            if url:
                add_dir(COLOR2(item['name']), url, 25, icon, icon, item['name'], isFolder=False)
            else:
                add_dir(COLOR2(item['name']), '', '', icon, icon, item['name'], isFolder=False)
