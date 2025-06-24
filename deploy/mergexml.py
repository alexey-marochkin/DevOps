import os
import shutil
import argparse
from xmldiff import main, actions
import pygit2
import subprocess
import sys

def ФайлВСпискеНеИзменяемых(ИмяФайла):
	return (ИмяФайла == "Rights.xml" or 
            ИмяФайла == "Form.xml" or
            ИмяФайла == "Template.xml" or
            ИмяФайла == "Schedule.xml" or
            ИмяФайла == "ru.html"
            )

scriptFolder = os.getcwd()

parser = argparse.ArgumentParser(description='Compares 3 XML file and tests wheirs diff')

parser.add_argument('--local', help='local file', type=str)
parser.add_argument('--remote', help='remote file', type=str)
parser.add_argument('--base', help='base file', type=str)
parser.add_argument('--result', help='result file', type=str)

parser.add_argument('-l', help='local commit', type=str)
parser.add_argument('-r', help='remote commit', type=str)
parser.add_argument('-b', help='base commit', type=str)

args = parser.parse_args()



localCommit = args.l.split(":")[0]
remoteCommit = args.r.split(":")[0]
baseCommit = args.b.split(":")[0]

originalFile = ""
# if(len(args.r.split(":"))>1):
#      originalFile = args.r.split(":")[1]
# elif (len(args.b.split(":"))>1):
#      originalFile = args.b.split(":")[1]
# elif (len(args.l.split(":"))>1):
#      originalFile = args.l.split(":")[1]

# if(originalFile == ""):
#      print("r:" + args.r)
#      print("l:" + args.l)
#      print("b:" + args.b)

localFile = args.local
remoteFile = args.remote
baseFile = args.base
resultFile = args.result
originalFile = resultFile

#scriptFolder = os.path.dirname(localFile)

print("\n\n--------------------------------\n"
      "Work dir: " + scriptFolder + "\n\n" +
      "Local commit: " + localCommit + "\n" +
      "Remote commit: " + remoteCommit + "\n" +
      "Base commit: " + baseCommit + "\n\n" +
      "Local file: " + localFile + "\n" +
      "Remote file: " + remoteFile + "\n" +
      "Base file: " + baseFile + "\n" +
      "Result file: " + resultFile + "\n")

repo = pygit2.Repository(scriptFolder)
currentBranchName = repo.head.shorthand

origin1c = None
if (remoteCommit.find("Temporary merge branch") == -1):
    # Их комит не из ориджина 1С?
    rCommit = repo.revparse_single(remoteCommit)
    origin1c = repo.branches.local.with_commit(rCommit).get('origin1c')
    #print("Текущая ветка: " + currentBranchName + "\n" +
    #      "Их ветка: " + origin1c.branch_name)

onlyVersionChanged = False
print("Проверяем в списке неизменяемых: " + os.path.basename(originalFile))
fileInUnchangeableList = ФайлВСпискеНеИзменяемых(os.path.basename(originalFile))

if (not fileInUnchangeableList):
     #Если файл всетаки возможно изменять, проверим, не только ли версия поменялась?
    diff = main.diff_files(localFile, remoteFile, diff_options={'F': 0.3, 'ratio_mode': 'faster', 'fast_match': True})
    
    print("diff получен")
    if((len(diff) == 1 and isinstance(diff[0], actions.UpdateAttrib) and diff[0].name == 'version') or
       (len(diff) == 2 and isinstance(diff[0], actions.UpdateAttrib) and diff[0].name == 'version' and 
        isinstance(diff[1], actions.UpdateAttrib) and diff[1].name == 'uuid')):
        onlyVersionChanged = True
        print("Изменений в XML: " + str(len(diff)) + "\n Имя измененного элемента: " + diff[0].name)


if (fileInUnchangeableList or onlyVersionChanged):
    if (fileInUnchangeableList):
        print("Имя файла в списке неизменяемых. Если их ветка или текущая ветка origin1c то файл будет взят от поставщика")     
    if (onlyVersionChanged):
        print("Отличается только версия XML, поэтому берем файл поставщика")        
    if (currentBranchName == 'origin1c'):
        print("Выбираю ""наш"" файл: " + resultFile + "(оставляем " + localFile + ")")
        exit(0)
    if ((origin1c != None and origin1c.branch_name == 'origin1c') or "РТ_" in resultFile or "html" in resultFile):
        print("Выбираю ""их"" файл! Копирую " + remoteFile + " в " + localFile + "(" + resultFile + ")")
        shutil.copyfile(remoteFile, localFile)
        exit(0)     

print("[osoxmlmerge] start")
pInst = subprocess.Popen(['C:\\Program Files\\Oso\\XMLMerge\\2\\OsoXMLMerge.exe',
                                        '-merge',
                                        '-silent',
                                        '-checkconflicts',
                                        '-base', baseFile,
                                        '-left', localFile,
                                        '-right', remoteFile,
                                        '-result', localFile]
                                        )
returnCode = pInst.wait()
# complitedProcess = subprocess.run(executable='C:\\Program Files\\Oso\\XMLMerge\\2\\OsoXMLMerge.exe',
#                                   args=['-merge',
#                                         '-silent',
#                                         '-checkconflicts',
#                                         '-base', baseFile,
#                                         '-left', localFile,
#                                         '-right', remoteFile,
#                                         '-result', localFile],
#                                         stdout=subprocess.STDOUT,
#                                         stderr=subprocess.STDOUT
#                                         )
print("[osoxmlmerge] end") # + pInst.stdout.decode("utf-8"))

if (returnCode < 0):
    print("Обнаружен конфликт в файле " + resultFile)
    exit(1)

exit(0)