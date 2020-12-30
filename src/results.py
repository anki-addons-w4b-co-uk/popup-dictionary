# -*- coding: utf-8 -*-

# Popup Dictionary Add-on for Anki
#
# Copyright (C)  2018-2019 Aristotelis P. <https://glutanimate.com/>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version, with the additions
# listed at the end of the license file that accompanied this program.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# NOTE: This program is subject to certain additional terms pursuant to
# Section 7 of the GNU Affero General Public License.  You should have
# received a copy of these additional terms immediately following the
# terms and conditions of the GNU Affero General Public License that
# accompanied this program.
#
# If not, please request a copy through one of the means of contact
# listed here: <https://glutanimate.com/contact/>.
#
# Any modifications to this file must keep this entire header intact.

"""
Parses collection for pertinent notes and generates result list
"""

import re

from aqt import mw
from aqt.utils import askUser

from .libaddon.debug import logger

from .config import config

# UI messages

WRN_RESCOUNT = ("<b>{}</b> relevant notes found.<br>"
                "The tooltip could take a lot of time to render and <br>"
                "temporarily slow down Anki.<br><br>"
                "<b>Are you sure you want to proceed?</b>")

# HTML format strings for results

html_reslist = """<div class="tt-reslist">{}</div>"""

html_res_normal = """\
<div class="tt-res" data-nid={}>{}<div title="Browse..." class="tt-brws"
onclick='pycmd("dctBrws:" + this.parentNode.dataset.nid)'>&rarr;</div></div>\
"""

html_res_dict = """\
<div class="tt-res tt-dict" data-nid={}>
    <div class="tt-dict-title">{}:</div>
    {}
    <div title="Browse..." class="tt-brws" onclick='pycmd("dctBrws:" + this.parentNode.dataset.nid)'>&rarr;</div>
</div>"""

html_card_dict = """\
<div class="tt-res tt-dict" data-cid=%(cid)d>
    <div class="tt-dict-title">%(term)s:</div>
    %(def)s
    <div title="Preview Card..." class="tt-card" onclick='pycmd("dctCard:" + %(cid)d)'>open card</div>
    <div title="Browse..." class="tt-brws" onclick='pycmd("dctBrws:" + %(nid)d)'>&rarr;</div>
</div>"""

html_field = """<div class="tt-fld">{}</div>"""

# RegExes for cloze marker removal

cloze_re_str = r"\{\{c(\d+)::(.*?)(::(.*?))?\}\}"
cloze_re = re.compile(cloze_re_str)

# Functions that compose tooltip content

def getContentFor(term, ignore_nid):
    """Compose tooltip content for search term.
    Returns HTML string."""
    conf = config["local"]

    note_content = None
    note_ids = set()
    content = []

    if conf["dictionaryEnabled"]:
        content.extend(search_dictionaries_for(term, note_ids))

    if conf["snippetsEnabled"]:
        note_content = getNoteSnippetsFor(term, ignore_nid, note_ids)

        if note_content:
            content.extend(note_content)

    if content:
        return html_reslist.format("".join(content))
    elif note_content is False:
        return ""
    elif note_content is None:
        return ("No other results found."
                if conf["generalConfirmEmpty"] else "")


def getNoteSnippetsFor(term, ignore_nid, note_ids):
    """Find relevant note snippets for search term.
    Returns list of HTML strings."""
    
    conf = config["local"]

    logger.debug("getNoteSnippetsFor called")
    exclusion_tokens = []
    # exclude current note
    if mw and mw.reviewer and mw.reviewer.card:
        current_nid = mw.reviewer.card.note().id
        exclusion_tokens = ["-nid:{}".format(current_nid)]

    if ignore_nid:
        exclusion_tokens.append("-nid:{}".format(ignore_nid))

    if conf["snippetsLimitToCurrentDeck"]:
        exclusion_tokens.append("deck:current")

    # construct query string
    query = u'''"{}" {}'''.format(term, " ".join(exclusion_tokens))

    # NOTE: performing the SQL query directly might be faster
    res = sorted(mw.col.findNotes(query))
    logger.debug("getNoteSnippetsFor query finished.")

    if not res:
        return None

    # Prevent slowdowns when search term is too common
    res_len = len(res)
    warn_limit = conf["snippetsResultsWarnLimit"]
    if warn_limit > 0 and res_len > warn_limit:
        if not askUser(WRN_RESCOUNT.format(res_len), title="Popup Dictionary"):
            return False

    note_content = []
    excluded_flds = conf["snippetsExcludedFields"]
    for nid in res:
        if nid in note_ids:
            continue
        note_ids.add(nid)
        note = mw.col.getNote(nid)
        valid_flds = [html_field.format(
            i[1]) for i in note.items() if i[0] not in excluded_flds]
        joined_flds = "".join(valid_flds)
        # remove cloze markers
        filtered_flds = cloze_re.sub(r"\2", joined_flds)
        note_content.append(html_res_normal.format(nid, filtered_flds))

    return note_content


def search_dictionaries_for(term, note_ids) -> []:
    result = []
    conf = config["local"]
    dictionary_term_field = conf["dictionaryTermFieldName"]
    dictionaries = conf["dictionaryNoteTypeNames"]
    for dictionary in dictionaries:
        query = u"""note:"{}" {}:"{}" """.format(dictionary,
                                                 dictionary_term_field,
                                                 term)
        res = mw.col.findNotes(query)
        if res:
            cid = -1
            nid = res[0]
            note = mw.col.getNote(nid)
            for card in note.cards():
                if card.ord == 0:
                    cid = card.id
            try:
                definition = note[conf["dictionaryDefinitionFieldName"]]
            except KeyError:
                continue
            note_ids.add(nid)
            if cid != -1:
                result.append(html_card_dict % {'cid': cid, 'term': term, 'def': definition, 'nid': nid})
            else:
                result.append(html_res_dict.format(nid, term, definition))

    return result
