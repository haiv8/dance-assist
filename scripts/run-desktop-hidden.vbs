Option Explicit

Dim shell
Dim target
Dim command

If WScript.Arguments.Count < 1 Then
  WScript.Quit 1
End If

target = WScript.Arguments(0)
Set shell = CreateObject("WScript.Shell")

command = "cmd.exe /c " & Chr(34) & Chr(34) & target & Chr(34) & " --worker" & Chr(34)
shell.Run command, 0, False
