(function () {
    "use strict";

    var dataNode = document.getElementById("workbook-data");
    var workbook = JSON.parse(dataNode.textContent || "{}");
    var grid = document.getElementById("grid");
    var tabs = document.getElementById("tabs");
    var namebox = document.getElementById("namebox");
    var formula = document.getElementById("formula");
    var activeSheet = 0;
    var selected = { row: 0, col: 0 };

    document.getElementById("doc-title").textContent = workbook.title || "Excel";

    function colName(index) {
        var n = index + 1;
        var label = "";
        while (n > 0) {
            var rem = (n - 1) % 26;
            label = String.fromCharCode(65 + rem) + label;
            n = Math.floor((n - 1) / 26);
        }
        return label;
    }

    function sheetSize(sheet) {
        var rows = (sheet && sheet.rows) || [];
        var colCount = (sheet.widths || []).length;
        rows.forEach(function (row) {
            colCount = Math.max(colCount, row.length);
        });
        return {
            rows: rows,
            widths: sheet.widths || [],
            heights: sheet.heights || [],
            rowCount: rows.length,
            colCount: colCount,
        };
    }

    function cellInfo(line, col) {
        if (!line || col >= line.length || line[col] == null) {
            return null;
        }
        var cell = line[col];
        if (typeof cell === "string") {
            return { v: cell };
        }
        return cell;
    }

    function cellText(size, row, col) {
        var info = cellInfo(size.rows[row], col);
        if (!info || info.s) {
            return "";
        }
        return info.v || "";
    }

    function isEmpty(info) {
        return !info || (!info.s && !info.v && !info.bg);
    }

    function displaySpan(size, row, col, info) {
        var span = (info && info.cs) || 1;
        if (!info || info.s || info.w || !info.v) {
            return span;
        }
        var next = col + span;
        while (next < size.colCount && isEmpty(cellInfo(size.rows[row], next))) {
            span += 1;
            next += 1;
        }
        return span;
    }

    function showCell(size) {
        namebox.textContent = colName(selected.col) + (selected.row + 1);
        formula.textContent = cellText(size, selected.row, selected.col);
    }

    function paintCell(td, info) {
        var span = td.querySelector(".gs-cell");
        if (info.bg) {
            td.style.background = info.bg;
        }
        if (info.fg) {
            span.style.color = info.fg;
        }
        if (info.b) {
            span.style.fontWeight = "700";
        }
        if (info.sz) {
            span.style.fontSize = info.sz + "pt";
        }
        if (info.a) {
            td.style.textAlign = info.a;
        }
        if (info.va) {
            td.style.verticalAlign = info.va;
        }
        if (info.w) {
            td.classList.add("gs-wrap");
        }
        if (info.rs > 1) {
            td.rowSpan = info.rs;
        }
        if (info.cs > 1) {
            td.colSpan = info.cs;
        }
        span.textContent = info.v || "";
    }

    function renderSheet(index) {
        var sheets = workbook.sheets || [];
        var sheet = sheets[index] || { name: "Sheet1", rows: [] };
        var size = sheetSize(sheet);
        if (selected.row >= size.rowCount) {
            selected.row = 0;
        }
        if (selected.col >= size.colCount) {
            selected.col = 0;
        }
        grid.innerHTML = "";
        if (workbook.error) {
            var error = document.createElement("div");
            error.className = "gs-error";
            error.textContent = workbook.error;
            grid.appendChild(error);
            return;
        }
        var table = document.createElement("table");
        table.className = "gs-grid";
        var thead = document.createElement("thead");
        var headRow = document.createElement("tr");
        var corner = document.createElement("th");
        corner.className = "gs-corner";
        headRow.appendChild(corner);
        var col;
        for (col = 0; col < size.colCount; col++) {
            var th = document.createElement("th");
            th.textContent = colName(col);
            th.style.minWidth = (size.widths[col] || 72) + "px";
            th.style.width = (size.widths[col] || 72) + "px";
            headRow.appendChild(th);
        }
        thead.appendChild(headRow);
        table.appendChild(thead);
        var tbody = document.createElement("tbody");
        var row;
        for (row = 0; row < size.rowCount; row++) {
            var tr = document.createElement("tr");
            var rowWrap = false;
            var line = size.rows[row] || [];
            line.forEach(function (item) {
                if (item && item.w) {
                    rowWrap = true;
                }
            });
            if (!rowWrap && size.heights[row]) {
                tr.style.height = size.heights[row] + "px";
            }
            var rowHead = document.createElement("th");
            rowHead.className = "gs-rowhead";
            rowHead.textContent = String(row + 1);
            tr.appendChild(rowHead);
            var skipUntil = 0;
            for (col = 0; col < size.colCount; col++) {
                if (col < skipUntil) {
                    continue;
                }
                var info = cellInfo(line, col);
                if (info && info.s) {
                    continue;
                }
                var td = document.createElement("td");
                td.dataset.row = String(row);
                td.dataset.col = String(col);
                var span = document.createElement("span");
                span.className = "gs-cell";
                td.appendChild(span);
                var shown = displaySpan(size, row, col, info);
                if (info) {
                    paintCell(td, info);
                }
                if (shown > 1) {
                    td.colSpan = shown;
                }
                skipUntil = col + shown;
                if (isEmpty(info)) {
                    td.classList.add("gs-empty");
                }
                if (row === selected.row && col === selected.col) {
                    td.classList.add("gs-selected");
                }
                tr.appendChild(td);
            }
            tbody.appendChild(tr);
        }
        table.appendChild(tbody);
        grid.appendChild(table);
        showCell(size);
        table.addEventListener("click", function (event) {
            var cell = event.target.closest("td");
            if (!cell) {
                return;
            }
            selected.row = Number(cell.dataset.row);
            selected.col = Number(cell.dataset.col);
            var current = table.querySelector(".gs-selected");
            if (current) {
                current.classList.remove("gs-selected");
            }
            cell.classList.add("gs-selected");
            showCell(size);
        });
    }

    function renderTabs() {
        tabs.innerHTML = "";
        var sheets = workbook.sheets || [];
        if (!sheets.length) {
            return;
        }
        sheets.forEach(function (sheet, index) {
            var button = document.createElement("button");
            button.type = "button";
            button.className = "gs-tab" + (index === activeSheet ? " active" : "");
            button.textContent = sheet.name || ("Sheet" + (index + 1));
            button.addEventListener("click", function () {
                activeSheet = index;
                selected = { row: 0, col: 0 };
                renderTabs();
                renderSheet(activeSheet);
            });
            tabs.appendChild(button);
        });
        if (workbook.truncated) {
            var note = document.createElement("div");
            note.className = "gs-note";
            note.textContent = "แสดงไม่เกิน " + workbook.maxRows + " แถว และ " +
                workbook.maxCols + " คอลัมน์";
            tabs.appendChild(note);
        }
    }

    document.addEventListener("keydown", function (event) {
        var sheets = workbook.sheets || [];
        if (!sheets.length || workbook.error) {
            return;
        }
        var size = sheetSize(sheets[activeSheet]);
        var next = { row: selected.row, col: selected.col };
        if (event.key === "ArrowDown") {
            next.row = Math.min(size.rowCount - 1, selected.row + 1);
        } else if (event.key === "ArrowUp") {
            next.row = Math.max(0, selected.row - 1);
        } else if (event.key === "ArrowRight") {
            next.col = Math.min(size.colCount - 1, selected.col + 1);
        } else if (event.key === "ArrowLeft") {
            next.col = Math.max(0, selected.col - 1);
        } else {
            return;
        }
        event.preventDefault();
        selected = next;
        renderSheet(activeSheet);
        var selectedCell = grid.querySelector(".gs-selected");
        if (selectedCell && selectedCell.scrollIntoView) {
            selectedCell.scrollIntoView({ block: "nearest", inline: "nearest" });
        }
    });

    renderTabs();
    renderSheet(activeSheet);
}());
