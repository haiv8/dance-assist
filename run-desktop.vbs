Option Explicit

Dim shell
Dim fso
Dim root
Dim launcher
Dim target

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

root = fso.GetParentFolderName(WScript.ScriptFullName)
launcher = fso.BuildPath(root, "scripts\run-desktop-hidden.vbs")
target = fso.BuildPath(root, "run-desktop.bat")

shell.Run Chr(34) & WScript.FullName & Chr(34) & " " & Chr(34) & launcher & Chr(34) & " " & Chr(34) & target & Chr(34), 0, False
