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

ALTER DATABASE [$(db)] SET SINGLE_USER WITH ROLLBACK IMMEDIATE
RESTORE DATABASE [$(db)] FROM  DISK = N'$(bakfile)' WITH  FILE = 1,  
MOVE N'$(sourcedb)' TO N'D:\MSSQL\Data\$(db).mdf',  
MOVE N'$(sourcedb)_log' TO N'D:\MSSQL\Logs\$(db)_log.ldf',  
NOUNLOAD,  REPLACE,  STATS = 5
ALTER DATABASE [$(db)] SET MULTI_USER
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