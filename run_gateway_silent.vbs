Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strPath = fso.GetParentFolderName(WScript.ScriptFullName)

' Run the gateway launcher silently in the background (window style 0 = hidden)
WshShell.CurrentDirectory = strPath
WshShell.Run """" & strPath & "\run_gateway.bat""", 0, False
