cls
$env:COMPUTERNAME
Write-Host 'Get-NetAdapter:' -f Yellow
Get-NetAdapter | ? Status -EQ 'UP'| sort Name | ft -a | Out-Host
Write-Host 'Get-NetAdapterRdma:' -f Yellow
Get-NetAdapterRdma | sort name | Out-Host
Write-Host 'Get-VMSwitch:' -f Yellow
#Get-VMSwitch | Out-Host
Get-VMSwitch | select Name,SwitchType,@{N='AdapterName';E={(Get-NetAdapter -InterfaceDescription $_.NetAdapterInterfaceDescription).Name}} | Out-Host

Write-Host 'Get VMSwitchTeam/NetLbfoTeam:' -f Yellow

Write-Host 'Get-VMNetworkAdapter (ManagementOS):' -f Yellow
Get-VMNetworkAdapter -ManagementOS | Out-Host
Write-Host 'Get-VMNetworkAdapterVlan (ManagementOS):' -f Yellow
Get-VMNetworkAdapter -ManagementOS | Get-VMNetworkAdapterVlan | Out-Host
Write-Host 'Get-NetIPAddress (not loopback):' -f Yellow
Get-NetIPAddress | ? InterfaceAlias -NotMatch 'loopback' | ft InterfaceAlias,InterfaceIndex,IPAddress | Out-Host
Write-Host 'Get-NetRoute:' -f Yellow
Get-NetRoute | ? NextHop -NotMatch '0\.0\.0\.0|::' | Out-Host
Write-Host 'Get-DnsClientServerAddress:' -f Yellow
Get-DnsClientServerAddress | ? InterfaceAlias -NotMatch 'loopback' | ? AddressFamily -eq '2' | Out-Host
Write-Host 'Get-NetAdapter (RegisterThisConnectionsAddress):' -f Yellow
Get-NetAdapter | Get-DnsClient -ErrorAction SilentlyContinue | ft Name,InterfaceAlias,RegisterThisConnectionsAddress | Out-Host
Write-Host 'Get-NetIPInterface:' -f Yellow
Get-NetIPInterface | sort InterfaceAlias | Out-Host