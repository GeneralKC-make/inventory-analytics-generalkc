# Inventory Stock Analytics

@Author: Vaishanth Srinivasan
@Date: 19/06/2024
@Version: 1.0
@License: Apache 2.0
DESCRIPTION:
This script analyzes inventory data using FIFO (First In, First Out) methodology to calculate
shelf time, aging analysis, and stock movement patterns. It processes inventory transactions
and generates comprehensive analytics reports.

USAGE:

    python individual_stock.py <csv_file_path>
    
    Example:
    python individual_stock.py inventory_data.csv
    
INPUT FILE FORMAT:
The CSV file should contain the following columns:
- Date: Transaction date (format: "DD MMM YYYY, HH:MM AM/PM")
- Primary SKU: Product identifier
- Location: Storage location
- Qty.: Quantity (positive for inbound, negative for outbound)
- Cost: Transaction cost
- Adj. reason: Adjustment reason

OUTPUT FILES (Generated automatically in working directory):
- detailed_shelf_aging.csv: Current stock aging analysis
- shelf_time_analysis.csv: Historical shelf time data (if available)
- current_stock_summary.csv: Summary of current stock levels
- aging_categories_summary.csv: Stock categorized by age groups

NOTES:
- Uses FIFO logic for stock rotation analysis
- Handles missing historical data gracefully
- Generates comprehensive aging reports
- All output files are saved in the current working directory
