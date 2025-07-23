#!/usr/bin/env python3

#Inventory Stock Analytics

#@Author: Vaishanth Srinivasan
#@Date: 19/06/2024
#@Version: 1.0
#@License: Apache 2.0
#DESCRIPTION:
#This script analyzes inventory data using FIFO (First In, First Out) methodology to calculate
#shelf time, aging analysis, and stock movement patterns. It processes inventory transactions
#and generates comprehensive analytics reports.

#USAGE:
#    To be run in command prompt --> win + r -> cmd
#    On command prompt, change directory to where the python file and csv is stored using 'cd'
#    example: PS C:\Users\FCI> cd '.\Desktop\Blown Inventory\Stock analytics'
#    
#    THEN RUN USING:

#    python individual_stock.py <csv_file_path>
    
#    Example:
#    python individual_stock.py inventory_data.csv
    
#INPUT FILE FORMAT:
#The CSV file should contain the following columns:
#- Date: Transaction date (format: "DD MMM YYYY, HH:MM AM/PM")
#- Primary SKU: Product identifier
#- Location: Storage location
#- Qty.: Quantity (positive for inbound, negative for outbound)
#- Cost: Transaction cost
#- Adj. reason: Adjustment reason

#OUTPUT FILES (Generated automatically in working directory):
#- detailed_shelf_aging.csv: Current stock aging analysis
#- shelf_time_analysis.csv: Historical shelf time data (if available)
#- current_stock_summary.csv: Summary of current stock levels
#- aging_categories_summary.csv: Stock categorized by age groups

#REQUIREMENTS:
#- pandas
#- numpy
#- Python 3.6+

#HOW TO INSTALL REQUIREMENTS:
#Download and install python: https://www.python.org/downloads/
#On command prompt, 'pip install pandas numpy'

#NOTES:
#- Uses FIFO logic for stock rotation analysis
#- Handles missing historical data gracefully
#- Generates comprehensive aging reports
#- All output files are saved in the current working directory


import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict, deque
import csv
import sys
import argparse
import os

class InventoryAnalyzer:
    def __init__(self, csv_file_path):
        """
        Initialize the inventory analyzer with CSV data
        """
        self.df = pd.read_csv(csv_file_path)
        self.prepare_data()
        self.shelf_time_records = []
        self.current_stock = defaultdict(lambda: defaultdict(deque))  # {product: {location: deque of (date, qty, cost)}}
        
    def prepare_data(self):
        """
        Clean and prepare the data for analysis
        """
        # Convert date string to datetime
        self.df['DateTime'] = pd.to_datetime(self.df['Date'], format='mixed')
        
        # Sort by datetime to ensure chronological processing
        self.df = self.df.sort_values('DateTime').reset_index(drop=True)
        
        # Clean column names (remove spaces and special characters)
        self.df.columns = self.df.columns.str.strip()
        
        print(f"Loaded {len(self.df)} transactions")
        print(f"Date range: {self.df['DateTime'].min()} to {self.df['DateTime'].max()}")
        
    def process_inventory_movements(self):
        """
        Process all inventory movements using FIFO logic
        """
        print("Processing inventory movements with FIFO logic...")
        
        for idx, row in self.df.iterrows():
            product = row['Primary SKU']
            location = row['Location']
            qty = row['Qty.']
            date = row['DateTime']
            cost = abs(row['Cost']) if pd.notna(row['Cost']) else 0
            adj_reason = row['Adj. reason']
            
            if qty > 0:
                # Stock coming in
                self._add_stock(product, location, date, qty, cost, adj_reason)
            elif qty < 0:
                # Stock going out
                self._remove_stock(product, location, date, abs(qty), adj_reason)
                
    def _add_stock(self, product, location, date, qty, cost, reason):
        """
        Add stock to inventory (FIFO queue)
        """
        # Add individual units to maintain granular tracking
        unit_cost = cost / qty if qty > 0 else 0
        
        for _ in range(qty):
            self.current_stock[product][location].append({
                'date': date,
                'cost': unit_cost,
                'reason': reason
            })
            
    def _remove_stock(self, product, location, date, qty, reason):
        """
        Remove stock from inventory using FIFO logic and calculate shelf time
        """
        removed_qty = 0
        
        while removed_qty < qty and self.current_stock[product][location]:
            # Get the oldest stock (FIFO)
            oldest_stock = self.current_stock[product][location].popleft()
            
            # Calculate shelf time
            shelf_time_days = (date - oldest_stock['date']).days
            
            # Record the shelf time
            self.shelf_time_records.append({
                'product': product,
                'location': location,
                'purchase_date': oldest_stock['date'],
                'sale_date': date,
                'shelf_time_days': shelf_time_days,
                'unit_cost': oldest_stock['cost'],
                'purchase_reason': oldest_stock['reason'],
                'sale_reason': reason
            })
            
            removed_qty += 1
            
        if removed_qty < qty:
            print(f"Warning: Tried to remove {qty} units of {product} at {location}, but only {removed_qty} were available")
    
    def generate_analytics(self):
        """
        Generate comprehensive analytics from shelf time data
        """
        if not self.shelf_time_records:
            print("No shelf time records found.")
            print("This likely means sales are occurring before purchases in your dataset.")
            print("You may need historical purchase data or starting inventory levels.")
            
            # Return empty analytics structure instead of None
            return {
                'overall': {
                    'total_units_sold': 0,
                    'average_shelf_time_days': 0,
                    'median_shelf_time_days': 0,
                    'min_shelf_time_days': 0,
                    'max_shelf_time_days': 0,
                    'std_shelf_time_days': 0
                },
                'by_product': pd.DataFrame(),
                'by_location': pd.DataFrame(),
                'fast_moving_products': pd.Series(dtype=float),
                'slow_moving_products': pd.Series(dtype=float),
                'monthly_trends': pd.DataFrame()
            }, pd.DataFrame()
            
        shelf_df = pd.DataFrame(self.shelf_time_records)
        
        analytics = {}
        
        # Overall statistics
        analytics['overall'] = {
            'total_units_sold': len(shelf_df),
            'average_shelf_time_days': shelf_df['shelf_time_days'].mean(),
            'median_shelf_time_days': shelf_df['shelf_time_days'].median(),
            'min_shelf_time_days': shelf_df['shelf_time_days'].min(),
            'max_shelf_time_days': shelf_df['shelf_time_days'].max(),
            'std_shelf_time_days': shelf_df['shelf_time_days'].std()
        }
        
        # By product analysis
        analytics['by_product'] = shelf_df.groupby('product').agg({
            'shelf_time_days': ['count', 'mean', 'median', 'min', 'max', 'std'],
            'unit_cost': 'mean'
        }).round(2)
        
        # By location analysis
        analytics['by_location'] = shelf_df.groupby('location').agg({
            'shelf_time_days': ['count', 'mean', 'median', 'min', 'max', 'std'],
            'unit_cost': 'mean'
        }).round(2)
        
        # Fast vs slow moving products
        product_avg_shelf_time = shelf_df.groupby('product')['shelf_time_days'].mean().sort_values()
        analytics['fast_moving_products'] = product_avg_shelf_time.head(10)
        analytics['slow_moving_products'] = product_avg_shelf_time.tail(10)
        
        # Monthly trends
        shelf_df['sale_month'] = shelf_df['sale_date'].dt.to_period('M')
        analytics['monthly_trends'] = shelf_df.groupby('sale_month').agg({
            'shelf_time_days': ['count', 'mean'],
            'unit_cost': 'sum'
        }).round(2)
        
        return analytics, shelf_df
    
    def get_current_stock_summary(self):
        """
        Get summary of current stock on hand
        """
        current_stock_summary = []
        
        for product in self.current_stock:
            for location in self.current_stock[product]:
                stock_queue = self.current_stock[product][location]
                if stock_queue:  # If there's stock remaining
                    qty = len(stock_queue)
                    oldest_date = min(item['date'] for item in stock_queue)
                    newest_date = max(item['date'] for item in stock_queue)
                    total_cost = sum(item['cost'] for item in stock_queue)
                    avg_cost = total_cost / qty if qty > 0 else 0
                    
                    # Calculate how long the oldest stock has been sitting
                    days_on_shelf = (datetime.now() - oldest_date).days
                    
                    current_stock_summary.append({
                        'product': product,
                        'location': location,
                        'current_qty': qty,
                        'oldest_stock_date': oldest_date,
                        'newest_stock_date': newest_date,
                        'days_on_shelf_oldest': days_on_shelf,
                        'total_cost': total_cost,
                        'avg_cost_per_unit': avg_cost
                    })
        
        return pd.DataFrame(current_stock_summary)
    
    def add_opening_stock(self, opening_stock_data):
        """
        Add opening stock data to initialize inventory before processing transactions
        opening_stock_data should be a list of dictionaries with keys:
        ['product', 'location', 'qty', 'date', 'cost_per_unit']
        """
        print("Adding opening stock data...")
        
        for stock_item in opening_stock_data:
            product = stock_item['product']
            location = stock_item['location']
            qty = stock_item['qty']
            date = pd.to_datetime(stock_item['date'])
            cost = stock_item.get('cost_per_unit', 0)
            
            self._add_stock(product, location, date, qty, cost * qty, "Opening Stock")
            
        print(f"Added opening stock for {len(opening_stock_data)} items")
        
    def print_analytics_report(self, analytics):
        """
        Print a formatted analytics report
        """
        print("INVENTORY ANALYTICS REPORT")
        print("="*60)
        
        # Overall statistics
        print("\nOVERALL STATISTICS:")
        print(f"Total units sold: {analytics['overall']['total_units_sold']:,}")
        print(f"Average shelf time: {analytics['overall']['average_shelf_time_days']:.1f} days")
        print(f"Median shelf time: {analytics['overall']['median_shelf_time_days']:.1f} days")
        print(f"Min shelf time: {analytics['overall']['min_shelf_time_days']} days")
        print(f"Max shelf time: {analytics['overall']['max_shelf_time_days']} days")
        print(f"Standard deviation: {analytics['overall']['std_shelf_time_days']:.1f} days")
        
        # Fast moving products
        print("\nTOP 5 FAST MOVING PRODUCTS (by avg shelf time):")
        for product, days in analytics['fast_moving_products'].head().items():
            print(f"  {product}: {days:.1f} days")
        
        # Slow moving products
        print("\nTOP 5 SLOW MOVING PRODUCTS (by avg shelf time):")
        for product, days in analytics['slow_moving_products'].tail().items():
            print(f"  {product}: {days:.1f} days")
        
        print("\n" + "="*60)
    
    def create_summary_report(self):
        """
        Create a summary report of all transactions and current stock
        """
        print("\n" + "="*60)
        print("TRANSACTION SUMMARY REPORT")
        print("="*60)
        
        # Transaction summary
        purchases = self.df[self.df['Qty.'] > 0]
        sales = self.df[self.df['Qty.'] < 0]
        
        print(f"\nTRANSACTION OVERVIEW:")
        print(f"Total transactions: {len(self.df)}")
        print(f"Purchase transactions: {len(purchases)} (Total qty: {purchases['Qty.'].sum()})")
        print(f"Sale transactions: {len(sales)} (Total qty: {abs(sales['Qty.'].sum())})")
        
        # Product summary
        print(f"\nPRODUCT SUMMARY:")
        product_summary = self.df.groupby('Primary SKU').agg({
            'Qty.': 'sum',
            'Cost': lambda x: x[x > 0].sum()  # Only positive costs (purchases)
        }).round(2)
        
        print(product_summary)
        
        # Location summary
        print(f"\nLOCATION SUMMARY:")
        location_summary = self.df.groupby('Location').agg({
            'Qty.': 'sum',
            'Cost': lambda x: x[x > 0].sum()
        }).round(2)
        
        print(location_summary)
        
    def get_detailed_shelf_aging_report(self):
        """
        Get detailed report of how long each product has been sitting on shelf at each location
        """
        current_date = datetime.now()
        shelf_aging_report = []
        
        print("\n" + "="*80)
        print("DETAILED SHELF AGING REPORT")
        print("="*80)
        print(f"Analysis as of: {current_date.strftime('%Y-%m-%d %H:%M')}")
        print("="*80)
        
        for product in self.current_stock:
            for location in self.current_stock[product]:
                stock_queue = self.current_stock[product][location]
                if stock_queue:  # If there's stock remaining
                    
                    print(f"\nPRODUCT: {product}")
                    print(f"LOCATION: {location}")
                    print("-" * 60)
                    
                    # Analyze each unit in the queue (FIFO order)
                    total_units = len(stock_queue)
                    total_days_aging = 0
                    
                    for i, stock_item in enumerate(stock_queue, 1):
                        purchase_date = stock_item['date']
                        days_on_shelf = (current_date - purchase_date).days
                        total_days_aging += days_on_shelf
                        
                        print(f"  Unit {i:2d}: Purchased on {purchase_date.strftime('%Y-%m-%d %H:%M')} "
                              f"→ {days_on_shelf:3d} days on shelf (₹{stock_item['cost']:.0f})")
                        
                        # Add to detailed report
                        shelf_aging_report.append({
                            'product': product,
                            'location': location,
                            'unit_number': i,
                            'purchase_date': purchase_date,
                            'days_on_shelf': days_on_shelf,
                            'unit_cost': stock_item['cost'],
                            'purchase_reason': stock_item['reason']
                        })
                    
                    avg_days_on_shelf = total_days_aging / total_units
                    oldest_days = max((current_date - item['date']).days for item in stock_queue)
                    newest_days = min((current_date - item['date']).days for item in stock_queue)
                    total_value = sum(item['cost'] for item in stock_queue)
                    
                    print(f"  {'='*58}")
                    print(f"  SUMMARY - Total Units: {total_units}, Total Value: ₹{total_value:.0f}")
                    print(f"  Average days on shelf: {avg_days_on_shelf:.1f} days")
                    print(f"  Oldest stock: {oldest_days} days, Newest stock: {newest_days} days")
        
        return pd.DataFrame(shelf_aging_report)
    
    def get_aging_summary_by_categories(self):
        """
        Categorize stock by aging periods
        """
        current_date = datetime.now()
        aging_categories = {
            'Fresh (0-7 days)': [],
            'Medium (8-30 days)': [],
            'Aged (31-90 days)': [],
            'Very Aged (90+ days)': []
        }
        
        for product in self.current_stock:
            for location in self.current_stock[product]:
                stock_queue = self.current_stock[product][location]
                for stock_item in stock_queue:
                    days_on_shelf = (current_date - stock_item['date']).days
                    
                    item_info = {
                        'product': product,
                        'location': location,
                        'days_on_shelf': days_on_shelf,
                        'cost': stock_item['cost'],
                        'purchase_date': stock_item['date']
                    }
                    
                    if days_on_shelf <= 7:
                        aging_categories['Fresh (0-7 days)'].append(item_info)
                    elif days_on_shelf <= 30:
                        aging_categories['Medium (8-30 days)'].append(item_info)
                    elif days_on_shelf <= 90:
                        aging_categories['Aged (31-90 days)'].append(item_info)
                    else:
                        aging_categories['Very Aged (90+ days)'].append(item_info)
        
        return aging_categories
    
    def print_aging_summary(self, aging_categories):
        """
        Print summary of aging categories
        """
        print("\n" + "="*60)
        print("STOCK AGING CATEGORY SUMMARY")
        print("="*60)
        
        for category, items in aging_categories.items():
            total_units = len(items)
            total_value = sum(item['cost'] for item in items)
            print(f"\n{category}:")
            print(f"  Units: {total_units}")
            print(f"  Total Value: ₹{total_value:.2f}")
            if total_units > 0:
                avg_days = sum(item['days_on_shelf'] for item in items) / total_units
                print(f"  Average Days on Shelf: {avg_days:.1f}")
    
    def save_all_reports_to_csv(self):
        """
        Save all analysis reports to CSV files in the working directory
        """
        print("\n" + "="*60)
        print("SAVING REPORTS TO CSV FILES")
        print("="*60)
        
        # Get current working directory
        current_dir = os.getcwd()
        
        # 1. Save detailed shelf aging report
        shelf_aging_df = self.get_detailed_shelf_aging_report()
        if not shelf_aging_df.empty:
            aging_file = os.path.join(current_dir, 'detailed_shelf_aging.csv')
            shelf_aging_df.to_csv(aging_file, index=False)
            print(f"✓ Detailed shelf aging report saved: {aging_file}")
        
        # 2. Save current stock summary
        current_stock_df = self.get_current_stock_summary()
        if not current_stock_df.empty:
            stock_file = os.path.join(current_dir, 'current_stock_summary.csv')
            current_stock_df.to_csv(stock_file, index=False)
            print(f"✓ Current stock summary saved: {stock_file}")
        
        # 3. Save aging categories summary
        aging_categories = self.get_aging_summary_by_categories()
        aging_summary_data = []
        
        for category, items in aging_categories.items():
            for item in items:
                aging_summary_data.append({
                    'category': category,
                    'product': item['product'],
                    'location': item['location'],
                    'days_on_shelf': item['days_on_shelf'],
                    'cost': item['cost'],
                    'purchase_date': item['purchase_date']
                })
        
        if aging_summary_data:
            aging_summary_df = pd.DataFrame(aging_summary_data)
            aging_categories_file = os.path.join(current_dir, 'aging_categories_summary.csv')
            aging_summary_df.to_csv(aging_categories_file, index=False)
            print(f"✓ Aging categories summary saved: {aging_categories_file}")
        
        # 4. Save shelf time analysis (if available)
        analytics, shelf_time_df = self.generate_analytics()
        if not shelf_time_df.empty:
            shelf_time_file = os.path.join(current_dir, 'shelf_time_analysis.csv')
            shelf_time_df.to_csv(shelf_time_file, index=False)
            print(f"✓ Shelf time analysis saved: {shelf_time_file}")
        
        # 5. Save transaction summary
        transaction_summary = []
        for idx, row in self.df.iterrows():
            transaction_summary.append({
                'date': row['DateTime'],
                'product': row['Primary SKU'],
                'location': row['Location'],
                'quantity': row['Qty.'],
                'cost': row['Cost'],
                'reason': row['Adj. reason'],
                'transaction_type': 'Purchase' if row['Qty.'] > 0 else 'Sale'
            })
        
        if transaction_summary:
            transaction_df = pd.DataFrame(transaction_summary)
            transaction_file = os.path.join(current_dir, 'transaction_summary.csv')
            transaction_df.to_csv(transaction_file, index=False)
            print(f"✓ Transaction summary saved: {transaction_file}")
        
        print(f"\nAll CSV files saved in: {current_dir}")
        return current_dir

def main():
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description='Inventory Stock Analytics with FIFO')
    parser.add_argument('csv_file', help='Path to the CSV file containing inventory data')
    
    # Parse command line arguments
    args = parser.parse_args()
    
    # Check if file exists and process the data
    try:
        print("="*80)
        print("INVENTORY ANALYTICS SYSTEM - FIFO ANALYSIS")
        print("="*80)
        
        # Initialize analyzer with the provided CSV file
        analyzer = InventoryAnalyzer(args.csv_file)
        
        # Process all inventory movements
        analyzer.process_inventory_movements()
        
        # Generate analytics
        analytics, shelf_time_df = analyzer.generate_analytics()
        
        # Create summary report
        analyzer.create_summary_report()
        
        # Print aging summary
        aging_categories = analyzer.get_aging_summary_by_categories()
        analyzer.print_aging_summary(aging_categories)
        
        if analytics and analytics['overall']['total_units_sold'] > 0:
            # Print analytics report only if we have shelf time data
            analyzer.print_analytics_report(analytics)
        
        # Save all reports to CSV files
        saved_location = analyzer.save_all_reports_to_csv()
        
        print("\n" + "="*80)
        print("ANALYSIS COMPLETE!")
        print("="*80)
        print(f"All results have been saved to CSV files in: {saved_location}")
        
        if analytics['overall']['total_units_sold'] == 0:
            print("\nNote: No shelf time analysis available - sales occurred before purchases in dataset.")
            print("Consider adding opening stock data or extending the dataset to include earlier purchases.")
        
        return analyzer, analytics, shelf_time_df
        
    except FileNotFoundError:
        print(f"Error: File '{args.csv_file}' not found.")
        print("Please check the file path and try again.")
        sys.exit(1)
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        sys.exit(1)
    
    return None

# Example usage
if __name__ == "__main__":
    # Run the analysis with command line arguments
    results = main()
    
    # Alternative usage if running directly in Python:
    # analyzer = InventoryAnalyzer('your_file.csv')
    # analyzer.process_inventory_movements()
    # analyzer.save_all_reports_to_csv()
