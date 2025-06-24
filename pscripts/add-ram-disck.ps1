$DriveLetter = 'R'

try
{
        $NewVirtualDisk = New-IscsiVirtualDisk -Path "ramdisk:tempdbRAM.vhdx" -Size 16GB -Description 'ramdisk' -ErrorAction Stop
        Add-IscsiVirtualDiskTargetMapping -TargetName targetRAM -DevicePath "ramdisk:tempdbRAM.vhdx" -ErrorAction Stop
}
catch {break}


try   {Get-Disk | Where {$_.PartitionStyle -eq 'RAW' -and $_.BusType -eq 'iSCSI'} | Initialize-Disk -PassThru -ErrorAction Stop | New-Partition -UseMaximumSize -DriveLetter $DriveLetter -ErrorAction Stop | Format-Volume -FileSystem NTFS -NewFileSystemLabel RAMDISK -Force -AllocationUnitSize 64KB -Confirm:$false -ErrorAction Stop}
catch {break}

if (Test-Path -LiteralPath "$DriveLetter`:\") {Start-Service MSSQLSERVER; Start-Service SQLSERVERAGENT} 
