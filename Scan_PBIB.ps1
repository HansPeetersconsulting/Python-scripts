Param(
    [Parameter(Mandatory = $true)]
    [string]$DefinitionPath,

    [switch]$DebugMode,
    [switch]$ShowTables,
    [switch]$ShowColumns,
    [switch]$ShowMeasures,

    [string]$FilterPrefix
)

# -----------------------------
# FIXED DEFAULT SELECTION LOGIC
# -----------------------------
# Case 1: user chose NOTHING → show EVERYTHING
if (-not $ShowTables -and -not $ShowColumns -and -not $ShowMeasures) {
    $ShowTables   = $true
    $ShowColumns  = $true
    $ShowMeasures = $true
}

# Case 2: user chose ONLY ShowTables → table-only mode
if ($ShowTables -and -not $ShowColumns -and -not $ShowMeasures) {
    $Mode = "TablesOnly"
} else {
    $Mode = "Normal"
}

$prefixUsed = $FilterPrefix -and $FilterPrefix.Trim() -ne ""

function DBG { if ($DebugMode) { param($m) Write-Host $m -ForegroundColor DarkGray } }

Write-Host "Scanning PBIR folder:"
Write-Host $DefinitionPath

# -----------------------------
# INTERNAL STORAGE
# -----------------------------
$results = New-Object System.Collections.ArrayList
$visualTables = @{}

function Add-Table {
    param($Page, $Visual, $Table)

    $key = "$Page|$Visual"
    if (-not $visualTables.ContainsKey($key)) {
        $visualTables[$key] = New-Object System.Collections.Generic.HashSet[string]
    }
    $visualTables[$key].Add($Table) | Out-Null
}

function Add-Entry {
    param($Page, $Visual, $Table, $Name, $Type)

    # Always track table → used by ShowTables mode
    if ($Table) { Add-Table $Page $Visual $Table }

    # Table-only mode: ignore columns/measures entirely
    if ($Mode -eq "TablesOnly") { return }

    # Apply type filters
    if ($Type -eq "Column"  -and -not $ShowColumns)  { return }
    if ($Type -eq "Measure" -and -not $ShowMeasures) { return }

    # Prefix filtering
    if ($prefixUsed) {
        $p = $FilterPrefix.ToLower()
        if (-not ($Table.ToLower().StartsWith($p) -or $Name.ToLower().StartsWith($p))) {
            return
        }
    }

    $null = $results.Add([PSCustomObject]@{
        PageGuid   = $Page
        VisualGuid = $Visual
        Table      = $Table
        Name       = $Name
        Type       = $Type
    })
}

# -----------------------------
# FIELD EXTRACTION
# -----------------------------
function ScanField {
    param($field, $Page, $Visual)

    # Column
    if ($field.PSObject.Properties.Name -contains "Column") {
        $c = $field.Column
        Add-Entry $Page $Visual $c.Expression.SourceRef.Entity $c.Property "Column"
    }

    # Measure
    if ($field.PSObject.Properties.Name -contains "Measure") {
        $m = $field.Measure
        Add-Entry $Page $Visual $m.Expression.SourceRef.Entity $m.Property "Measure"
    }

    # Sparkline
    if ($field.PSObject.Properties.Name -contains "SparklineData") {
        $s = $field.SparklineData

        if ($s.Measure.Measure.Expression.SourceRef.Entity) {
            Add-Entry $Page $Visual $s.Measure.Measure.Expression.SourceRef.Entity $s.Measure.Measure.Property "Measure"
        }

        if ($s.Groupings) {
            foreach ($g in $s.Groupings) {

                if ($g.PSObject.Properties.Name -contains "Column") {
                    $gc = $g.Column
                    Add-Entry $Page $Visual $gc.Expression.SourceRef.Entity $gc.Property "Column"
                }

                if ($g.PSObject.Properties.Name -contains "HierarchyLevel") {
                    $h = $g.HierarchyLevel
                    Add-Entry $Page $Visual $h.Expression.Hierarchy.Expression.SourceRef.Entity $h.Level "Column"
                }
            }
        }
    }
}

# -----------------------------
# JSON RECURSION
# -----------------------------
function ScanNode {
    param($node, $Page, $Visual)

    if ($null -eq $node) { return }

    if ($node -is [System.Management.Automation.PSCustomObject]) {

        $keys = $node.PSObject.Properties.Name

        if ($keys -contains "field") {
            ScanField $node.field $Page $Visual
        }

        if ($keys -contains "sortDefinition") {
            foreach ($s in $node.sortDefinition.sort) {
                Add-Entry $Page $Visual $s.field.Column.Expression.SourceRef.Entity $s.field.Column.Property "Column"
            }
        }

        foreach ($prop in $node.PSObject.Properties) {
            ScanNode $prop.Value $Page $Visual
        }
        return
    }

    if ($node -is [System.Collections.IDictionary]) {
        foreach ($key in $node.Keys) {
            ScanNode $node[$key] $Page $Visual
        }
        return
    }

    if ($node -is [System.Collections.IEnumerable] -and -not ($node -is [string])) {
        foreach ($x in $node) {
            ScanNode $x $Page $Visual
        }
        return
    }
}

# -----------------------------
# MAIN SCAN
# -----------------------------
$pagesPath = Join-Path $DefinitionPath "pages"

foreach ($page in (Get-ChildItem $pagesPath -Directory)) {

    $pageId = $page.Name
    $visualsPath = Join-Path $page.FullName "visuals"

    if (-not (Test-Path $visualsPath)) { continue }

    foreach ($visual in (Get-ChildItem $visualsPath -Directory)) {

        $visualId = $visual.Name
        $visualJson = Join-Path $visual.FullName "visual.json"

        if (-not (Test-Path $visualJson)) { continue }

        $json = Get-Content $visualJson -Raw | ConvertFrom-Json
        ScanNode $json $pageId $visualId
    }
}

# -----------------------------
# OUTPUT SECTION
# -----------------------------
Write-Host ""
Write-Host "=== RESULTS ===" -ForegroundColor Yellow
Write-Host ""

# ============================================================
# ✅ TABLE-ONLY MODE (CORRECTED)
# ============================================================
if ($Mode -eq "TablesOnly") {

    $tablesPrinted = @{}

    foreach ($visualKey in $visualTables.Keys) {

        $tbls = @()

        foreach ($t in $visualTables[$visualKey]) {
            if ($prefixUsed) {
                if ($t.ToLower().StartsWith($FilterPrefix.ToLower())) {
                    $tbls += $t
                }
            } else {
                $tbls += $t
            }
        }

        if ($prefixUsed -and $tbls.Count -eq 0) { continue }

        if (-not $prefixUsed) {
            foreach ($t in $tbls) {
                if (-not $tablesPrinted.ContainsKey($t)) {
                    Write-Host "Table: $t" -ForegroundColor Green
                    $tablesPrinted[$t] = $true
                }
            }
            continue
        }

        # prefix → show page + visual
        $parts = $visualKey.Split("|")
        Write-Host "Page: $($parts[0])" -ForegroundColor Cyan
        Write-Host "  Visual: $($parts[1])" -ForegroundColor Magenta

        foreach ($t in $tbls) {
            Write-Host "    Table: $t" -ForegroundColor Green
        }

        Write-Host ""
    }

    exit
}

# ============================================================
# ✅ NORMAL MODE (Columns + Measures)
# ============================================================
$pg = $results | Group-Object PageGuid

foreach ($page in $pg) {

    $pageId = $page.Name
    $visuals = $page.Group | Group-Object VisualGuid

    if ($prefixUsed) {
        $pageHas = $false
        foreach ($vis in $visuals) {
            $filtered = $vis.Group | Where-Object {
                $_.Table.ToLower().StartsWith($FilterPrefix.ToLower()) -or
                $_.Name.ToLower().StartsWith($FilterPrefix.ToLower())
            }
            if ($filtered.Count -gt 0) { $pageHas = $true }
        }
        if (-not $pageHas) { continue }
    }

    if ($prefixUsed) {
        Write-Host "Page: $pageId" -ForegroundColor Cyan
    }

    foreach ($vis in $visuals) {

        $visualId = $vis.Name
        $entries  = $vis.Group

        if ($prefixUsed) {
            $entries = $entries | Where-Object {
                $_.Table.ToLower().StartsWith($FilterPrefix.ToLower()) -or
                $_.Name.ToLower().StartsWith($FilterPrefix.ToLower())
            }
        }

        if ($entries.Count -eq 0) { continue }

        if ($prefixUsed) {
            Write-Host "  Visual: $visualId" -ForegroundColor Magenta
        }

        foreach ($tbl in ($entries | Group-Object Table)) {

            if ($prefixUsed) {
                Write-Host "    Table: $($tbl.Name)" -ForegroundColor Green
            } else {
                Write-Host "Table: $($tbl.Name)" -ForegroundColor Green
            }

            foreach ($row in $tbl.Group) {
                if ($prefixUsed) {
                    Write-Host "      - $($row.Type): $($row.Name)"
                } else {
                    Write-Host "- $($row.Type): $($row.Name)"
                }
            }
        }

        if ($prefixUsed) { Write-Host "" }
    }
}