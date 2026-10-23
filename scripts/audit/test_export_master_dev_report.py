"""Проверка границ периода, DEV в теле, слияний и содержимого XLSX."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import io
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch
from datetime import date
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import export_master_dev_report as report


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        self.run_git('init', '-b', 'master')
        self.run_git('config', 'user.name', 'Test Author')
        self.run_git('config', 'user.email', 'report-test@example.invalid')
        self.commit('DEV-1: already in master', '2025-12-01T12:00:00+03:00')
        self.run_git('checkout', '-b', 'feature')
        self.old = self.commit('DEV-2: old change', '2025-12-20T12:00:00+03:00')
        self.run_git('checkout', 'master')
        self.run_git('merge', '--no-ff', 'feature', '-m', 'DEV-90000: merge only',
                     when='2026-01-01T00:00:00+03:00')
        self.body = self.commit('Body reference\n\nRelated: dev-3 and DEV-3',
                                '2026-01-31T23:59:59+03:00')
        self.commit('DEV-4: after period', '2026-02-01T00:00:00+03:00')
        self.run_git('checkout', '-b', 'unmerged')
        self.commit('DEV-5: not in master', '2026-01-10T12:00:00+03:00')
        self.run_git('checkout', 'master')

    def run_git(self, *args, when=None):
        env = dict(os.environ)
        if when:
            env.update(GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when)
        return subprocess.check_output(['git', '-C', str(self.repo), *args], env=env,
                                       stderr=subprocess.DEVNULL).decode().strip()

    def commit(self, message, when):
        self.run_git('commit', '--allow-empty', '-m', message, when=when)
        return self.run_git('rev-parse', 'HEAD')

    def collect(self, start=date(2026, 1, 1), end=date(2026, 1, 31)):
        return report.collect_report(self.repo, 'master', start, end)

    def test_introduction_date_and_no_merges(self):
        data = self.collect()
        self.assertEqual({r['hash'] for r in data['rows']}, {self.old, self.body})
        self.assertTrue(all(len(r['parents']) <= 1 for r in data['rows']))
        self.assertEqual([t['task'] for t in data['tasks']], ['DEV-2', 'DEV-3'])
        self.assertEqual(data['rows'][0]['masterDate'], '2026-01-01T00:00:00+03:00')
        self.assertEqual(data['rows'][0]['commitDate'], '2025-12-20T12:00:00+03:00')

    def test_end_exclusive_and_empty(self):
        self.assertEqual(len(self.collect(date(2026, 2, 1), date(2026, 2, 1))['rows']), 1)
        data = self.collect(date(2027, 1, 1), date(2027, 1, 1))
        self.assertEqual(data['rows'], [])
        output = report.write_xlsx(data, self.repo / 'empty.xlsx')
        with ZipFile(output) as z:
            self.assertNotIn('xl/tables/table1.xml', z.namelist())
            self.assertIn('Коммитов изменений: 0.', z.read('xl/worksheets/sheet1.xml').decode())

    def test_xlsx_readable_dates_and_filters(self):
        output = report.write_xlsx(self.collect(), self.repo / 'report.xlsx')
        with ZipFile(output) as z:
            self.assertIsNone(z.testzip())
            ns = {'m': report.MAIN}
            sheet = ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
            cells = {c.attrib['r']: c for c in sheet.findall('.//m:c', ns)}
            value = lambda address: ''.join(cells[address].itertext())
            self.assertEqual(value('D11'), '2026-01-01 00:00')
            self.assertEqual(value('F11'), '2025-12-20 12:00')
            self.assertEqual(cells['D11'].attrib['t'], 'inlineStr')
            self.assertIn('Коммитов изменений: 2. Уникальных задач DEV: 2.', value('A8'))
            self.assertEqual(sheet.find('m:sheetViews/m:sheetView/m:pane', ns).attrib['topLeftCell'], 'A11')
            table = ET.fromstring(z.read('xl/tables/table1.xml'))
            self.assertEqual(table.attrib['ref'], 'A10:I12')
            self.assertIsNotNone(table.find('m:autoFilter', ns))

    def test_input_dates_and_timezone(self):
        self.assertEqual(report.parse_date('30.09.2026'), date(2026, 9, 30))
        self.assertEqual(report.parse_date('2026-09-30'), date(2026, 9, 30))
        self.assertEqual(report.display_date('2025-12-31T21:00:00+00:00'), '2026-01-01 00:00')
        self.assertEqual(report.display_date('2026-02-01T00:30:00+04:00'), '2026-01-31 23:30')
        with self.assertRaises(ValueError):
            self.collect(date(2026, 2, 1), date(2026, 1, 31))

    def test_every_task_has_its_own_jira_link(self):
        data = self.collect()
        data['rows'][0]['tasks'] = ['DEV-2', 'DEV-8', 'DEV-9']
        output = report.write_xlsx(data, self.repo / 'links.xlsx')
        with ZipFile(output) as z:
            ns = {'m': report.MAIN, 'r': report.DOCREL, 'p': report.REL}
            for sheet_id in (1, 2):
                sheet = ET.fromstring(z.read(f'xl/worksheets/sheet{sheet_id}.xml'))
                relationships = ET.fromstring(z.read(f'xl/worksheets/_rels/sheet{sheet_id}.xml.rels'))
                targets = {r.attrib['Id']: r.attrib for r in relationships}
                cells = {c.attrib['r']: ''.join(c.itertext()) for c in sheet.findall('.//m:c', ns)}
                links = sheet.findall('m:hyperlinks/m:hyperlink', ns)
                self.assertEqual(len(links), 4 if sheet_id == 1 else 2)
                for link in links:
                    relation = targets[link.attrib['{' + report.DOCREL + '}id']]
                    self.assertEqual(relation['Target'], report.JIRA_BASE + cells[link.attrib['ref']])
                    self.assertEqual(relation['TargetMode'], 'External')
                if sheet_id == 1:
                    self.assertEqual(cells['B11'], 'DEV-2')
                    self.assertEqual(cells['J11'], 'DEV-8')
                    self.assertEqual(cells['K11'], 'DEV-9')
                    self.assertEqual(len(sheet.findall('m:sheetData/m:row', ns)), 9)

    def test_fetch_uses_remote_ref_and_preserves_local_branch(self):
        remote = self.repo / 'remote.git'
        self.run_git('init', '--bare', str(remote))
        self.run_git('remote', 'add', 'origin', str(remote))
        self.run_git('push', 'origin', 'master')
        remote_head = self.run_git('rev-parse', 'master')
        local_head = self.commit('DEV-6: local only', '2026-01-15T12:00:00+03:00')
        # Имитируем устаревший tracking ref, оставляя локальную master впереди.
        self.run_git('update-ref', 'refs/remotes/origin/master', self.old)
        for branch in ('master', 'origin/master'):
            selected = report.fetch_branch(self.repo, branch)
            self.assertEqual(selected, 'origin/master')
            self.assertEqual(self.run_git('rev-parse', selected), remote_head)
            self.assertEqual(self.run_git('rev-parse', 'master'), local_head)
            self.assertEqual(self.run_git('branch', '--show-current'), 'master')
            data = report.collect_report(self.repo, selected, date(2026, 1, 1), date(2026, 1, 31))
            self.assertEqual({r['hash'] for r in data['rows']}, {self.old, self.body})

    def test_fetch_failure_stops_before_report_and_keeps_output(self):
        self.run_git('remote', 'add', 'origin', str(self.repo / 'missing.git'))
        output = self.repo / 'existing.xlsx'
        output.write_bytes(b'existing report')
        argv = ['report', '--fetch', '--repo', str(self.repo), '--from', '2026-01-01',
                '--to', '2026-01-31', '--output', str(output)]
        with patch.object(report.sys, 'argv', argv), patch.object(report, 'collect_report') as collect:
            with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    report.main()
            self.assertEqual(error.exception.code, 1)
            collect.assert_not_called()
        self.assertEqual(output.read_bytes(), b'existing report')


if __name__ == '__main__':
    unittest.main()
