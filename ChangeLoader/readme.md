# Скрипт ChangeLoader
Содержит следующие команды:
- **config**
	- **load:** выполняет полную или частичную загрузку основной конфигурации и полную загрузку расширения из репозитория с обновлением БД
	- **dump:** выгружает .cf файл конфигурации
	- **configDumpInfo:** формирует файл ConfigDumpInfo.xml
- **processors**
	- **build:** выполняет полную или частичную сборку внешних обработок
	- **dump:** разбирает обработки на исходные файлы
	- **load:** загружает обработки в базу данных
	- **save:** выгружает обработки из базы данных

# Параметры подключения
Каждая команда требует указания настроек подключения к БД, поэтому опции с настройками подключения вынесены на самый верхний уровень:
```shell
oscript ChangeLoader.os --connection="connection_settings.json" command subcommand arguments
```
или

```shell
oscript ChangeLoader.os --logs="path" --srvname="srvname" --ibname="ibname" --user="user" --pwd="pwd" --uc="unblock_code" command subcommand arguments
```

## Список возможных опций:
- `--connection, --con - файл с параметрами подключения к базе`
- `--logs, -l - каталог с логами`
- `--srvname, -s - имя сервера`
- `--ibname, -b - имя базы`
- `--user, -u - имя пользователя`
- `--pwd, -p - пароль пользователя`
- `--uc - код разблокировки базы`

Формат файла с параметрами подключения:

```json
{
    "logs": "Каталог с логами",
    "srvname": "Имя сервера",
    "ibname": "Имя базы",
    "user": "Имя пользователя",
    "pwd": "Пароль пользователя",
    "uc": "Код разблокировки базы"
}

```
## Спек команды:
```shell
--connection | (--logs --srvname --ibname --user --pwd [--uc])
```

# Команда config load
Пример использования:
```shell
oscript ChangeLoader.os --con="connection_settings.json" config load --config --update "REPOSITORY_PATH"
```
## Список возможных опций:

- `--config, -c - включить загрузку основной конфигурации`
- `--extension, -e - включить загрузку конфигурации расширения`
- `--update, -u - обновить конфигурацию БД после загрузки (обновит динамически при возможности)`
- `--configDumpInfo, i - выгрузить ConfigDumpInfo.xml в репозиторий после загрузки`
- `--branch, -b - имя ветки для переключения`
- `REPO - каталог репозитория`
- `--diff, -d - частичная загрузка (разницы)`
- `COMMIT - хеши коммитов (от 0 до 2), разницу между которыми необходимо загрузить`
	- `0 - последний коммит`
	- `1 - разница между указанным коммитом и текущим состоянием репозитория (HEAD)`
	- `2 - разница между указанными коммитами`

## Спек команды:
```shell
((-c | -e) | (-c -e)) [-u] [-i] [-b] REPO [-d [COMMIT...]]
```

# Команда config dump
Пример использования:
```shell
oscript ChangeLoader.os --con="connection_settings.json" config dump --syntax --config "DEPLOY_PATH"
```
## Список возможных опций:
- `--syntax, -s - выполнить синтаксический контроль перед выгрузкой`
- `--config, -c - выгрузить основную конфигурацию`
- `--extension, -e - имена расширений для выгрузки`
- `PATH - каталог для выгрузки ,cf и .cfe`

## Спек команды:
```shell
[-s] ((-c | -e...) | (-c -e...)) PATH
```

# Команда config configDumpInfo
Пример использования:
```shell
oscript ChangeLoader.os --con="connection_settings.json" config configDumpInfo "REPO"
```

## Список возможных опций:
- `REPO - каталог репозитория, файл выгрузить в подкаталог config`

## Спек команды:
```shell
REPO
```

# Команда proccessors build
Пример использования:
```shell
oscript ChangeLoader.os --con="connection_settings.json" processors build "REPO" "DEST" --diff COMMIT...
```
## Список возможных опций:
- `REPO - каталог репозитория`
- `DEST - каталог назначения`
- `--diff, -d - частичная загрузка (разницы)`
- `COMMIT - хеши коммитов (от 0 до 2), разницу между которыми необходимо загрузить`
	- 	`0 - последний коммит`
	- 	`1 - разница между указанным коммитом и текущим состоянием репозитория (HEAD)`
	- 	`2 - разница между указанными коммитами`

## Спек команды:
```shell
REPO DEST [-d [COMMIT...]]
```

# Команда proccessors dump
Пример использования:
```shell
oscript ChangeLoader.os --con="connection_settings.json" processors dump "SOURCE" "DEST"
```
## Список возможных опций:
- `SOURCE - каталог c обработками`
- `DEST - каталог назначения`

## Спек команды:
```shell
SOURCE DEST
```

# Команда proccessors load
Пример использования:
```shell
oscript ChangeLoader.os --con="connection_settings.json" processors load "PROCESSOR" "PATH"
```
## Список возможных опций:
- `PROCESSOR - обработка, используемая для загрузки обработок (лежит в репозитории devops: tools\ВыгрузкаЗагрузкаДополнительныхОтчетовИОбработок.epf)`
- `PATH - каталог с обработками`

## Спек команды:
```shell
PROCESSOR PATH
```

# Команда proccessors save
Пример использования:
```shell
oscript ChangeLoader.os --con="connection_settings.json" processors save "PROCESSOR" "PATH"
```
## Список возможных опций:
- `PROCESSOR - обработка, используемая для выгрузки обработок (лежит в репозитории devop: tools\ВыгрузкаЗагрузкаДополнительныхОтчетовИОбработок.epf)`
- `PATH - каталог для выгрузки обработок`

## Спек команды:
```shell
PROCESSOR PATH
```
