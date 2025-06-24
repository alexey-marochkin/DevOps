# -*- coding: utf-8 -*-
from typing import Text, get_args
import pygit2
import re
from sys import exit
import sys

def sortElements(repo_path, staged_files):

    repo = pygit2.Repository(repo_path)
    for file_path in staged_files:
        if not "Configuration.xml" in file_path:
            continue
        
        with open(file_path, 'rb') as fd:
            xml_file = fd.read().decode('utf8')

        xml_file_copy = xml_file

        tag_list = ['ChildObjects']
        for tag in tag_list:
            if tag not in xml_file:
                continue
        
            xml_file_copy = re.sub("<%s>([\s\S]*)<\/%s>" % (tag, tag), converter_re, xml_file)
            
        save_if_changed(file_path, xml_file, xml_file_copy)

        need_to_place_index = repo.status_file(file_path) & pygit2.GIT_STATUS_WT_MODIFIED
        if need_to_place_index:
            print(f"sorted file: {file_path}")
            repo.index.add(file_path)
            repo.index.write()


def converter_re(match):
        
    source = match.group(0)

    uniqueGroups = list()
    groups = re.findall('<(?!ChildObjects|\/)(\S+?)>', source) # https://regex101.com/r/eymVxm/2
    for group in groups:
        if not group in uniqueGroups:
            uniqueGroups.append(group)

    edited = ''
    objects = list()
    for group in uniqueGroups:           
        objects.clear()
        
        elements = re.findall('<%s>(\S*)<\/%s>' % (group, group), source)
        for element in elements:
            owner = '1c' if (not element.startswith('РТ_') and not element.startswith('кл')) else 'RT'
            
            # Убираем возможные дубли при мерже
            obj = (element, element.upper(), owner)
            if not obj in objects: 
                objects.append(obj)

        # В ERP языки не отсортированы
        if not group == "Language": 
            objects.sort(key=lambda obj: (obj[2], obj[1]))

        for obj in objects:
            edited += '\t\t\t<%s>%s</%s>\r\n' % (group, obj[0], group)

    edited = '<ChildObjects>\r\n' + edited + '\t\t</ChildObjects>'

    return edited


def save_if_changed(path, old_text, new_text):
    # при замене файл поменялся, значит нужно перезаписать
    if new_text != old_text:
        with open(path, 'wb') as fd:
            fd.write(new_text.encode('utf8'))

if __name__ == '__main__':
    try:
        sortElements(sys.argv[1], sys.argv[2:])
    except Exception as exp:
        print(exp)
        exit(1)
