import openpyxl
import os

file_path = 'msp_export.xlsx'

if not os.path.exists(file_path):
    print(f"❌ Error: Could not find '{file_path}' in current folder!")
else:
    # 1. Load Workbook and Sheet
    wb = openpyxl.load_workbook(file_path)
    sheet = wb.active

    headers = [cell.value for cell in sheet[1]]
    
    # Helper function to support column names with spaces or underscores
    def get_col_idx(*col_names):
        for name in col_names:
            if name in headers:
                return headers.index(name)
        return None

    id_idx = get_col_idx('ID', 'id')
    baseline_cost_idx = get_col_idx('Baseline Cost', 'Baseline_Cost')
    actual_cost_idx = get_col_idx('Actual Cost', 'Actual_Cost')
    percent_comp_idx = get_col_idx('% Complete', 'Percent_Complete', '%_Complete')

    # Remove existing calculated EVM columns if present
    clean_headers = [h for h in headers if h not in ['PV ($)', 'EV ($)', 'AC ($)', 'CV ($)', 'SV ($)', 'CPI', 'SPI']]
    
    new_headers = clean_headers + ['PV ($)', 'EV ($)', 'AC ($)', 'CV ($)', 'SV ($)', 'CPI', 'SPI']
    processed_data = [new_headers]

    # Clean numeric values from string formatting
    def parse_number(val):
        if val is None:
            return 0.0
        s = str(val).replace('$', '').replace(',', '').strip()
        try:
            return float(s)
        except ValueError:
            return 0.0

    # 2. Iterate through task rows and calculate EVM metrics
    for row in sheet.iter_rows(min_row=2, values_only=True):
        if id_idx is not None and row[id_idx] is None:
            continue

        row_list = [row[headers.index(h)] for h in clean_headers]

        b_cost = parse_number(row[baseline_cost_idx]) if baseline_cost_idx is not None else 0.0
        a_cost = parse_number(row[actual_cost_idx]) if actual_cost_idx is not None else 0.0
        p_comp = parse_number(row[percent_comp_idx]) if percent_comp_idx is not None else 0.0

        # Convert ratio to percentage if stored as decimal (e.g., 0.88 -> 88.0)
        if 0 < p_comp <= 1.0:
            p_comp = p_comp * 100.0

        # Core EVM Calculations
        pv = b_cost
        ev = b_cost * (p_comp / 100.0)
        ac = a_cost
        cv = ev - ac
        sv = ev - pv
        cpi = round(ev / ac, 2) if ac > 0 else 1.0
        spi = round(ev / pv, 2) if pv > 0 else 1.0

        row_list.extend([pv, ev, ac, cv, sv, cpi, spi])
        processed_data.append(row_list)

    # 3. Export processed EVM metrics to a new Excel workbook
    new_wb = openpyxl.Workbook()
    new_sheet = new_wb.active
    new_sheet.title = "EVM Data"

    for r in processed_data:
        new_sheet.append(r)

    output_path = 'evm_processed_data.xlsx'
    new_wb.save(output_path)

    print("✅ Data processing completed successfully with corrected columns!")