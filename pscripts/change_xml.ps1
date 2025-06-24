$files = Get-Childitem D:\Users\MAV\GIT\ERP\Extension -Recurse -Include *.xml -File

$xmlsettings = New-Object System.Xml.XmlWriterSettings
$xmlsettings.Indent = $true
$xmlsettings.IndentChars = "`t"

foreach ($file in $files) {
    
    $waschanged = $false
    $xmldata = [xml](Get-Content $file -Encoding UTF8)
    
    $ns = new-object Xml.XmlNamespaceManager $xmldata.NameTable
    $ns.AddNamespace("ns", "http://v8.1c.ru/8.3/MDClasses")
    $ns.AddNamespace("v8", "http://v8.1c.ru/8.1/data/core")

    $nodes = $xmldata.SelectNodes(".//ns:Attribute/ns:Properties/ns:Name[contains(text(), '—умма')]/following-sibling::ns:Type/v8:Type[text()='xs:decimal']/..", $ns)

    foreach ($node in $nodes) {
        
        $newtext = "cfg:DefinedType.ƒенежна€—уммаЋюбого«нака"

        $elsign = $node.GetElementsByTagName("AllowedSign")
        if ($null -ne $elsign -and $elsign.InnerText -eq "Nonnegative" ) {
            
            $newtext = "cfg:DefinedType.ƒенежна€—уммаЌеотрицательна€";

        }

        $node.RemoveAll()
        $newNode = $node.AppendChild($xmldata.CreateElement("v8:TypeSet", "http://v8.1c.ru/8.1/data/core"))

        $newNode.InnerText = $newtext
        
        $waschanged = $true
    }


    if ($waschanged) {

        $XmlWriter = [System.XML.XmlWriter]::Create($file, $xmlsettings)
    
        $xmldata.Save($XmlWriter)
    
        $XmlWriter.Close()
        
    }
}