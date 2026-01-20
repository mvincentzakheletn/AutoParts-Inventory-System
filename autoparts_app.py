import streamlit as st
import pandas as pd
import sqlalchemy as sa
import urllib
from datetime import datetime, date, timedelta
import tempfile
import os

params = urllib.parse.quote_plus(
    r'DRIVER={ODBC Driver 17 for SQL Server};'
    r'SERVER=DESKTOP-6O63UFT\SQLEXPRESS01;' 
    r'DATABASE=AutoPartsDB;'
    r'Trusted_Connection=yes;'
)
engine = sa.create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

st.set_page_config(page_title="AutoParts Pro Manager", layout="wide")
st.title("🚗 AutoParts Pro: Management System")

st.sidebar.markdown("---")
st.sidebar.subheader("📊 Quick Stats")

try:
    low_stock_count = pd.read_sql(
        "SELECT COUNT(*) as count FROM Parts WHERE StockQTY < 10", 
        engine
    )['count'].iloc[0]
    
    if low_stock_count > 0:
        st.sidebar.error(f"⚠️ {low_stock_count} items need restock!")
    else:
        st.sidebar.success("✅ All items in stock")
except:
    st.sidebar.info("Stats loading...")

st.sidebar.markdown("---")

menu = ["Inventory View", "Process Sale", "Transaction History", "Inventory Management", "Customer Management", "Monthly Report"]
choice = st.sidebar.selectbox("Navigation", menu)

def generate_html_receipt(customer_name, cart_items, grand_total, sale_date, receipt_number):
    """Generate an HTML receipt that can be printed or saved"""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>AutoParts Pro - Receipt #{receipt_number}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .receipt {{ max-width: 600px; margin: 0 auto; border: 1px solid #ddd; padding: 20px; }}
            .header {{ text-align: center; border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 20px; }}
            .header h1 {{ color: #333; }}
            .details {{ margin-bottom: 20px; }}
            .details p {{ margin: 5px 0; }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            th {{ background-color: #f2f2f2; text-align: left; padding: 10px; border-bottom: 1px solid #ddd; }}
            td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
            .total {{ text-align: right; font-size: 18px; font-weight: bold; margin-top: 20px; }}
            .footer {{ text-align: center; margin-top: 30px; color: #666; font-style: italic; }}
            @media print {{
                body {{ margin: 0; }}
                .no-print {{ display: none; }}
            }}
        </style>
    </head>
    <body>
        <div class="receipt">
            <div class="header">
                <h1>🚗 AutoParts Pro</h1>
                <h2>SALES RECEIPT</h2>
            </div>
            
            <div class="details">
                <p><strong>Receipt No:</strong> {receipt_number}</p>
                <p><strong>Date:</strong> {sale_date.strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>Customer:</strong> {customer_name}</p>
            </div>
            
            <table>
                <thead>
                    <tr>
                        <th>Item</th>
                        <th>Model</th>
                        <th>Qty</th>
                        <th>Price</th>
                        <th>Total</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    for item in cart_items:
        html_content += f"""
                    <tr>
                        <td>{item['PartName']}</td>
                        <td>{item['CarModel']}</td>
                        <td>{item['Qty']}</td>
                        <td>R{item['Price']:.2f}</td>
                        <td>R{item['Total']:.2f}</td>
                    </tr>
        """
    
    html_content += f"""
                </tbody>
            </table>
            
            <div class="total">
                <p>GRAND TOTAL: <span style="color: green;">R{grand_total:,.2f}</span></p>
            </div>
            
            <div class="footer">
                <p>Thank you for your business!</p>
                <p>AutoParts Pro - Quality Auto Parts</p>
                <p>Contact: info@autopartspro.co.za | Tel: +27 123 456 789</p>
            </div>
            
            <div class="no-print" style="margin-top: 20px; text-align: center;">
                <p><em>Print this page (Ctrl+P) or save as PDF</em></p>
            </div>
        </div>
    </body>
    </html>
    """
    
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode='w', encoding='utf-8')
    temp_file.write(html_content)
    temp_file.close()
    
    return temp_file.name

if choice == "Inventory View":
    st.subheader("📦 Current Stock Levels")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        search_term = st.text_input("🔍 Search parts by name or car model", "")
    with col2:
        low_stock_only = st.checkbox("Show low stock only (<10)")
    
    query = "SELECT * FROM Parts"
    conditions = []
    
    if search_term:
        conditions.append(f"(PartName LIKE '%{search_term}%' OR CarModel LIKE '%{search_term}%')")
    
    if low_stock_only:
        conditions.append("StockQTY < 10")
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY StockQTY ASC"
    
    df = pd.read_sql(query, engine)
    
    if not df.empty:
        total_items = len(df)
        total_value = (df['StockQTY'] * df['Price']).sum()
        
        metric1, metric2, metric3 = st.columns(3)
        metric1.metric("Total Items", total_items)
        metric2.metric("Total Stock QTY", df['StockQTY'].sum())
        metric3.metric("Total Inventory Value", f"R {total_value:,.2f}")
        
        def color_low_stock(val):
            if val < 10:
                return 'color: red; font-weight: bold'
            elif val < 20:
                return 'color: orange'
            else:
                return 'color: green'
    
        styled_df = df.style.map(color_low_stock, subset=['StockQTY'])
        
        st.dataframe(
            styled_df,
            use_container_width=True,
            column_config={
                "Price": st.column_config.NumberColumn("Price", format="R %.2f"),
                "StockQTY": st.column_config.NumberColumn("In Stock", format="%d"),
                "CostPrice": st.column_config.NumberColumn("Cost", format="R %.2f")
            }
        )
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Inventory",
            data=csv,
            file_name='inventory_export.csv',
            mime='text/csv',
        )
    else:
        st.info("No items found matching your search criteria.")

elif choice == "Process Sale":
    st.subheader("🛒 New Transaction")
    
    if 'cart' not in st.session_state:
        st.session_state['cart'] = []
    
    if 'receipt_number' not in st.session_state:
        st.session_state['receipt_number'] = datetime.now().strftime("%Y%m%d") + "-001"
    
    customers_df = pd.read_sql("SELECT CustomerID, FullName FROM Customers", engine)
    parts_df = pd.read_sql("SELECT PartID, PartName, CarModel, StockQTY, Price FROM Parts", engine)
    
    if customers_df.empty:
        st.error("No customers found! Please add customers first.")
    else:
        selected_cust_name = st.selectbox("Select Customer", customers_df['FullName'].tolist())
        cust_id = customers_df[customers_df['FullName'] == selected_cust_name]['CustomerID'].values[0]
        
        col_rec1, col_rec2 = st.columns([2, 1])
        with col_rec1:
            st.info(f"**Receipt No:** {st.session_state['receipt_number']} | **Customer:** {selected_cust_name}")
        with col_rec2:
            st.info(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        st.divider()
        
        col_search, col_filter = st.columns([3, 1])
        with col_search:
            part_search = st.text_input("🔍 Search parts", "")
        with col_filter:
            unique_models = ["All"] + parts_df['CarModel'].unique().tolist()
            selected_car = st.selectbox("Filter by Car Model", unique_models)
    
        filtered_parts = parts_df.copy()
        if part_search:
            filtered_parts = filtered_parts[filtered_parts['PartName'].str.contains(part_search, case=False)]
        if selected_car != "All":
            filtered_parts = filtered_parts[filtered_parts['CarModel'] == selected_car]
        
        if not filtered_parts.empty:
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                selected_part_name = st.selectbox("Select Part", filtered_parts['PartName'].tolist())
            
            with col2:
                selected_model = filtered_parts[filtered_parts['PartName'] == selected_part_name]['CarModel'].iloc[0]
                st.text_input("Car Model", selected_model, disabled=True)
            
            with col3:
                available_stock = int(filtered_parts[filtered_parts['PartName'] == selected_part_name]['StockQTY'].iloc[0])
                qty = st.number_input("Quantity", min_value=1, max_value=available_stock, value=1)
            
            if selected_part_name:
                item_details = filtered_parts[filtered_parts['PartName'] == selected_part_name].iloc[0]
                
                price = round(float(item_details['Price']), 2)
                max_stock = int(item_details['StockQTY'])
                line_total = round(price * qty, 2)
                
                st.info(f"💰 **Unit Price:** R{price:,.2f} | **Line Total:** R{line_total:,.2f} | **Available:** {max_stock}")
                
                col_add, col_info = st.columns([1, 3])
                with col_add:
                    if st.button("➕ Add to Cart", use_container_width=True):
                        st.session_state['cart'].append({
                            "PartID": int(item_details['PartID']),
                            "PartName": selected_part_name,
                            "CarModel": selected_model,
                            "Qty": qty,
                            "Price": price,
                            "Total": line_total
                        })
                        st.toast(f"Added {selected_part_name} to cart!")
                        st.rerun()
                
                with col_info:
                    if qty > max_stock:
                        st.error(f"Only {max_stock} units available!")
        
        st.divider()
        
        st.write("### 🛒 Current Shopping Cart")
        if st.session_state['cart']:
            cart_display = pd.DataFrame(st.session_state['cart'])
            
            st.dataframe(
                cart_display[['PartName', 'CarModel', 'Qty', 'Price', 'Total']],
                use_container_width=True,
                column_config={
                    "Price": st.column_config.NumberColumn(format="R %.2f"),
                    "Total": st.column_config.NumberColumn(format="R %.2f")
                }
            )
            
            grand_total = round(cart_display['Total'].sum(), 2)
            total_items = cart_display['Qty'].sum()
            
            col_summary1, col_summary2 = st.columns(2)
            with col_summary1:
                st.metric("Total Items in Cart", total_items)
            with col_summary2:
                st.metric("Grand Total", f"R {grand_total:,.2f}")
            
            col_clear, col_sale, col_export = st.columns(3)
            with col_clear:
                if st.button("🗑️ Clear Cart", use_container_width=True):
                    st.session_state['cart'] = []
                    st.rerun()
            
            with col_sale:
                if st.button("✅ Complete Sale", type="primary", use_container_width=True):
                    sale_date = datetime.now()
                    try:
                        with engine.begin() as conn:
                            for item in st.session_state['cart']:
                                conn.execute(sa.text(
                                    "UPDATE Parts SET StockQTY = StockQTY - :q WHERE PartID = :p"), 
                                    {"q": item['Qty'], "p": item['PartID']}
                                )
                                conn.execute(sa.text(
                                    "INSERT INTO Sales (CustomerID, PartsID, QuantitySold, TotalAmount, SaleDate) VALUES (:c, :p, :q, :t, :d)"),
                                    {"c": int(cust_id), "p": item['PartID'], "q": item['Qty'], "t": item['Total'], "d": sale_date}
                                )
                        
                        html_path = generate_html_receipt(
                            selected_cust_name,
                            st.session_state['cart'],
                            grand_total,
                            sale_date,
                            st.session_state['receipt_number']
                        )
                        
                        st.success(f"✅ Sale completed successfully! Total: R{grand_total:,.2f}")
                        st.balloons()
                        
                        st.divider()
                        st.write("### 📄 Sales Receipt")
                        
                        with open(html_path, 'r', encoding='utf-8') as f:
                            html_content = f.read()
                
                        st.components.v1.html(html_content, height=800, scrolling=True)
                        
                        col_html, col_csv, col_new = st.columns(3)
                        
                        with col_html:
                            with open(html_path, 'rb') as f:
                                html_data = f.read()
                            st.download_button(
                                label="📥 Download Receipt (HTML)",
                                data=html_data,
                                file_name=f"receipt_{st.session_state['receipt_number']}.html",
                                mime="text/html",
                                use_container_width=True
                            )
                        
                        with col_csv:
                            receipt_csv = cart_display.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                label="📥 Export Cart as CSV",
                                data=receipt_csv,
                                file_name=f"receipt_{st.session_state['receipt_number']}.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                        
                        with col_new:
                            if st.button("🔄 Start New Sale", use_container_width=True):
                                try:
                                    current_num = int(st.session_state['receipt_number'].split('-')[1])
                                    new_num = current_num + 1
                                except:
                                    new_num = 1
                                st.session_state['receipt_number'] = datetime.now().strftime("%Y%m%d") + f"-{new_num:03d}"
                                st.session_state['cart'] = []
                                st.rerun()
                        
                        st.info("💡 **Tip:** You can print this receipt by pressing **Ctrl+P** and saving as PDF")
                        
                        try:
                            os.unlink(html_path)
                        except:
                            pass
                        
                    except Exception as e:
                        st.error(f"Transaction failed: {str(e)}")
            
            with col_export:
                csv = cart_display.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Export Cart",
                    data=csv,
                    file_name='cart_export.csv',
                    mime='text/csv',
                    use_container_width=True
                )
        else:
            st.info("Your cart is empty. Add items to begin.")

elif choice == "Transaction History":
    st.subheader("📋 Sales Transaction History")
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", date.today() - timedelta(days=30))
    with col2:
        end_date = st.date_input("End Date", date.today())
    
    search_term = st.text_input("🔍 Search by customer or part name")
    
    query = f"""
        SELECT 
            s.SalesId,
            s.SaleDate,
            c.FullName as Customer,
            p.PartName,
            p.CarModel,
            s.QuantitySold,
            s.TotalAmount
        FROM Sales s
        JOIN Customers c ON s.CustomerID = c.CustomerID
        JOIN Parts p ON s.PartsID = p.PartID
        WHERE CAST(s.SaleDate AS DATE) BETWEEN '{start_date}' AND '{end_date}'
    """
    
    if search_term:
        query += f" AND (c.FullName LIKE '%{search_term}%' OR p.PartName LIKE '%{search_term}%')"
    
    query += " ORDER BY s.SaleDate DESC"
    
    df_sales = pd.read_sql(query, engine)
    
    if not df_sales.empty:
        total_sales = df_sales['TotalAmount'].sum()
        total_transactions = len(df_sales)
        avg_sale = total_sales / total_transactions if total_transactions > 0 else 0
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Sales", f"R {total_sales:,.2f}")
        m2.metric("Total Transactions", total_transactions)
        m3.metric("Average Sale", f"R {avg_sale:,.2f}")
        
        st.dataframe(
            df_sales,
            use_container_width=True,
            column_config={
                "SaleDate": st.column_config.DatetimeColumn(format="DD/MM/YYYY HH:mm"),
                "TotalAmount": st.column_config.NumberColumn(format="R %.2f")
            }
        )
        
        csv = df_sales.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Transaction History",
            data=csv,
            file_name=f'sales_history_{date.today()}.csv',
            mime='text/csv',
        )
    else:
        st.info("No sales records found for the selected period.")

elif choice == "Customer Management":
    st.subheader("👥 Customer Relationship Management")
    tab1, tab2, tab3, tab4 = st.tabs(["View Customers", "Add New Customer", "Remove Customer", "Customer Analytics"])

    with tab1:
        st.write("### 📇 Active Customer Directory")
        
        search_customer = st.text_input("🔍 Search customers by name or email")
        
        query = "SELECT CustomerID, FullName, Email, Phone, CreatedDate FROM Customers"
        if search_customer:
            query += f" WHERE FullName LIKE '%{search_customer}%' OR Email LIKE '%{search_customer}%'"
        
        cust_df = pd.read_sql(query, engine)
        
        if not cust_df.empty:
            st.dataframe(
                cust_df,
                use_container_width=True,
                column_config={
                    "CreatedDate": st.column_config.DateColumn(format="DD/MM/YYYY")
                }
            )
            
            csv = cust_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export Customer List",
                data=csv,
                file_name='customers_export.csv',
                mime='text/csv',
            )
        else:
            st.info("No customers found.")

    with tab2:
        st.write("### ➕ Register New Customer")
        with st.form("add_cust_form"):
            new_cust_name = st.text_input("Full Name *", placeholder="John Doe")
            new_cust_email = st.text_input("Email Address", placeholder="john@example.com")
            new_cust_phone = st.text_input("Phone Number", placeholder="+27 123 456 789")
            
            submit_cust = st.form_submit_button("Add Customer", type="primary")
            
            if submit_cust:
                if new_cust_name == "":
                    st.error("Full Name is required.")
                else:
                    try:
                        with engine.begin() as conn:
                            conn.execute(
                                sa.text("INSERT INTO Customers (FullName, Email, Phone, CreatedDate) VALUES (:n, :e, :p, :d)"),
                                {"n": new_cust_name, "e": new_cust_email, "p": new_cust_phone, "d": datetime.now()}
                            )
                        st.success(f"✅ {new_cust_name} added successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding customer: {str(e)}")

    with tab3:
        st.write("### 🗑️ Remove Customer Profile")
        st.warning("⚠️ Action cannot be undone. Be careful!")
        
        cust_list_df = pd.read_sql("SELECT CustomerID, FullName FROM Customers", engine)
        
        if not cust_list_df.empty:
            cust_to_del = st.selectbox("Select Customer to Remove", cust_list_df['FullName'].tolist())
            
            target_id = cust_list_df[cust_list_df['FullName'] == cust_to_del]['CustomerID'].values[0]
            sales_count = pd.read_sql(
                f"SELECT COUNT(*) as count FROM Sales WHERE CustomerID = {target_id}",
                engine
            )['count'].iloc[0]
            
            if sales_count > 0:
                st.error(f"This customer has {sales_count} sales records. Deletion is blocked for audit purposes.")
                st.info("Consider marking them as inactive instead.")
            else:
                if st.button("Delete Customer Permanently", type="secondary"):
                    try:
                        with engine.begin() as conn:
                            conn.execute(sa.text("DELETE FROM Customers WHERE CustomerID = :id"), {"id": int(target_id)})
                        st.success(f"🗑️ Record for {cust_to_del} has been deleted.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error deleting customer: {str(e)}")
        else:
            st.info("No customers to delete.")

    with tab4:
        st.write("### 📊 Customer Analytics")
        
        query = """
            SELECT 
                c.FullName,
                COUNT(s.SalesId) as PurchaseCount,
                SUM(s.TotalAmount) as TotalSpent,
                AVG(s.TotalAmount) as AvgPurchase
            FROM Customers c
            LEFT JOIN Sales s ON c.CustomerID = s.CustomerID
            GROUP BY c.CustomerID, c.FullName
            ORDER BY TotalSpent DESC
        """
        
        cust_analytics = pd.read_sql(query, engine)
        
        if not cust_analytics.empty:
            st.dataframe(
                cust_analytics,
                use_container_width=True,
                column_config={
                    "TotalSpent": st.column_config.NumberColumn(format="R %.2f"),
                    "AvgPurchase": st.column_config.NumberColumn(format="R %.2f")
                }
            )
        else:
            st.info("No purchase data available.")

elif choice == "Monthly Report":
    st.subheader("📊 Financial Overview & Profit Report")
    
    col1, col2 = st.columns(2)
    with col1:
        report_month = st.selectbox("Select Period", 
                                  ["Current Month", "Last Month", "Last 30 Days", "All Time", "Custom Range"] + 
                                  [f"{m:02d}" for m in range(1, 13)])
    
    with col2:
        report_year = datetime.now().year
        
        if report_month == "Custom Range":
            custom_start = st.date_input("Start Date", date.today() - timedelta(days=30))
            custom_end = st.date_input("End Date", date.today())
        elif report_month in ["Current Month", "Last Month", "Last 30 Days", "All Time"]:
            pass
        elif report_month.isdigit():
            report_year = st.selectbox("Select Year", 
                                     [datetime.now().year, datetime.now().year - 1])
    
    date_condition = ""
    if report_month == "Current Month":
        current_month = datetime.now().month
        current_year = datetime.now().year
        date_condition = f"AND MONTH(s.SaleDate) = {current_month} AND YEAR(s.SaleDate) = {current_year}"
    elif report_month == "Last Month":
        last_month = datetime.now().replace(day=1) - timedelta(days=1)
        date_condition = f"AND MONTH(s.SaleDate) = {last_month.month} AND YEAR(s.SaleDate) = {last_month.year}"
    elif report_month == "Last 30 Days":
        thirty_days_ago = datetime.now() - timedelta(days=30)
        date_condition = f"AND s.SaleDate >= '{thirty_days_ago}'"
    elif report_month.isdigit():
        if 'report_year' not in locals():
            report_year = datetime.now().year
        date_condition = f"AND MONTH(s.SaleDate) = {report_month} AND YEAR(s.SaleDate) = {report_year}"
    elif report_month == "Custom Range":
        date_condition = f"AND s.SaleDate BETWEEN '{custom_start}' AND '{custom_end}'"
    
    report_query = f"""
        SELECT 
            p.PartName, 
            p.CarModel,
            SUM(s.QuantitySold) AS Units_Sold, 
            SUM(s.TotalAmount) AS Total_Revenue,
            SUM(s.QuantitySold * p.CostPrice) AS Total_Cost
        FROM Sales s
        INNER JOIN Parts p ON s.PartsID = p.PartID 
        WHERE 1=1 {date_condition}
        GROUP BY p.PartName, p.CarModel
        ORDER BY Total_Revenue DESC
    """
    
    try:
        df_sales = pd.read_sql(report_query, engine)
        
        if df_sales.empty:
            st.info("No sales recorded for the selected period.")
        else:
            df_sales['Gross_Profit'] = df_sales['Total_Revenue'] - df_sales['Total_Cost']
            df_sales['Margin_%'] = df_sales.apply(
                lambda x: (x['Gross_Profit'] / x['Total_Revenue'] * 100) if x['Total_Revenue'] > 0 else 0, 
                axis=1
            )

            total_rev = df_sales['Total_Revenue'].sum()
            total_cost = df_sales['Total_Cost'].sum()
            total_profit = df_sales['Gross_Profit'].sum()
            avg_margin = (total_profit / total_rev) * 100 if total_rev > 0 else 0
            total_units = df_sales['Units_Sold'].sum()

            kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
            kpi1.metric("Total Revenue", f"R {total_rev:,.2f}")
            kpi2.metric("Total Cost", f"R {total_cost:,.2f}")
            kpi3.metric("Gross Profit", f"R {total_profit:,.2f}")
            kpi4.metric("Avg Margin", f"{avg_margin:.1f}%")
            kpi5.metric("Units Sold", f"{total_units:,}")
            
            st.divider()
            
            st.dataframe(
                df_sales, 
                use_container_width=True,
                column_config={
                    "Total_Revenue": st.column_config.NumberColumn(format="R %.2f"),
                    "Total_Cost": st.column_config.NumberColumn(format="R %.2f"),
                    "Gross_Profit": st.column_config.NumberColumn(format="R %.2f"),
                    "Margin_%": st.column_config.NumberColumn(format="%.1f%%"),
                    "Units_Sold": st.column_config.NumberColumn(format="%d")
                }
            )
            
            if report_month == "Custom Range":
                file_name_part = f"custom_{custom_start}_{custom_end}"
            elif report_month.isdigit():
                file_name_part = f"{report_month}_{report_year}"
            else:
                file_name_part = report_month.lower().replace(" ", "_")
        
            csv = df_sales.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Profit Report",
                data=csv,
                file_name=f'profit_report_{file_name_part}.csv',
                mime='text/csv',
            )
            
    except Exception as e:
        st.error(f"Database Error: {e}")

elif choice == "Inventory Management":
    st.subheader("📦 Stock Control Center")
    tab1, tab2 = st.tabs(["Restock Existing Item", "Add New Product"])

    with tab1:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.write("### 📋 Current Inventory Overview")
        
            search_inv = st.text_input("🔍 Search inventory", "")
            
            query = "SELECT PartName, CarModel, StockQTY, Price, CostPrice FROM Parts"
            if search_inv:
                query += f" WHERE PartName LIKE '%{search_inv}%' OR CarModel LIKE '%{search_inv}%'"
            query += " ORDER BY StockQTY ASC"
            
            stock_df = pd.read_sql(query, engine)
            
            if not stock_df.empty:
                def color_text(val):
                    if val < 10:
                        return 'color: red; font-weight: bold'
                    elif val < 20:
                        return 'color: orange'
                    else:
                        return ''
                
                styled_df = stock_df.style.map(color_text, subset=['StockQTY']).format({
                    "Price": "R {:.2f}",
                    "CostPrice": "R {:.2f}"
                })
                
                st.dataframe(styled_df, use_container_width=True)
                
                low_stock_items = stock_df[stock_df['StockQTY'] < 10]
                if not low_stock_items.empty:
                    st.warning(f"⚠️ {len(low_stock_items)} items have stock below 10 units")
            else:
                st.info("No items found.")

        with col2:
            st.write("### ➕ Update Stock")
            st.info("Select an item to increase quantity.")
            
            if not stock_df.empty:
                stock_df['DisplayName'] = stock_df['PartName'] + " (" + stock_df['CarModel'] + ")"
                part_list = stock_df['DisplayName'].tolist()
                
                selected_display_name = st.selectbox("Select Part to Restock", part_list)
                current_stock = int(stock_df[stock_df['DisplayName'] == selected_display_name]['StockQTY'].iloc[0])
                
                if current_stock < 10:
                    stock_color = "red"
                elif current_stock < 20:
                    stock_color = "orange"
                else:
                    stock_color = "green"
                
                st.markdown(f"**Current Stock:** <span style='color:{stock_color}; font-weight:bold'>{current_stock}</span>", unsafe_allow_html=True)
                
                add_qty = st.number_input("Quantity to Add", min_value=1, value=10)

                if st.button("✅ Confirm Restock", type="primary"):
                    part_name = selected_display_name.split(" (")[0]
                    car_model = selected_display_name.split(" (")[1].replace(")", "")

                    with engine.begin() as conn:
                        conn.execute(
                            sa.text("UPDATE Parts SET StockQty = StockQty + :q WHERE PartName = :p AND CarModel = :m"),
                            {"q": add_qty, "p": part_name, "m": car_model}
                        )
                    
                    st.success(f"✅ Added {add_qty} units to {part_name}!")
                    st.rerun()
            else:
                st.info("No items available for restocking.")

    with tab2:
        st.write("### 🆕 Add New Product to Database")
        with st.form("new_part_form"):
            col_a, col_b = st.columns(2)
            
            with col_a:
                new_name = st.text_input("Part Name *", placeholder="Brake Pad")
                new_model = st.text_input("Car Model *", placeholder="VW Polo")
                new_qty = st.number_input("Initial Stock Quantity", min_value=0, value=10)
                supplier = st.text_input("Supplier", placeholder="Auto Parts Inc.")
            
            with col_b:
                cost_price = st.number_input("Cost Price (R) *", min_value=0.0, value=50.0, format="%.2f")
                markup_pct = st.slider("Markup Percentage (%)", min_value=10, max_value=200, value=50)
                selling_price = cost_price * (1 + (markup_pct / 100))
                
                st.metric("Calculated Selling Price", f"R {selling_price:,.2f}")
                st.caption(f"Profit per unit: R {selling_price - cost_price:.2f}")
            
            submit_new = st.form_submit_button("🚀 Add to Inventory", type="primary")
            
            if submit_new:
                if not new_name or not new_model:
                    st.error("Part Name and Car Model are required.")
                else:
                    try:
                        with engine.begin() as conn:
                            conn.execute(
                                sa.text("""INSERT INTO Parts (PartName, CarModel, Price, CostPrice, StockQty, Supplier) 
                                           VALUES (:n, :m, :p, :c, :q, :s)"""),
                                {"n": new_name, "m": new_model, "p": selling_price, 
                                 "c": cost_price, "q": new_qty, "s": supplier}
                            )
                        st.success(f"🚀 {new_name} added successfully!")
                        st.info(f"Cost: R{cost_price:.2f} | Price: R{selling_price:.2f} | Markup: {markup_pct}%")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding product: {str(e)}")
