# PowerShell script to register autonomous 1-Video-Daily publisher in Windows Task Scheduler
$taskName = "InstaAgentDailyPublisher"
$workDir = "C:\Users\KRISHNA\Desktop\agent"
$vbsPath = "$workDir\run_silent.vbs"

# 1. Action: Execute silent VBS runner
$action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "`"$vbsPath`"" -WorkingDirectory $workDir

# 2. Triggers: Multiple daily peak windows + At Logon (catches missed posts on boot)
$triggers = @(
    (New-ScheduledTaskTrigger -Daily -At "08:45AM"),
    (New-ScheduledTaskTrigger -Daily -At "12:45PM"),
    (New-ScheduledTaskTrigger -Daily -At "06:45PM"),
    (New-ScheduledTaskTrigger -AtLogOn)
)

# 3. Settings: Run immediately if computer was off/sleeping during scheduled time!
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 25) `
    -MultipleInstances IgnoreNew

# 4. Register task for current user
$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $triggers -Settings $settings -User $currentUser

Write-Host "SUCCESS: Windows Task '$taskName' registered successfully for $currentUser!"
Get-ScheduledTask -TaskName $taskName | Format-List TaskName, State
