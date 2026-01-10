import streamlit as st
import pandas as pd
import sqlalchemy as sa
import urllib


# --- DATABASE CONNECTION ---
params = urllib.parse.quote_plus(
    r'DRIVER={ODBC Driver 17 for SQL Server};'
    r'SERVER=DESKTOP-6O63UFT\SQLEXPRESS01;' 
    r'DATABASE=AutoPartsDB;'
    r'Trusted_Connection=yes;'
)
engine = sa.create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

# --- APP INTERFACE ---
st.set_page_config(page_title="AutoParts Pro Manager", layout="wide")
st.title("🚗 AutoParts Pro: Management System")

# Sidebar Navigation
menu = ["Inventory View", "Process Sale", "Inventory Management", "Monthly Report"]
choice = st.sidebar.selectbox("Navigation", menu)

if choice == "Inventory View":
    st.subheader("Current Stock Levels")
    df = pd.read_sql("SELECT * FROM Parts", engine)
    st.dataframe(df, use_container_width=True)
    
    # Low Stock Alert
    low_stock = df[df['StockQTY'] < 10]
    if not low_stock.empty:
        st.warning("⚠️ Items requiring restock!")
        st.table(low_stock)

elif choice == "Process Sale":
    st.subheader("New Transaction")
    
    # Get dropdown data from SQL
    parts_list = pd.read_sql("SELECT PartName FROM Parts", engine)['PartName'].tolist()
    customers_list = pd.read_sql("SELECT FullName FROM Customers", engine)['FullName'].tolist()
    
    col1, col2 = st.columns(2)
    with col1:
        selected_cust = st.selectbox("Select Customer", customers_list)
        selected_part = st.selectbox("Select Part", parts_list)
    with col2:
        qty = st.number_input("Quantity", min_value=1, value=1)
        
    if st.button("Complete Sale"):
        # We reuse your existing logic here
        with engine.begin() as conn:
            # 1. Check Stock
            part_info = conn.execute(sa.text("SELECT PartID, Price, StockQTY FROM Parts WHERE PartName = :p"), {"p": selected_part}).fetchone()
            cust_info = conn.execute(sa.text("SELECT CustomerID FROM Customers WHERE FullName = :c"), {"c": selected_cust}).fetchone()
            
            if part_info[2] >= qty:
                total_price = float(part_info[1]) * qty
                # 2. Record Sale
                conn.execute(sa.text("INSERT INTO Sales (CustomerID, PartsID, QuantitySold, TotalAmount) VALUES (:c, :p, :q, :t)"),
                             {"c": cust_info[0], "p": part_info[0], "q": qty, "t": total_price})
                # 3. Update Stock
                conn.execute(sa.text("UPDATE Parts SET StockQTY = StockQTY - :q WHERE PartID = :p"), {"q": qty, "p": part_info[0]})
                
                st.success(f"✅ Sale Processed! Total: R{total_price:,.2f}")
            else:
                st.error("❌ Insufficient Stock!")

elif choice == "Monthly Report":
    st.subheader("📊 Financial Overview & Month-End Report")
    
    # Query to get data per part
    report_query = """
        SELECT 
            Parts.PartName, 
            SUM(Sales.QuantitySold) AS Units, 
            SUM(Sales.TotalAmount) AS Revenue 
        FROM Sales
        INNER JOIN Parts ON Sales.PartsID = Parts.PartID 
        GROUP BY Parts.PartName
    """
    
    try:
        df_sales = pd.read_sql(report_query, engine)
        
        if df_sales.empty:
            st.info("No sales recorded yet. The totals will appear once transactions are made.")
        else:
            # --- THE CALCULATION PART ---
            total_revenue = df_sales['Revenue'].sum()
            total_units = df_sales['Units'].sum()
            
            # Display Grand Totals in attractive "Metric" boxes
            col1, col2 = st.columns(2)
            with col1:
                st.metric(label="Total Monthly Revenue", value=f"R {total_revenue:,.2f}")
            with col2:
                st.metric(label="Total Units Sold", value=int(total_units))
            
            st.divider() # Adds a clean visual line
            
            # --- THE VISUAL PART ---
            st.write("### Revenue by Product")
            st.bar_chart(data=df_sales, x="PartName", y="Revenue")
            
            st.write("### Detailed Breakdown")
            st.dataframe(df_sales, use_container_width=True)
            
            # Professional Add-on: Download Button
            csv = df_sales.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Report as CSV",
                data=csv,
                file_name='Monthly_AutoParts_Report.csv',
                mime='text/csv',
            )
            
    except Exception as e:
        st.error(f"Database Error: {e}")
    
    st.bar_chart(data=df_sales, x="PartName", y="Revenue")
    st.write("Summary Table", df_sales)

elif choice == "Inventory Management":
    st.subheader("📦 Stock Control")
    tab1, tab2 = st.tabs(["Restock Existing Item", "Add New Product"])

    # --- TAB 1: RESTOCK ---
    with tab1:
        st.write("Increase stock levels for items already in the system.")
        parts_df = pd.read_sql("SELECT PartName, StockQty FROM Parts", engine)
        part_to_restock = st.selectbox("Select Part to Restock", parts_df['PartName'].tolist())
        add_qty = st.number_input("Amount to Add", min_value=1, value=10)

        if st.button("Update Stock"):
            with engine.begin() as conn:
                conn.execute(
                    sa.text("UPDATE Parts SET StockQty = StockQty + :q WHERE PartName = :p"),
                    {"q": add_qty, "p": part_to_restock}
                )
            st.success(f"✅ Added {add_qty} units to {part_to_restock}!")
            st.rerun()

    # --- TAB 2: NEW PRODUCT ---
    with tab2:
        st.write("Add a brand new part to the inventory database.")
        with st.form("new_part_form"):
            new_name = st.text_input("Part Name (e.g., Spark Plug)")
            new_model = st.text_input("Car Model (e.g., Ford Ranger)")
            new_price = st.number_input("Selling Price (R)", min_value=0.0, format="%.2f")
            new_qty = st.number_input("Initial Stock Quantity", min_value=0)
            
            submit_new = st.form_submit_button("Add to Inventory")
            
            if submit_new:
                if new_name == "":
                    st.error("Please enter a part name.")
                else:
                    with engine.begin() as conn:
                        conn.execute(
                            sa.text("""INSERT INTO Parts (PartName, CarModel, Price, StockQty) 
                                     VALUES (:n, :m, :p, :q)"""),
                            {"n": new_name, "m": new_model, "p": new_price, "q": new_qty}
                        )
                    st.success(f"🚀 {new_name} has been added to the system!")