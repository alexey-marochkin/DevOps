#!/usr/bin/env python3
"""Отчёт XLSX по DEV-коммитам, впервые попавшим в ветку за период.

Python 3.9+ и Git в PATH. Дополнительные пакеты и Excel не требуются.
Пример: python export_master_dev_report.py --from 2026-01-01 --to 2026-09-30
"""

import argparse
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from datetime import date, datetime, time, timedelta, timezone
from xml.etree import ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED


MSK = timezone(timedelta(hours=3))
JIRA_BASE = "https://1c-jira.rtits.ru/browse/"
DEV = re.compile(r"(?<![A-Za-z0-9])DEV-[0-9]+(?![0-9])", re.IGNORECASE)
MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
DOCREL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"
ET.register_namespace("", MAIN)


def git(repo, *args):
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
    result = subprocess.run(
        ["git", "-C", str(repo), "-c", "i18n.logOutputEncoding=UTF-8", *args],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
    )
    if result.returncode:
        raise ValueError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout.decode("utf-8")


def parse_date(value):
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    raise argparse.ArgumentTypeError("Дата должна иметь формат ГГГГ-ММ-ДД или ДД.ММ.ГГГГ")


def fetch_branch(repo, branch):
    """Обновить ref origin, сохранив текущую и локальные ветки."""
    for prefix in ("refs/remotes/origin/", "origin/", "refs/heads/"):
        if branch.startswith(prefix):
            branch = branch[len(prefix):]
            break
    if branch.startswith("refs/"):
        raise ValueError("С --fetch укажите имя ветки, например master или origin/master")
    git(repo, "check-ref-format", "refs/heads/" + branch)
    # Явный refspec обновляет именно тот ref, который затем прочитает отчёт,
    # в том числе при нестандартной настройке remote.origin.fetch.
    git(repo, "fetch", "--no-tags", "origin",
        f"refs/heads/{branch}:refs/remotes/origin/{branch}")
    return "origin/" + branch


def collect_report(repo, branch, start, finish):
    """Сопоставить коммит с первым включившим его коммитом first-parent.

    git log --since фильтрует дату самого коммита, поэтому здесь он не
    используется. Разность reachable(release) - reachable(release^1)
    определяет первое попадание SHA в выбранную ветку.
    """
    if start > finish:
        raise ValueError("Начало периода должно быть не позже окончания")
    repo = Path(repo).resolve()
    if git(repo, "rev-parse", "--is-shallow-repository").strip() == "true":
        raise ValueError("История неполная (shallow clone). Сначала загрузите полную историю Git.")
    head = git(repo, "rev-parse", "--verify", "--end-of-options", branch + "^{commit}").strip()
    fmt = "%H%x1f%P%x1f%cI%x1f%an%x1f%s%x1f%B%x1e"
    records = {}
    for chunk in git(repo, "log", head, "--format=" + fmt).split("\x1e"):
        chunk = chunk.strip("\r\n")
        if not chunk:
            continue
        sha, parents, committed, author, subject, message = chunk.split("\x1f", 5)
        records[sha] = dict(hash=sha, parents=parents.split(), commitDate=committed,
                            author=author, subject=subject, message=message.strip())
    lower = datetime.combine(start, time.min, MSK)
    upper = datetime.combine(finish + timedelta(days=1), time.min, MSK)
    rows = []
    chain = git(repo, "rev-list", "--first-parent", "--reverse", head).splitlines()
    for sha in chain:
        release = records[sha]
        if not lower <= datetime.fromisoformat(release["commitDate"]) < upper:
            continue
        args = ["rev-list", "--no-merges", sha]
        if release["parents"]:
            args.append("^" + release["parents"][0])
        for commit in git(repo, *args).splitlines():
            record = records[commit]
            tasks = sorted({s.upper() for s in DEV.findall(record["message"])},
                           key=lambda s: int(s[4:]))
            if tasks:
                rows.append(dict(record, tasks=tasks, masterDate=release["commitDate"],
                                 releaseHash=sha))
    rows.sort(key=lambda r: (datetime.fromisoformat(r["masterDate"]),
                             datetime.fromisoformat(r["commitDate"]), r["hash"]))
    if len({r["hash"] for r in rows}) != len(rows):
        raise ValueError("В истории обнаружены повторные SHA после группировки")
    grouped = {}
    for row in rows:
        for task in row["tasks"]:
            grouped.setdefault(task, []).append(row)
    tasks = []
    for task, commits in sorted(grouped.items(), key=lambda pair: int(pair[0][4:])):
        tasks.append(dict(task=task, count=len(commits), description=commits[0]["subject"],
                          first=commits[0]["masterDate"], last=commits[-1]["masterDate"],
                          authors="; ".join(sorted({r["author"] for r in commits}))))
    return dict(rows=rows, tasks=tasks, branch=branch, master=head,
                start=start.isoformat(), finish=finish.isoformat())


def display_date(value):
    # ISO-порядок сохраняет правильную сортировку текстовых дат в Excel.
    # Текст виден одинаково в Excel и просмотрщиках без поддержки numFmt.
    return datetime.fromisoformat(value).astimezone(MSK).strftime("%Y-%m-%d %H:%M")


def sheet_data(data):
    period = f'{data["start"]} — {data["finish"]}, включительно'
    task_columns = max([1] + [len(r["tasks"]) for r in data["rows"]])
    commits = [[i, r["tasks"][0], r["subject"], display_date(r["masterDate"]),
                r["author"], display_date(r["commitDate"]), r["hash"], r["releaseHash"],
                "Тема" if DEV.search(r["subject"]) else "Тело сообщения",
                *r["tasks"][1:], *[""] * (task_columns - len(r["tasks"]))]
               for i, r in enumerate(data["rows"], 1)]
    tasks = [[i, t["task"], t["description"], t["count"], display_date(t["first"]),
              display_date(t["last"]), t["authors"]]
             for i, t in enumerate(data["tasks"], 1)]
    source_status = 'Ветка загружена с origin перед формированием отчёта.' if data.get('fetched') else 'Сервер автоматически не обновляется.'
    source = f'Источник: Git ref {data["branch"]}, SHA {data["master"]}. {source_status}'
    return [dict(
        name="Коммиты", title=f'ERP · Коммиты изменений с задачами DEV в {data["branch"]}',
        notes=[f'Период попадания в ветку: {period}. Время — Москва (UTC+3).',
               'Отбор: первое появление SHA в цепочке первых родителей ветки. DEV-<номер> ищется во всём сообщении.',
               'Только коммиты без слияния (0 или 1 родитель). Даты: ГГГГ-ММ-ДД ЧЧ:ММ, текст для совместимости просмотрщиков.',
               source],
        summary=f'Коммитов изменений: {len(commits)}. Уникальных задач DEV: {len(tasks)}.',
        headers=["№", "Задача DEV", "Тема коммита", "Попадание в ветку", "Автор",
                 "Дата коммита", "SHA коммита", "SHA в ветке", "Где найден DEV",
                 *[f"Задача DEV {i}" for i in range(2, task_columns + 1)]],
        widths=[6, 25, 85, 22, 35, 22, 44, 44, 21] + [18] * (task_columns - 1),
        link_columns=[1] + list(range(9, 8 + task_columns)), rows=commits, table="MasterCommits",
    ), dict(
        name="Задачи", title=f'ERP · Уникальные задачи DEV в {data["branch"]}',
        notes=[f'Период попадания в ветку: {period}. Одна строка на задачу. Время — Москва (UTC+3).',
               'Тема задачи взята из первого коммита в отчёте. Название и статус из трекера не запрашиваются.',
               'Количество учитывает только коммиты изменений. Слияния исключены. Даты первого/последнего попадания — в рамках периода.',
               source],
        summary=f'Уникальных задач DEV: {len(tasks)}. Коммитов изменений: {len(commits)}.',
        headers=["№", "Задача", "Тема первого коммита", "Коммитов", "Впервые в ветке",
                 "Последний раз в ветке", "Авторы изменений"],
        widths=[6, 18, 85, 14, 24, 25, 42], link_columns=[1], rows=tasks, table="DevTasks",
    )]


def element(parent, tag, attrs=None, text=None, ns=MAIN):
    node = ET.SubElement(parent, "{" + ns + "}" + tag, attrs or {})
    node.text = text
    return node


def xml(node):
    # OPC package parts require the package namespace as their default.
    ET.register_namespace("", node.tag[1:].split("}", 1)[0])
    ET.register_namespace("r", DOCREL)
    return ET.tostring(node, encoding="utf-8", xml_declaration=True)


def col(index):
    result = ""
    while index:
        index, digit = divmod(index - 1, 26)
        result = chr(65 + digit) + result
    return result


def safe_text(value):
    # XML 1.0 запрещает эти управляющие символы. Git допускает их в сообщениях.
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(value))[:32767]


def cell(parent, address, value, style):
    node = element(parent, "c", {"r": address, "s": str(style)})
    if isinstance(value, int):
        node.set("t", "n")
        element(node, "v", text=str(value))
    else:
        node.set("t", "inlineStr")
        is_node = element(node, "is")
        element(is_node, "t", {"{http://www.w3.org/XML/1998/namespace}space": "preserve"}, safe_text(value))


def worksheet(spec, index):
    last = col(len(spec["headers"]))
    end = 10 + len(spec["rows"])
    root = ET.Element("{" + MAIN + "}worksheet")
    element(root, "dimension", {"ref": f"A1:{last}{end}"})
    views = element(root, "sheetViews")
    view = element(views, "sheetView", {"workbookViewId": "0", "showGridLines": "0"})
    element(view, "pane", {"ySplit": "10", "topLeftCell": "A11", "activePane": "bottomLeft", "state": "frozen"})
    element(view, "selection", {"pane": "bottomLeft", "activeCell": "A11", "sqref": "A11"})
    element(root, "sheetFormatPr", {"defaultRowHeight": "24"})
    cols = element(root, "cols")
    for i, width in enumerate(spec["widths"], 1):
        element(cols, "col", {"min": str(i), "max": str(i), "width": str(width), "customWidth": "1"})
    rows = element(root, "sheetData")
    for number, values, height, style in [(2, [spec["title"]], 30, 1),
                                          *[(i, [note], 24, 2) for i, note in enumerate(spec["notes"], 4)],
                                          (8, [spec["summary"]], 28, 3),
                                          (10, spec["headers"], 36, 4)]:
        row = element(rows, "row", {"r": str(number), "ht": str(height), "customHeight": "1"})
        for i, value in enumerate(values, 1):
            cell(row, f"{col(i)}{number}", value, style)
    for number, values in enumerate(spec["rows"], 11):
        lines = max([1] + [math.ceil(len(str(v)) / max(1, spec["widths"][i] - 6))
                                 for i, v in enumerate(values) if i not in (6, 7) or spec["name"] == "Задачи"])
        row = element(rows, "row", {"r": str(number), "ht": str(min(409, max(30, lines * 15 + 8))), "customHeight": "1"})
        for i, value in enumerate(values, 1):
            cell(row, f"{col(i)}{number}", value, 6 if value and i - 1 in spec["link_columns"] else 5)
    merges = element(root, "mergeCells", {"count": "6"})
    for number in [2, 4, 5, 6, 7, 8]:
        element(merges, "mergeCell", {"ref": f"A{number}:{last}{number}"})
    links = sheet_links(spec)
    if links:
        hyperlinks = element(root, "hyperlinks")
        for link_id, address, task in links:
            element(hyperlinks, "hyperlink", {"ref": address, "{" + DOCREL + "}id": link_id,
                                               "tooltip": "Открыть " + task + " в Jira"})
    element(root, "pageMargins", {"left": "0.25", "right": "0.25", "top": "0.5", "bottom": "0.5", "header": "0.2", "footer": "0.2"})
    element(root, "pageSetup", {"orientation": "landscape", "paperSize": "9"})
    if spec["rows"]:
        parts = element(root, "tableParts", {"count": "1"})
        element(parts, "tablePart", {"{" + DOCREL + "}id": "rId1"})
    return root


def sheet_links(spec):
    links = []
    for row_number, values in enumerate(spec["rows"], 11):
        for index in spec["link_columns"]:
            if values[index]:
                links.append((f"rId{len(links) + 2}", f"{col(index + 1)}{row_number}", values[index]))
    return links


def styles():
    root = ET.Element("{" + MAIN + "}styleSheet")
    fonts = element(root, "fonts", {"count": "6"})
    for size, color, bold in [(10, "202D3B", False), (16, "243D59", True),
                               (10, "56677A", False), (10, "243D59", True), (10, "FFFFFF", True)]:
        font = element(fonts, "font")
        element(font, "sz", {"val": str(size)})
        element(font, "color", {"rgb": "FF" + color})
        element(font, "name", {"val": "Arial"})
        if bold:
            element(font, "b")
    link_font = element(fonts, "font")
    element(link_font, "sz", {"val": "10"})
    element(link_font, "color", {"rgb": "FF0563C1"})
    element(link_font, "name", {"val": "Arial"})
    element(link_font, "u", {"val": "single"})
    fills = element(root, "fills", {"count": "4"})
    for pattern, color in [("none", None), ("gray125", None), ("solid", "EBF1F7"), ("solid", "243D59")]:
        fill = element(fills, "fill")
        pattern_node = element(fill, "patternFill", {"patternType": pattern})
        if color:
            element(pattern_node, "fgColor", {"rgb": "FF" + color})
            element(pattern_node, "bgColor", {"indexed": "64"})
    borders = element(root, "borders", {"count": "1"})
    element(borders, "border")
    element(element(root, "cellStyleXfs", {"count": "1"}), "xf", {"numFmtId": "0", "fontId": "0", "fillId": "0", "borderId": "0"})
    xfs = element(root, "cellXfs", {"count": "7"})
    for font_id, fill_id, wrap, centered in [(0, 0, False, False), (1, 0, False, False),
                                          (2, 0, False, False), (3, 2, False, False),
                                          (4, 3, True, True), (0, 0, True, False),
                                          (5, 0, True, False)]:
        xf = element(xfs, "xf", {"numFmtId": "0", "fontId": str(font_id), "fillId": str(fill_id), "borderId": "0", "xfId": "0", "applyFont": "1", "applyFill": "1", "applyAlignment": "1"})
        element(xf, "alignment", {"vertical": "center", "horizontal": "center" if centered else "left", "wrapText": "1" if wrap else "0"})
    element(element(root, "cellStyles", {"count": "1"}), "cellStyle", {"name": "Normal", "xfId": "0", "builtinId": "0"})
    element(root, "dxfs", {"count": "0"})
    element(root, "tableStyles", {"count": "0", "defaultTableStyle": "TableStyleMedium2", "defaultPivotStyle": "PivotStyleLight16"})
    return root


def write_xlsx(data, output):
    """Сформировать обычный OOXML XLSX средствами стандартной библиотеки."""
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    specs = sheet_data(data)
    types = ET.Element("{" + CT + "}Types")
    for ext, content in [("rels", "application/vnd.openxmlformats-package.relationships+xml"), ("xml", "application/xml")]:
        element(types, "Default", {"Extension": ext, "ContentType": content}, ns=CT)
    def override(name, kind):
        element(types, "Override", {"PartName": name, "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml." + kind + "+xml"}, ns=CT)
    override("/xl/workbook.xml", "sheet.main")
    override("/xl/styles.xml", "styles")
    package_rels = ET.Element("{" + REL + "}Relationships")
    element(package_rels, "Relationship", {"Id": "rId1", "Type": DOCREL + "/officeDocument", "Target": "xl/workbook.xml"}, ns=REL)
    book = ET.Element("{" + MAIN + "}workbook")
    element(element(book, "bookViews"), "workbookView", {"activeTab": "0"})
    sheets = element(book, "sheets")
    book_rels = ET.Element("{" + REL + "}Relationships")
    element(book_rels, "Relationship", {"Id": "rId3", "Type": DOCREL + "/styles", "Target": "styles.xml"}, ns=REL)
    # Атомарная замена: сбой не оставляет повреждённый файл вместо старого отчёта.
    fd, temporary = tempfile.mkstemp(prefix=".dev-report-", suffix=".xlsx", dir=output.parent)
    os.close(fd)
    try:
        with ZipFile(temporary, "w", ZIP_DEFLATED) as archive:
            archive.writestr("_rels/.rels", xml(package_rels))
            archive.writestr("xl/styles.xml", xml(styles()))
            for i, spec in enumerate(specs, 1):
                override(f"/xl/worksheets/sheet{i}.xml", "worksheet")
                element(sheets, "sheet", {"name": spec["name"], "sheetId": str(i), "{" + DOCREL + "}id": f"rId{i}"})
                element(book_rels, "Relationship", {"Id": f"rId{i}", "Type": DOCREL + "/worksheet", "Target": f"worksheets/sheet{i}.xml"}, ns=REL)
                archive.writestr(f"xl/worksheets/sheet{i}.xml", xml(worksheet(spec, i)))
                if not spec["rows"]:
                    continue
                override(f"/xl/tables/table{i}.xml", "table")
                address = f'A10:{col(len(spec["headers"]))}{10 + len(spec["rows"])}'
                table = ET.Element("{" + MAIN + "}table", {"id": str(i), "name": spec["table"], "displayName": spec["table"], "ref": address, "totalsRowShown": "0"})
                element(table, "autoFilter", {"ref": address})
                columns = element(table, "tableColumns", {"count": str(len(spec["headers"]))})
                for j, header in enumerate(spec["headers"], 1):
                    element(columns, "tableColumn", {"id": str(j), "name": header})
                element(table, "tableStyleInfo", {"name": "TableStyleMedium2", "showFirstColumn": "0", "showLastColumn": "0", "showRowStripes": "1", "showColumnStripes": "0"})
                archive.writestr(f"xl/tables/table{i}.xml", xml(table))
                sheet_rels = ET.Element("{" + REL + "}Relationships")
                element(sheet_rels, "Relationship", {"Id": "rId1", "Type": DOCREL + "/table", "Target": f"../tables/table{i}.xml"}, ns=REL)
                for link_id, address, task in sheet_links(spec):
                    element(sheet_rels, "Relationship", {"Id": link_id, "Type": DOCREL + "/hyperlink",
                            "Target": JIRA_BASE + task, "TargetMode": "External"}, ns=REL)
                archive.writestr(f"xl/worksheets/_rels/sheet{i}.xml.rels", xml(sheet_rels))
            archive.writestr("xl/workbook.xml", xml(book))
            archive.writestr("xl/_rels/workbook.xml.rels", xml(book_rels))
            archive.writestr("[Content_Types].xml", xml(types))
        os.replace(temporary, output)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from", dest="start", required=True, type=parse_date, help="Начало периода, включительно")
    parser.add_argument("--to", dest="finish", required=True, type=parse_date, help="Конец периода, включительно")
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="Репозиторий (по умолчанию текущая папка)")
    parser.add_argument("--branch", default="master", help="Ветка или ref (по умолчанию master)")
    parser.add_argument("--fetch", action="store_true", help="Загрузить ветку с origin и сформировать отчёт по origin/<ветка>")
    parser.add_argument("--output", type=Path, help="Путь к XLSX; существующий отчёт по этому пути заменяется")
    args = parser.parse_args()
    if args.start > args.finish:
        parser.error("Начало периода должно быть не позже окончания")
    try:
        branch = args.branch
        if args.fetch:
            print(f"Загрузка ветки {branch} с origin...", flush=True)
            branch = fetch_branch(args.repo, branch)
        data = collect_report(args.repo, branch, args.start, args.finish)
        data["fetched"] = args.fetch
        output = args.output or Path(f"DEV_report_{args.start}_{args.finish}.xlsx")
        result = write_xlsx(data, output)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Ошибка: {exc}\n")
    print(f'Коммитов изменений: {len(data["rows"])}. Уникальных задач DEV: {len(data["tasks"])}.')
    print(f"Файл: {result}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
