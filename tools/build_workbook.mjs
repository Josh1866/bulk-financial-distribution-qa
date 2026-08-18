import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = process.cwd();
const outDir = path.join(root, "outputs", "4fe07373286f");

function parseCsv(text) {
  const rows = []; let row = [], cell = "", quoted = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i], next = text[i + 1];
    if (ch === '"' && quoted && next === '"') { cell += '"'; i++; }
    else if (ch === '"') quoted = !quoted;
    else if (ch === ',' && !quoted) { row.push(cell); cell = ""; }
    else if ((ch === '\n' || ch === '\r') && !quoted) {
      if (ch === '\r' && next === '\n') i++;
      row.push(cell); if (row.some(v => v !== "")) rows.push(row); row = []; cell = "";
    } else cell += ch;
  }
  if (cell || row.length) { row.push(cell); rows.push(row); }
  return rows;
}

const details = parseCsv(await fs.readFile(path.join(root, "reports/generated/discrepancy_details.csv"), "utf8"));
const source = parseCsv(await fs.readFile(path.join(root, "data/source_calculations.csv"), "utf8"));
const output = parseCsv(await fs.readFile(path.join(root, "data/distribution_output.csv"), "utf8"));
const workbook = Workbook.create();
const summary = workbook.worksheets.add("Summary");
const detailSheet = workbook.worksheets.add("Affected Records");
const sourceSheet = workbook.worksheets.add("Source Data");
const outputSheet = workbook.worksheets.add("Distribution Output");
const checks = workbook.worksheets.add("Checks");
workbook.comments.setSelf({ displayName: "Joshua Kinnear" });

const navy = "#17365D", blue = "#D9EAF7", pale = "#F3F6F9", red = "#FCE4E4", green = "#E2F0D9", gold = "#FFF2CC";
function title(sheet, range, text) {
  range.merge(); range.values = [[text]];
  range.format.fill = navy; range.format.font = { bold: true, color: "#FFFFFF", size: 16 };
  range.format.rowHeight = 30; range.format.verticalAlignment = "center";
}
function header(range) {
  range.format.fill = navy; range.format.font = { bold: true, color: "#FFFFFF" };
  range.format.wrapText = true; range.format.borders = { preset: "inside", style: "thin", color: "#B4C6E7" };
}
function finish(sheet) { sheet.showGridLines = false; sheet.freezePanes.freezeRows(3); }

title(summary, summary.getRange("A1:D1"), "Bulk Distribution QA — Discrepancy Summary");
summary.getRange("A2:D2").merge(); summary.getRange("A2:D2").values = [["Cent-accurate reconciliation | Sample batch | 5 affected clients"]];
summary.getRange("A4:C4").values = [["Discrepancy Type", "Count", "Affected Clients"]]; header(summary.getRange("A4:C4"));
const types = ["Calculation / business-rule error", "Duplicate distribution record", "Missing distribution record", "Rounding / amount mismatch", "Unexpected / orphan output"];
summary.getRange("A5:A9").values = types.map(x => [x]);
summary.getRange("B5").formulas = [["=COUNTIF('Affected Records'!$A$4:$A$8,A5)"]]; summary.getRange("B5:B9").fillDown();
summary.getRange("C5:C9").values = [["C011"], ["C007"], ["C005"], ["C002"], ["C013"]];
summary.getRange("A10:C10").values = [["TOTAL", null, "C002, C005, C007, C011, C013"]];
summary.getRange("B10").formulas = [["=SUM(B5:B9)"]];
summary.getRange("A10:C10").format.fill = blue; summary.getRange("A10:C10").format.font = { bold: true, color: "#000000" };
summary.getRange("A4:C10").format.borders = { preset: "outside", style: "thin", color: "#8096B0" };
summary.getRange("A12:D12").merge(); summary.getRange("A12:D12").values = [["Review note: each category is counted once per affected client. See Affected Records for amounts, variance, row counts, and evidence."]];
summary.getRange("A12:D12").format.fill = gold; summary.getRange("A12:D12").format.wrapText = true; summary.getRange("A12:D12").format.rowHeight = 34;
summary.getRange("A:A").format.columnWidth = 36; summary.getRange("B:B").format.columnWidth = 12; summary.getRange("C:C").format.columnWidth = 34; summary.getRange("D:D").format.columnWidth = 3; finish(summary);

title(detailSheet, detailSheet.getRange("A1:I1"), "Affected Client Records");
detailSheet.getRange("A3:I8").values = details.map((row, i) => row.map((v, j) => i === 0 ? ["Discrepancy Type", "Client ID", "Client Name", "Expected Amount", "Distributed Amount", "Variance", "Source Rows", "Output Rows", "Evidence"][j] : ([3,4,5,6,7].includes(j) && v !== "" ? Number(v) : v)));
header(detailSheet.getRange("A3:I3"));
detailSheet.tables.add("A3:I8", true, "AffectedRecordsTable").style = "TableStyleMedium2";
detailSheet.getRange("D4:F8").format.numberFormat = [["$#,##0.00;[Red]($#,##0.00);-"],["$#,##0.00;[Red]($#,##0.00);-"],["$#,##0.00;[Red]($#,##0.00);-"],["$#,##0.00;[Red]($#,##0.00);-"],["$#,##0.00;[Red]($#,##0.00);-"]];
detailSheet.getRange("A:A").format.columnWidth = 34; detailSheet.getRange("B:B").format.columnWidth = 12; detailSheet.getRange("C:C").format.columnWidth = 15; detailSheet.getRange("D:F").format.columnWidth = 18; detailSheet.getRange("G:H").format.columnWidth = 15; detailSheet.getRange("I:I").format.columnWidth = 58; detailSheet.getRange("I4:I8").format.wrapText = true; finish(detailSheet);

function dataTab(sheet, titleText, rows, tableName, amountCols, pctCols=[]) {
  title(sheet, sheet.getRangeByIndexes(0, 0, 1, rows[0].length), titleText);
  const converted = rows.map((r, i) => r.map((v, j) => i > 0 && (amountCols.includes(j) || pctCols.includes(j)) ? Number(v) : v));
  sheet.getRangeByIndexes(2, 0, converted.length, converted[0].length).values = converted;
  header(sheet.getRangeByIndexes(2, 0, 1, converted[0].length));
  sheet.tables.add(`A3:${String.fromCharCode(64 + converted[0].length)}${converted.length + 2}`, true, tableName).style = "TableStyleMedium2";
  for (const col of amountCols) sheet.getRangeByIndexes(3, col, converted.length - 1, 1).format.numberFormat = Array(converted.length - 1).fill(["$#,##0.00;[Red]($#,##0.00);-"]);
  for (const col of pctCols) sheet.getRangeByIndexes(3, col, converted.length - 1, 1).format.numberFormat = Array(converted.length - 1).fill(["0.00\"%\""]);
  sheet.getUsedRange().format.autofitColumns();
  for (let c = 0; c < converted[0].length; c++) if (sheet.getRangeByIndexes(0,c,converted.length+2,1).format.columnWidth > 24) sheet.getRangeByIndexes(0,c,converted.length+2,1).format.columnWidth = 24;
  finish(sheet);
}
dataTab(sourceSheet, "Source Calculation Data (Read-only fixture)", source, "SourceDataTable", [2,4], [3]);
dataTab(outputSheet, "Distribution Output Data (Read-only fixture)", output, "DistributionOutputTable", [2]);

title(checks, checks.getRange("A1:F1"), "Workbook Control Checks");
checks.getRange("A3:F3").values = [["Check", "Actual", "Expected", "Difference", "Tolerance", "Status"]]; header(checks.getRange("A3:F3"));
checks.getRange("A4:A6").values = [["Detail discrepancy rows"], ["Summary discrepancy count"], ["Affected client IDs populated"]];
checks.getRange("B4:B6").formulas = [["=COUNTA('Affected Records'!B4:B8)"], ["='Summary'!B10"], ["=COUNTA('Affected Records'!B4:B8)"]];
checks.getRange("C4:C6").values = [[5], [5], [5]]; checks.getRange("D4").formulas = [["=B4-C4"]]; checks.getRange("D4:D6").fillDown(); checks.getRange("E4:E6").values = [[0],[0],[0]];
checks.getRange("F4").formulas = [["=IF(ABS(D4)<=E4,\"OK\",\"FAIL\")"]]; checks.getRange("F4:F6").fillDown();
checks.getRange("F4:F6").conditionalFormats.add("containsText", { text: "OK", format: { fill: green, font: { bold: true, color: "#006100" } } });
checks.getRange("F4:F6").conditionalFormats.add("containsText", { text: "FAIL", format: { fill: red, font: { bold: true, color: "#9C0006" } } });
checks.getRange("A3:F6").format.borders = { preset: "outside", style: "thin", color: "#8096B0" }; checks.getRange("A:A").format.columnWidth = 32; checks.getRange("B:F").format.columnWidth = 14; finish(checks);

for (const sheet of [summary, detailSheet, sourceSheet, outputSheet, checks]) sheet.getUsedRange().format.font = { name: "Aptos", size: 10 };
summary.getRange("A1:D1").format.font = { name: "Aptos Display", size: 16, bold: true, color: "#FFFFFF" };

console.log((await workbook.inspect({kind:"table", range:"Summary!A1:D12", include:"values,formulas", tableMaxRows:20, tableMaxCols:10})).ndjson);
console.log((await workbook.inspect({kind:"match", searchTerm:"#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options:{useRegex:true,maxResults:100}, summary:"formula error scan"})).ndjson);
await fs.mkdir(outDir, { recursive: true });
for (const sheetName of ["Summary", "Affected Records", "Source Data", "Distribution Output", "Checks"]) {
  const preview = await workbook.render({ sheetName, autoCrop: "all", scale: 1.2, format: "png" });
  await fs.writeFile(path.join(outDir, `preview-${sheetName.replaceAll(" ", "-").toLowerCase()}.png`), new Uint8Array(await preview.arrayBuffer()));
}
const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(path.join(outDir, "discrepancy_summary.xlsx"));
