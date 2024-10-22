# [console]::OutputEncoding = [System.Text.Encoding]::GetEncoding('windows-1251')
$script = ($(get-location).Path + "\sql\loadsqlcopy.os")
oscript $script 'RTITS-CIS-02' 'ERP_MAV' 'D:\Users\MAV\GIT\.logs\gitflic\ERP_MAV' -encoding=windows-1251