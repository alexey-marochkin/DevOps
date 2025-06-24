[ERP_LoadLastSqlCopy](ERP_LoadLastSqlCopy.sql) - скрипт используется в maintenens plan для ежедневной загрузки копий баз из последней доступной резервной копии

[LoadBackupFileToDB.sql](LoadBackupFileToDB.sql) - используется в CI/CD для загрузки персональной базы разработчика или аналитика

[loadsqlcopy.os](loadsqlcopy.os) - скрипт oscript для запуска из Bamboo загрузки персональной копии и оповещения о статусах загрузки по почте или telegram