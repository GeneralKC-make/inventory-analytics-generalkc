#!/usr/bin/env python3
"""
Inventory Stock Analytics - Streamlit Web App

@Author: Vaishanth Srinivasan
@Date: 19/06/2024
@Version: 2.0 (Streamlit)
@License: Apache 2.0

DESCRIPTION:
This streamlit web app analyzes inventory data using FIFO (First In, First Out) methodology 
to calculate shelf time, aging analysis, and stock movement patterns.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from collections import defaultdict, deque
import io

# Set page config
st.set_page_config(
    page_title="Inventory Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

class InventoryAnalyzer:
    def __init__(self, df):
        """
        Initialize the inventory analyzer with DataFrame
        """
        self.df = df.copy()
        self.prepare_data()
        self.shelf_time_records = []
        self.current_stock = defaultdict(lambda: defaultdict(deque))
        
    def prepare_data(self):
        """
        Clean and prepare the data for analysis
        """
        # Convert date string to datetime
        self.df['DateTime'] = pd.to_datetime(self.df['Date'], format='%d %b %Y, %I:%M %p')
        
        # Sort by datetime to ensure chronological processing
        self.df = self.df.sort_values('DateTime').reset_index(drop=True)
        
        # Clean column names
        self.df.columns = self.df.columns.str.strip()
        
    def process_inventory_movements(self):
        """
        Process all inventory movements using FIFO logic
        """
        for idx, row in self.df.iterrows():
            product = row['Primary SKU']
            location = row['Location']
            qty = row['Qty.']
            date = row['DateTime']
            cost = abs(row['Cost']) if pd.notna(row['Cost']) else 0
            adj_reason = row['Adj. reason']
            
            if qty > 0:
                self._add_stock(product, location, date, qty, cost, adj_reason)
            elif qty < 0:
                self._remove_stock(product, location, date, abs(qty), adj_reason)
                
    def _add_stock(self, product, location, date, qty, cost, reason):
        """
        Add stock to inventory (FIFO queue)
        """
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
            oldest_stock = self.current_stock[product][location].popleft()
            shelf_time_days = (date - oldest_stock['date']).days
            
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
            st.warning(f"⚠️ Tried to remove {qty} units of {product} at {location}, but only {removed_qty} were available")
    
    def generate_analytics(self):
        """
        Generate comprehensive analytics from shelf time data
        """
        if not self.shelf_time_records:
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
                if stock_queue:
                    qty = len(stock_queue)
                    oldest_date = min(item['date'] for item in stock_queue)
                    newest_date = max(item['date'] for item in stock_queue)
                    total_cost = sum(item['cost'] for item in stock_queue)
                    avg_cost = total_cost / qty if qty > 0 else 0
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

def create_visualizations(analytics, shelf_time_df, current_stock_df, aging_categories):
    """
    Create Plotly visualizations for the dashboard
    """
    charts = {}
    
    # 1. Shelf Time Distribution
    if not shelf_time_df.empty:
        fig_hist = px.histogram(
            shelf_time_df, 
            x='shelf_time_days', 
            nbins=30,
            title='Distribution of Shelf Time (Days)',
            labels={'shelf_time_days': 'Shelf Time (Days)', 'count': 'Frequency'}
        )
        charts['shelf_time_distribution'] = fig_hist
        
        # 2. Average Shelf Time by Product
        product_avg = shelf_time_df.groupby('product')['shelf_time_days'].mean().sort_values(ascending=False).head(10)
        fig_product = px.bar(
            x=product_avg.values,
            y=product_avg.index,
            orientation='h',
            title='Top 10 Products by Average Shelf Time',
            labels={'x': 'Average Shelf Time (Days)', 'y': 'Product'}
        )
        charts['product_shelf_time'] = fig_product
        
        # 3. Monthly Trends
        if not analytics['monthly_trends'].empty:
            monthly_data = analytics['monthly_trends'].reset_index()
            monthly_data['month_str'] = monthly_data['sale_month'].astype(str)
            fig_monthly = px.line(
                monthly_data,
                x='month_str',
                y=('shelf_time_days', 'mean'),
                title='Monthly Average Shelf Time Trend',
                labels={'month_str': 'Month', 'y': 'Average Shelf Time (Days)'}
            )
            charts['monthly_trends'] = fig_monthly
    
    # 4. Current Stock Aging
    if not current_stock_df.empty:
        fig_aging = px.scatter(
            current_stock_df,
            x='current_qty',
            y='days_on_shelf_oldest',
            size='total_cost',
            color='product',
            title='Current Stock: Quantity vs Days on Shelf',
            labels={'current_qty': 'Current Quantity', 'days_on_shelf_oldest': 'Days on Shelf'}
        )
        charts['stock_aging_scatter'] = fig_aging
    
    # 5. Aging Categories Pie Chart
    aging_summary = {category: len(items) for category, items in aging_categories.items()}
    if sum(aging_summary.values()) > 0:
        fig_pie = px.pie(
            values=list(aging_summary.values()),
            names=list(aging_summary.keys()),
            title='Stock Distribution by Aging Categories'
        )
        charts['aging_pie'] = fig_pie
    
    return charts

def main():
    """
    Main Streamlit application
    """
    st.title("📊 Inventory Analytics Dashboard")
    st.markdown("---")
    
    # Sidebar
    st.sidebar.header("📁 Upload Data")
    uploaded_file = st.sidebar.file_uploader(
        "Upload your inventory CSV file",
        type=['csv'],
        help="Upload a CSV file with columns: Date, Primary SKU, Location, Qty., Cost, Adj. reason"
    )
    
    if uploaded_file is not None:
        try:
            # Load data
            df = pd.read_csv(uploaded_file)
            
            # Display data info
            st.sidebar.success(f"✅ File uploaded successfully!")
            st.sidebar.info(f"📄 {len(df)} transactions loaded")
            
            # Initialize analyzer
            with st.spinner("🔄 Processing inventory data..."):
                analyzer = InventoryAnalyzer(df)
                analyzer.process_inventory_movements()
                analytics, shelf_time_df = analyzer.generate_analytics()
                current_stock_df = analyzer.get_current_stock_summary()
                aging_categories = analyzer.get_aging_summary_by_categories()
            
            # Main dashboard
            st.header("📈 Key Metrics")
            
            # Metrics row
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Total Transactions",
                    f"{len(df):,}",
                    help="Total number of inventory transactions"
                )
            
            with col2:
                if analytics['overall']['total_units_sold'] > 0:
                    st.metric(
                        "Avg Shelf Time",
                        f"{analytics['overall']['average_shelf_time_days']:.1f} days",
                        help="Average time products stay on shelf"
                    )
                else:
                    st.metric("Avg Shelf Time", "N/A", help="No shelf time data available")
            
            with col3:
                current_stock_units = current_stock_df['current_qty'].sum() if not current_stock_df.empty else 0
                st.metric(
                    "Current Stock",
                    f"{current_stock_units:,} units",
                    help="Total units currently in stock"
                )
            
            with col4:
                current_stock_value = current_stock_df['total_cost'].sum() if not current_stock_df.empty else 0
                st.metric(
                    "Stock Value",
                    f"₹{current_stock_value:,.0f}",
                    help="Total value of current stock"
                )
            
            # Tabs for different views
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "📊 Analytics", "📋 Current Stock", "🏷️ Aging Analysis", 
                "📈 Visualizations", "📄 Raw Data"
            ])
            
            with tab1:
                st.header("📊 Analytics Overview")
                
                if analytics['overall']['total_units_sold'] > 0:
                    # Overall statistics
                    st.subheader("📋 Overall Statistics")
                    stats_col1, stats_col2 = st.columns(2)
                    
                    with stats_col1:
                        st.write(f"**Total Units Sold:** {analytics['overall']['total_units_sold']:,}")
                        st.write(f"**Average Shelf Time:** {analytics['overall']['average_shelf_time_days']:.1f} days")
                        st.write(f"**Median Shelf Time:** {analytics['overall']['median_shelf_time_days']:.1f} days")
                    
                    with stats_col2:
                        st.write(f"**Min Shelf Time:** {analytics['overall']['min_shelf_time_days']} days")
                        st.write(f"**Max Shelf Time:** {analytics['overall']['max_shelf_time_days']} days")
                        st.write(f"**Std Deviation:** {analytics['overall']['std_shelf_time_days']:.1f} days")
                    
                    # Fast vs Slow Moving Products
                    st.subheader("🚀 Fast Moving Products")
                    if not analytics['fast_moving_products'].empty:
                        fast_df = analytics['fast_moving_products'].reset_index()
                        fast_df.columns = ['Product', 'Avg Shelf Time (Days)']
                        st.dataframe(fast_df, use_container_width=True)
                    
                    st.subheader("🐌 Slow Moving Products")
                    if not analytics['slow_moving_products'].empty:
                        slow_df = analytics['slow_moving_products'].reset_index()
                        slow_df.columns = ['Product', 'Avg Shelf Time (Days)']
                        st.dataframe(slow_df, use_container_width=True)
                
                else:
                    st.warning("⚠️ No shelf time analysis available. Sales may be occurring before purchases in your dataset.")
            
            with tab2:
                st.header("📋 Current Stock Summary")
                
                if not current_stock_df.empty:
                    st.dataframe(current_stock_df, use_container_width=True)
                    
                    # Download button for current stock
                    csv_stock = current_stock_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Current Stock CSV",
                        data=csv_stock,
                        file_name=f"current_stock_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("ℹ️ No current stock data available.")
            
            with tab3:
                st.header("🏷️ Stock Aging Analysis")
                
                # Aging categories summary
                aging_summary = {category: len(items) for category, items in aging_categories.items()}
                
                if sum(aging_summary.values()) > 0:
                    st.subheader("📊 Aging Categories Summary")
                    
                    aging_cols = st.columns(4)
                    for i, (category, count) in enumerate(aging_summary.items()):
                        with aging_cols[i]:
                            total_value = sum(item['cost'] for item in aging_categories[category])
                            st.metric(
                                category,
                                f"{count} units",
                                f"₹{total_value:,.0f}"
                            )
                    
                    # Detailed aging breakdown
                    st.subheader("📋 Detailed Aging Breakdown")
                    aging_data = []
                    for category, items in aging_categories.items():
                        for item in items:
                            aging_data.append({
                                'Category': category,
                                'Product': item['product'],
                                'Location': item['location'],
                                'Days on Shelf': item['days_on_shelf'],
                                'Cost': item['cost'],
                                'Purchase Date': item['purchase_date']
                            })
                    
                    if aging_data:
                        aging_df = pd.DataFrame(aging_data)
                        st.dataframe(aging_df, use_container_width=True)
                        
                        # Download button for aging analysis
                        csv_aging = aging_df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download Aging Analysis CSV",
                            data=csv_aging,
                            file_name=f"aging_analysis_{datetime.now().strftime('%Y%m%d')}.csv",
                            mime="text/csv"
                        )
                else:
                    st.info("ℹ️ No aging data available.")
            
            with tab4:
                st.header("📈 Visualizations")
                
                # Create visualizations
                charts = create_visualizations(analytics, shelf_time_df, current_stock_df, aging_categories)
                
                # Display charts
                for chart_name, chart in charts.items():
                    st.plotly_chart(chart, use_container_width=True)
            
            with tab5:
                st.header("📄 Raw Data")
                
                st.subheader("🔍 Transaction Data")
                st.dataframe(df, use_container_width=True)
                
                # Download button for processed data
                csv_raw = df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Transaction Data CSV",
                    data=csv_raw,
                    file_name=f"transaction_data_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
                
                if not shelf_time_df.empty:
                    st.subheader("📊 Shelf Time Records")
                    st.dataframe(shelf_time_df, use_container_width=True)
                    
                    # Download button for shelf time data
                    csv_shelf = shelf_time_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Shelf Time CSV",
                        data=csv_shelf,
                        file_name=f"shelf_time_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
            
        except Exception as e:
            st.error(f"❌ Error processing file: {str(e)}")
            st.info("Please ensure your CSV file has the required columns: Date, Primary SKU, Location, Qty., Cost, Adj. reason")
    
    else:
        # Landing page
        st.info("👆 Please upload a CSV file to get started with the analysis.")
        
        st.markdown("""
        ### 📝 Required CSV Format
        
        Your CSV file should contain the following columns:
        - **Date**: Transaction date (format: "DD MMM YYYY, HH:MM AM/PM")
        - **Primary SKU**: Product identifier
        - **Location**: Storage location
        - **Qty.**: Quantity (positive for inbound, negative for outbound)
        - **Cost**: Transaction cost
        - **Adj. reason**: Adjustment reason
        
        ### 🔍 What This App Does
        
        - **FIFO Analysis**: Tracks inventory using First In, First Out methodology
        - **Shelf Time Calculation**: Measures how long products stay in inventory
        - **Aging Analysis**: Categorizes stock by age (Fresh, Medium, Aged, Very Aged)
        - **Interactive Visualizations**: Charts and graphs for better insights
        - **Export Reports**: Download analysis results as CSV files
        
        ### 📊 Features
        
        - Real-time inventory analytics
        - Current stock summary
        - Product movement analysis
        - Location-wise insights
        - Interactive dashboard
        """)

if __name__ == "__main__":
    main()
