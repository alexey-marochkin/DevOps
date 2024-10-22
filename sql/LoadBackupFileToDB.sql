--:setvar sourcedb ERP_Production
--:setvar db ERP_MAV
--:setvar bakfile D:\DBBACKUP\ERP_Production_Copy.bak

USE Master
GO

Declare @spid int
Select @spid = min(spid) from master.dbo.sysprocesses
where dbid = db_id('$(db)')
While @spid Is Not Null
Begin
	Execute ('Kill ' + @spid)
	Select @spid = min(spid) from master.dbo.sysprocesses
	where dbid = db_id('$(db)') and spid > @spid
End

GO

RESTORE DATABASE $(db) FROM DISK = '$(bakfile)' WITH REPLACE, FILE = 1, RECOVERY,
MOVE N'$(sourcedb)' TO 'D:\MSSQL\data\$(db).mdf',
MOVE N'$(sourcedb)_log' TO 'D:\MSSQL\logs\$(db)_log.ldf'
GO

USE $(db)
ALTER DATABASE $(db) SET RECOVERY SIMPLE
GO

DBCC SHRINKFILE ('$(sourcedb)_log', 0);
GO

IF '$(owner)' <> ''
	BEGIN
		ALTER AUTHORIZATION ON DATABASE::$(db) TO [$(owner)]
	END
GO