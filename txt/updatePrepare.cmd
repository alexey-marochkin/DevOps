"C:\Program Files\1cv8\common\1cestart.exe" DESIGNER /DisableSplash /DisableStartupDialogs /S "RTITS-1C-04\ERP_DEMO_2_5_17_48" /N "Администратор" /ManageCfgSupport -disableSupport -force /UpdateDBCfg /Out D:\Users\MAV\GIT\.logs\supportdesable.log
"C:\Program Files\1cv8\common\1cestart.exe" DESIGNER /DisableSplash /DisableStartupDialogs /S "RTITS-1C-04\ERP_DEMO_2_5_17_48" /N "Администратор" /UpdateDBCfg /Out D:\Users\MAV\GIT\.logs\supportdesableUpdateDB.log

"C:\Program Files\1cv8\common\1cestart.exe" DESIGNER /DisableSplash /DisableStartupDialogs /S "RTITS-1C-04\ERP_DEMO_2_5_17_48" /N "Администратор" /DumpConfigToFiles "D:\Users\MAV\GIT\erp\Config" -force -Server -JobsCount 16 /Out D:\Users\MAV\GIT\.logs\dumptofiles.log


"C:\Program Files\1cv8\8.3.23.2040\bin\ibcmd.exe" infobase config export --data="D:\Users\MAV\ibcmd\erp_rel" --db-server=RTITS-1C-04 --dbms=MSSQLServer --db-name=ERP_DEMO_2_5_12_167 "D:\Users\MAV\GIT\erp\Config"

"C:\Program Files\1cv8\8.3.24.1467\bin\ibcmd.exe" infobase config export --data="D:\Users\MAV\ibcmd\erp_rel" --db-server=RTITS-1C-04 --dbms=MSSQLServer --db-name=ERP_DEMO_2_5_12_167 --user "Администратор" --password "" --force --sync "D:\Users\MAV\GIT\erp\Config"