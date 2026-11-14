"""
Excel Automation Builder for Field Engineering Reports
Supports professional styling, auto-sum formulas, conditional formatting,
and auto-fitting column widths.
"""

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

class EngineeringExcelBuilder:
    def __init__(self, title="Engineering Report"):
        self.wb = Workbook()
        # Remove default sheet
        self.wb.remove(self.wb.active)
        self.title = title

        # Styling constants
        self.header_font = Font(name="맑은 고딕", size=11, bold=True, color="FFFFFF")
        self.header_fill = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid") # Navy
        self.sub_header_fill = PatternFill(start_color="2C5E8A", end_color="2C5E8A", fill_type="solid") # Steel Blue
        self.section_fill = PatternFill(start_color="E6EEF8", end_color="E6EEF8", fill_type="solid") # Light Blue Tint
        
        self.data_font = Font(name="맑은 고딕", size=10, bold=False, color="1F2937")
        self.total_font = Font(name="맑은 고딕", size=10, bold=True, color="111827")
        self.title_font = Font(name="맑은 고딕", size=16, bold=True, color="1B365D")
        self.sub_title_font = Font(name="맑은 고딕", size=10, italic=True, color="4B5563")

        self.thin_border_side = Side(border_style="thin", color="D1D5DB")
        self.thick_bottom_side = Side(border_style="medium", color="1B365D")
        self.double_bottom_side = Side(border_style="double", color="1B365D")

        self.cell_border = Border(
            left=self.thin_border_side,
            right=self.thin_border_side,
            top=self.thin_border_side,
            bottom=self.thin_border_side
        )

        self.total_border = Border(
            top=self.thin_border_side,
            bottom=self.double_bottom_side,
            left=self.thin_border_side,
            right=self.thin_border_side
        )

    def add_sheet(self, sheet_name):
        return self.wb.create_sheet(title=sheet_name)

    def build_styled_table(self, ws, start_row, headers, data, alignments=None, number_formats=None, add_total=True, sum_cols=None, title=None, sub_title=None):
        """
        Populate a styled table in the given worksheet.
        - headers: list of str
        - data: list of lists
        - alignments: list of 'left', 'center', 'right'
        - number_formats: dict of col_idx (0-based) -> format string (e.g. '#,##0.00')
        - sum_cols: list of col_idx (0-based) to apply SUM formula
        """
        curr_row = start_row

        if title:
            ws.cell(row=curr_row, column=1, value=title).font = self.title_font
            curr_row += 1
        if sub_title:
            ws.cell(row=curr_row, column=1, value=sub_title).font = self.sub_title_font
            curr_row += 1
        if title or sub_title:
            curr_row += 1  # Add blank line

        header_row_idx = curr_row
        ws.row_dimensions[header_row_idx].height = 28

        # Write Headers
        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=header_row_idx, column=col_idx, value=header)
            cell.font = self.header_font
            cell.fill = self.header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = self.cell_border

        curr_row += 1
        data_start_row = curr_row

        # Write Data
        for row_data in data:
            ws.row_dimensions[curr_row].height = 20
            # Zebra striping
            row_fill = PatternFill(start_color="F9FAFB" if curr_row % 2 == 0 else "FFFFFF", fill_type="solid")

            for col_idx, val in enumerate(row_data, start=1):
                cell = ws.cell(row=curr_row, column=col_idx, value=val)
                cell.font = self.data_font
                cell.fill = row_fill
                cell.border = self.cell_border

                align = "center"
                if alignments and col_idx - 1 < len(alignments):
                    align = alignments[col_idx - 1]
                cell.alignment = Alignment(horizontal=align, vertical="center")

                # Format numbers
                if number_formats and (col_idx - 1) in number_formats:
                    cell.number_format = number_formats[col_idx - 1]

            curr_row += 1

        data_end_row = curr_row - 1

        # Add Total Row if requested
        if add_total and sum_cols and len(data) > 0:
            ws.row_dimensions[curr_row].height = 24
            # First column: "합계 (Total)"
            tot_cell = ws.cell(row=curr_row, column=1, value="합계 (Total)")
            tot_cell.font = self.total_font
            tot_cell.fill = self.section_fill
            tot_cell.alignment = Alignment(horizontal="center", vertical="center")
            tot_cell.border = self.total_border

            for col_idx in range(2, len(headers) + 1):
                c = ws.cell(row=curr_row, column=col_idx)
                c.fill = self.section_fill
                c.border = self.total_border
                c.font = self.total_font

                if (col_idx - 1) in sum_cols:
                    col_letter = get_column_letter(col_idx)
                    c.value = f"=SUM({col_letter}{data_start_row}:{col_letter}{data_end_row})"
                    align = "right" if alignments and alignments[col_idx - 1] == "right" else "center"
                    c.alignment = Alignment(horizontal=align, vertical="center")
                    if number_formats and (col_idx - 1) in number_formats:
                        c.number_format = number_formats[col_idx - 1]
                else:
                    c.value = "-"
                    c.alignment = Alignment(horizontal="center", vertical="center")
            curr_row += 1

        # Auto-adjust column widths
        for col_idx in range(1, len(headers) + 1):
            col_letter = get_column_letter(col_idx)
            max_len = 0
            for row in range(header_row_idx, curr_row):
                cell_val = str(ws.cell(row=row, column=col_idx).value or "")
                # Korean characters take approx 2 width units
                char_len = sum(2 if ord(ch) > 127 else 1 for ch in cell_val)
                if char_len > max_len:
                    max_len = char_len
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

        return curr_row

    def save(self, filepath):
        self.wb.save(filepath)
        return filepath
