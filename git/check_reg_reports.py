# -*- coding: utf8 -*-
from pathlib import Path
import re
import os
import glob
import sys
import codecs

sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

def check_reg_reports(repo_path, changed_files):

    reports = set()

    with open(changed_files, 'r', encoding='utf-8') as file:
        for line in file:
         
            report_path = re.findall('Config/Reports/РегламентированныйОтчет[А-яA-z0-9]*', line)
            report_folder = Path(os.path.join(repo_path, report_path[0]))
           
            modules = glob.glob(report_folder.__str__() + "/**/Form/Module.bsl", recursive=True)
            for module in modules:
                with open(module, 'rb') as mod:
                    text_module = mod.read().decode('utf8')
                    match = re.search("RTITS|rtits|РТИТС|ртитс", text_module)
                    if (match):
                        reports.add(report_path[0])
                        break

    for report in reports:
        print("Найдена новая форма доработанного регл. отчета: ", report)


if __name__ == '__main__':
    try:
        check_reg_reports(sys.argv[1], sys.argv[2])
    except Exception as exp:
        print(exp)
        exit(1)
