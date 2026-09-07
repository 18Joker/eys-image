# run_task.ps1 - eys-image 批量生图一键启动脚本 (双击 run_task.bat 运行)
#
# 用法 1: 双击 run_task.bat, 按提示输入任务 JSON 的完整路径
# 用法 2: 把任务 JSON 文件直接拖到 run_task.bat 图标上
# 用法 3: 在提示处直接粘贴 JSON 内容 (单对象 {...} 或数组 [{...}],
#         支持多行, 粘贴后自动识别; 空行或输入 END 结束)
#
# 说明:
# - 调用同目录的 image_generate_v5.py 执行批量生图 (Agnes AI),
#   任务 JSON 格式见 batch_tasks_logo_goose.json 示例
#   (task_id / type / prompt / size / output_path / model 可选)
# - Python 解释器按候选列表自动选择 (workbuddy venv -> conda), 均已装 requests
# - 运行结束后: 若任务 JSON 同目录下生成了新的 image_gallery.html
#   (即本轮有成功产出), 自动在浏览器打开
# - 粘贴的 JSON 先落成临时文件 (UTF-8 无 BOM, 与 runner 读取编码一致),
#   执行结束后自动删除临时文件
# - 校验: 每个任务项必须带 prompt 字段; 粘贴设计稿类 JSON
#   (如含 style_guide / logo_prompts 的文档) 会被拒绝, 提示先转换为任务格式

param([string]$TaskFile)

$ErrorActionPreference = "Continue"
# 让 python 的 UTF-8 中文输出在本窗口正确显示
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch { }

# Python 候选解释器 (按顺序取第一个存在的), 两者均已安装 requests
$PythonCandidates = @(
    "C:\Users\22322\.workbuddy\binaries\python\envs\default\Scripts\python.exe",
    "D:\program\tools\conda\conda\python.exe"
)
$Runner = Join-Path $PSScriptRoot "image_generate_v5.py"

function Wait-Exit {
    Write-Host ""
    Read-Host "按回车键退出" | Out-Null
}

function Fail([string]$Msg) {
    Write-Host ""
    Write-Host "[错误] $Msg" -ForegroundColor Red
    Wait-Exit
    exit 1
}

# --- 核心解析: 判断缓冲区文本是否为合法任务 JSON, 并规范化为数组文本 ---
function ConvertFrom-TaskJsonBuffer {
    param([string]$Buffer)
    $trimmed = ""
    if ($null -ne $Buffer) { $trimmed = $Buffer.Trim() }
    if ([string]::IsNullOrWhiteSpace($trimmed)) {
        return [pscustomobject]@{ Ok = $false; Payload = $null; Error = "内容为空" }
    }
    if (-not $trimmed.StartsWith("[") -and -not $trimmed.StartsWith("{")) {
        return [pscustomobject]@{ Ok = $false; Payload = $null; Error = "不是 JSON 内容 (应以 [ 或 { 开头)" }
    }
    # 先直接解析, 失败则外层包裹成数组再试 (兼容单对象粘贴)
    $parsed = $null
    try { $parsed = ConvertFrom-Json -InputObject $trimmed } catch { $parsed = $null }
    if ($null -eq $parsed) {
        try { $parsed = ConvertFrom-Json -InputObject ("[" + $trimmed + "]") } catch { $parsed = $null }
    }
    if ($null -eq $parsed) {
        return [pscustomobject]@{ Ok = $false; Payload = $null; Error = "JSON 不完整或格式错误" }
    }
    # 校验: 每个任务项必须带 prompt 字段 (image_generate_v5 任务格式)
    $items = @($parsed)
    if ($items.Count -eq 0) {
        return [pscustomobject]@{ Ok = $false; Payload = $null; Error = "JSON 中没有任何任务项" }
    }
    $bad = @($items | Where-Object { $null -eq $_.PSObject.Properties['prompt'] })
    if ($bad.Count -gt 0) {
        return [pscustomobject]@{ Ok = $false; Payload = $null;
            Error = ("有 " + $bad.Count + " 项缺少 prompt 字段, 不是生图任务格式 (设计稿类 JSON 请先转换为任务格式再粘贴)") }
    }
    # 单对象粘贴 -> 包裹成数组 (image_generate_v5.py 要求任务文件为 JSON 数组)
    if ($trimmed.StartsWith("{")) {
        $trimmed = "[" + $trimmed + "]"
    }
    return [pscustomobject]@{ Ok = $true; Payload = $trimmed; Error = $null }
}

# --- 将规范化后的 JSON 数组文本写入临时文件 (UTF-8 无 BOM) ---
function Save-PastedTaskJson {
    param([string]$Payload)
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss_fff"
    $tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("eysimage_paste_task_" + $stamp + ".json")
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($tmp, $Payload, $utf8NoBom)
    return $tmp
}

# --- 交互输入: 文件路径 或 多行粘贴 JSON 内容 ---
function Read-TaskInput {
    while ($true) {
        $first = Read-Host "JSON/路径"
        if ($null -eq $first) { $first = "" }
        $firstTrim = $first.Trim()

        # --- 分支 1: 粘贴 JSON (以 [ 或 { 开头) ---
        if ($firstTrim.StartsWith("[") -or $firstTrim.StartsWith("{")) {
            $sb = New-Object System.Text.StringBuilder
            [void]$sb.AppendLine($first)
            while ($true) {
                $explicitEnd = $false
                $line = Read-Host "..."
                if ($null -eq $line) { $line = "" }
                $t = $line.Trim()

                if ($t.Length -eq 0 -or $t -ieq "END") {
                    # 空行 / END: 缓冲非空时视为显式结束; 缓冲为空则忽略并继续等待
                    if ($sb.Length -gt 0) { $explicitEnd = $true }
                }

                if ($explicitEnd) {
                    # 用户显式结束: JSON 明显未闭合时按失败处理并提示重输
                    $r = ConvertFrom-TaskJsonBuffer $sb.ToString()
                    if ($r.Ok) {
                        $tmp = Save-PastedTaskJson $r.Payload
                        return [pscustomobject]@{ Mode = "Paste"; TaskFile = $tmp; TempFile = $tmp }
                    }
                    Write-Host ""
                    Write-Host ("[提示] 粘贴的 " + $r.Error + ", 请重新输入 (直接粘贴 JSON 或输入文件路径)") -ForegroundColor Yellow
                    break
                }

                # 普通内容行: 追加缓冲后立即尝试解析, 成功即结束累积
                [void]$sb.AppendLine($line)
                $r = ConvertFrom-TaskJsonBuffer $sb.ToString()
                if ($r.Ok) {
                    $tmp = Save-PastedTaskJson $r.Payload
                    return [pscustomobject]@{ Mode = "Paste"; TaskFile = $tmp; TempFile = $tmp }
                }
            }
            continue   # 回到外层重新输入
        }

        # --- 分支 2: 文件路径 ---
        if ([string]::IsNullOrWhiteSpace($firstTrim)) {
            Write-Host "[提示] 未输入任何内容, 请重新输入:" -ForegroundColor Yellow
            continue
        }
        return [pscustomobject]@{ Mode = "Path"; TaskFile = ($firstTrim.Trim('"').Trim("'")); TempFile = $null }
    }
}

# dot-source 时仅加载以上函数 (供校验逻辑测试复用), 直接执行时才运行主流程
if ($MyInvocation.InvocationName -eq ".") { return }

Write-Host "============================================================"
Write-Host " eys-image 批量生图 (Agnes AI)"
Write-Host "============================================================"

# --- 前置检查: 解释器 ---
$PythonExe = $null
foreach ($cand in $PythonCandidates) {
    if (Test-Path -LiteralPath $cand) { $PythonExe = $cand; break }
}
if (-not $PythonExe) {
    Fail ("未找到任何 Python 解释器:`n" + ($PythonCandidates -join "`n"))
}
if (-not (Test-Path -LiteralPath $Runner)) {
    Fail "未找到主脚本: $Runner"
}

# --- 获取任务 JSON: 优先取拖放参数, 否则交互输入 (文件路径 或 粘贴 JSON 内容) ---
$PastedTempFile = $null
if ([string]::IsNullOrWhiteSpace($TaskFile)) {
    Write-Host "请输入任务 JSON 文件路径, 或直接粘贴 JSON 内容:"
    Write-Host "(粘贴支持多行, 自动识别, 空行或输入 END 结束; 也可直接把 JSON 文件拖进本窗口)" -ForegroundColor DarkGray
    $inputResult = Read-TaskInput
    $TaskFile       = $inputResult.TaskFile
    $PastedTempFile = $inputResult.TempFile
    if ($inputResult.Mode -eq "Paste") {
        Write-Host ""
        Write-Host "已识别粘贴的 JSON, 写入临时任务文件: $PastedTempFile" -ForegroundColor DarkGray
    }
}

# --- 清理路径: 去除两端引号与空白 ---
$TaskFile = $TaskFile.Trim().Trim('"').Trim("'")
if ([string]::IsNullOrWhiteSpace($TaskFile)) {
    Fail "未输入任务文件路径。"
}
if (-not (Test-Path -LiteralPath $TaskFile)) {
    Fail "任务文件不存在: $TaskFile"
}
$TaskFile = (Resolve-Path -LiteralPath $TaskFile).ProviderPath

Write-Host ""
Write-Host "任务文件 : $TaskFile"
Write-Host "解释器   : $PythonExe"
Write-Host "开始执行, 请勿关闭本窗口..."
Write-Host "============================================================"
Write-Host ""

# --- 执行生图 (输出实时透传到本窗口), 画廊生成在任务 JSON 同目录 ---
$RunStart = Get-Date
$ExitCode = 0
Push-Location $PSScriptRoot
try {
    & $PythonExe $Runner -c $TaskFile
    $ExitCode = $LASTEXITCODE
} finally {
    Pop-Location
    if ($PastedTempFile -and (Test-Path -LiteralPath $PastedTempFile)) {
        Remove-Item -LiteralPath $PastedTempFile -Force -ErrorAction SilentlyContinue
    }
}

# --- 本轮有新产出时自动打开画廊 (画廊时间戳晚于启动时间才算本轮生成) ---
$Gallery = Join-Path (Split-Path $TaskFile -Parent) "image_gallery.html"
$GalleryOpened = $false
if ((Test-Path -LiteralPath $Gallery) -and ((Get-Item -LiteralPath $Gallery).LastWriteTime -ge $RunStart)) {
    Invoke-Item -LiteralPath $Gallery
    $GalleryOpened = $true
}

Write-Host ""
Write-Host "============================================================"
if ($ExitCode -eq 0) {
    if ($GalleryOpened) {
        Write-Host " 执行完成, 结果画廊已在浏览器中打开。" -ForegroundColor Green
    } else {
        Write-Host " 执行完成, 但本轮没有新产出 (0 张成功), 未打开画廊。" -ForegroundColor Yellow
    }
} else {
    Write-Host " 执行异常退出, 退出码: $ExitCode (请检查上方日志)" -ForegroundColor Red
}
Write-Host "============================================================"
Wait-Exit
exit $ExitCode
