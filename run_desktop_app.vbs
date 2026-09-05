Set WshShell = CreateObject("WScript.Shell")
strPath = WScript.ScriptFullName
strDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(strPath)
WshShell.CurrentDirectory = strDir
WshShell.Run "cmd /c """ & strDir & "\run.bat""", 1, False
