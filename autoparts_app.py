import streamlit as st
import pandas as pd
import sqlalchemy as sa
import urllib

params = urllib.parse.quote_plus(
    r'DRIVER={ODBC Driver 17 for SQL Server};'
    r'SERVER=DESKTOP-6O63UFT\SQLEXPRESS01;' 
    r'DATABASE=AutoPartsDB;'
    r'Trusted_Connection=yes;'
)
engine = sa.create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

st.set_page_config(page_title="AutoParts Pro Manager", layout="wide")
st.title("🚗 AutoParts Pro: Management System")

menu = ["Inventory View", "Process Sale", "Inventory Management", "Customer Management", "Monthly Report"]
choice = st.sidebar.selectbox("Navigation", menu)

if choice == "Inventory View":
    st.subheader("Current Stock Levels")
    df = pd.read_sql("SELECT * FROM Parts", engine)
    st.dataframe(df, use_container_width=True)
    
    low_stock = df[df['StockQTY'] < 10]
    if not low_stock.empty:
        st.warning("⚠️ Items requiring restock!")
        st.table(low_stock)

elif choice == "Process Sale":
    st.subheader("New Transaction 🛒")

    if 'cart' not in st.session_state:
        st.session_state['cart'] = []

    customers_df = pd.read_sql("SELECT CustomerID, FullName FROM Customers", engine)
    parts_df = pd.read_sql("SELECT PartID, PartName, CarModel, StockQTY, Price FROM Parts", engine)

    selected_cust_name = st.selectbox("Select Customer", customers_df['FullName'].tolist())
    cust_id = customers_df[customers_df['FullName'] == selected_cust_name]['CustomerID'].values[0]

    st.divider()

    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        unique_models = parts_df['CarModel'].unique().tolist()
        selected_car = st.selectbox("Filter by Car Model", unique_models)
    
    with col2:
        filtered_parts = parts_df[parts_df['CarModel'] == selected_car]
        selected_part_name = st.selectbox("Select Part", filtered_parts['PartName'].tolist())
    
    with col3:
        qty = st.number_input("Quantity", min_value=1, value=1)

    if selected_part_name:
        item_details = filtered_parts[filtered_parts['PartName'] == selected_part_name].iloc[0]
        
        price = round(float(item_details['Price']), 2)
        max_stock = int(item_details['StockQTY'])
        line_total = round(price * qty, 2)

        st.info(f"💰 **Unit Price:** R{price:,.2f} | **Line Total:** R{line_total:,.2f} | **Available:** {max_stock}")

        if st.button("➕ Add to Cart"):
            if qty <= max_stock:
                st.session_state['cart'].append({
                    "PartID": int(item_details['PartID']),
                    "PartName": selected_part_name,
                    "CarModel": selected_car,
                    "Qty": qty,
                    "Price": price,
                    "Total": line_total
                })
                st.toast(f"Added {selected_part_name} to cart!")
                st.rerun()
            else:
                st.error("Not enough stock!")

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
        st.markdown(f"## **Grand Total: :green[R {grand_total:,.2f}]**")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("🗑️ Clear Cart"):
                st.session_state['cart'] = []
                st.rerun()
        
        with c2:
            if st.button("✅ Complete Sale", type="primary"):
                try:
                    with engine.begin() as conn:
                        for item in st.session_state['cart']:
                            conn.execute(sa.text(
                                "UPDATE Parts SET StockQTY = StockQTY - :q WHERE PartID = :p"), 
                                {"q": item['Qty'], "p": item['PartID']}
                            )
                            conn.execute(sa.text(
                                "INSERT INTO Sales (CustomerID, PartsID, QuantitySold, TotalAmount) VALUES (:c, :p, :q, :t)"),
                                {"c": int(cust_id), "p": item['PartID'], "q": item['Qty'], "t": item['Total']}
                            )
                    
                    st.session_state['cart'] = [] 
                    st.success("Successfully processed transaction!")
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    st.error(f"Transaction failed: {e}")
    else:
        st.info("Your cart is empty.")

elif choice == "Customer Management":
    st.subheader("👥 Customer Relationship Management")
    tab1, tab2, tab3 = st.tabs(["View Customers", "Add New Customer", "Remove Customer"])

    with tab1:
        st.write("### 📇 Active Customer Directory")
        cust_df = pd.read_sql("SELECT CustomerID, FullName, Email, Phone FROM Customers", engine)
        st.dataframe(cust_df, use_container_width=True)

    with tab2:
        st.write("### ➕ Register New Customer")
        with st.form("add_cust_form"):
            new_cust_name = st.text_input("Full Name")
            new_cust_email = st.text_input("Email Address")
            new_cust_phone = st.text_input("Phone Number")
            
            submit_cust = st.form_submit_button("Add Customer")
            
            if submit_cust:
                if new_cust_name == "":
                    st.error("Full Name is required.")
                else:
                    with engine.begin() as conn:
                        conn.execute(
                            sa.text("INSERT INTO Customers (FullName, Email, Phone) VALUES (:n, :e, :p)"),
                            {"n": new_cust_name, "e": new_cust_email, "p": new_cust_phone}
                        )
                    st.success(f"✅ {new_cust_name} added successfully!")
                    st.rerun()

    with tab3:
        st.write("### 🗑️ Remove Customer Profile")
        st.warning("Action cannot be undone. Be careful!")
        
        cust_list_df = pd.read_sql("SELECT CustomerID, FullName FROM Customers", engine)
        cust_to_del = st.selectbox("Select Customer to Remove", cust_list_df['FullName'].tolist())
        
        if st.button("Delete Customer Permanently"):
            target_id = cust_list_df[cust_list_df['FullName'] == cust_to_del]['CustomerID'].values[0]
            
            try:
                with engine.begin() as conn:
                    conn.execute(sa.text("DELETE FROM Customers WHERE CustomerID = :id"), {"id": int(target_id)})
                st.success(f"🗑️ Record for {cust_to_del} has been deleted.")
                st.rerun()
            except Exception as e:
                st.error("❌ Cannot delete customer because they have existing sales records. You must keep them for audit purposes.")

elif choice == "Monthly Report":
    st.subheader("📊 Financial Overview & Month-End Report")
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
            total_revenue = df_sales['Revenue'].sum()
            total_units = df_sales['Units'].sum()
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric(label="Total Monthly Revenue", value=f"R {total_revenue:,.2f}")
            with col2:
                st.metric(label="Total Units Sold", value=int(total_units))
            
            st.divider() 
            
            st.write("### Revenue by Product")
            st.bar_chart(data=df_sales, x="PartName", y="Revenue")
            
            st.write("### Detailed Breakdown")
            st.dataframe(df_sales, use_container_width=True)
            
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
    st.subheader("📦 Stock Control Center")
    tab1, tab2 = st.tabs(["Restock Existing Item", "Add New Product"])

    with tab1:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.write("### 📋 Current Inventory Overview")
            
            stock_df = pd.read_sql("SELECT PartName, CarModel, StockQTY, Price FROM Parts", engine)
            
            def highlight_low(s):
                return ['color: red; font-weight: bold' if v < 10 else '' for v in s]

            st.dataframe(
                stock_df.style
                .format({"Price": "R {:.2f}"}) 
                .apply(highlight_low, subset=['StockQTY']), 
                use_container_width=True
            )

        with col2:
            st.write("### ➕ Update Stock")
            st.info("Select an item from the list to increase quantity.")
            
            stock_df['DisplayName'] = stock_df['PartName'] + " (" + stock_df['CarModel'] + ")"
            part_list = stock_df['DisplayName'].tolist()
            
            selected_display_name = st.selectbox("Select Part to Restock", part_list)
            add_qty = st.number_input("Quantity to Add", min_value=1, value=10)

            if st.button("Confirm Restock"):
                
                part_name = selected_display_name.split(" (")[0]
                car_model = selected_display_name.split(" (")[1].replace(")", "")

                with engine.begin() as conn:
                    conn.execute(
                        sa.text("UPDATE Parts SET StockQty = StockQty + :q WHERE PartName = :p AND CarModel = :m"),
                        {"q": add_qty, "p": part_name, "m": car_model}
                    )
                
                st.success(f"✅ Added {add_qty} units to {part_name}!")
                st.rerun()

    with tab2:
        st.write("### 🆕 Add New Product to Database")
        with st.form("new_part_form"):
            col_a, col_b = st.columns(2)
            with col_a:
                new_name = st.text_input("Part Name (e.g., Brake Pad)")
                new_model = st.text_input("Car Model (e.g., VW Polo)")
            with col_b:
                new_price = st.number_input("Selling Price (R)", min_value=0.0, format="%.2f")
                new_qty = st.number_input("Initial Stock Quantity", min_value=0)
            
            submit_new = st.form_submit_button("Add to Inventory")
            
            if submit_new:
                if new_name == "" or new_model == "":
                    st.error("Please enter both Part Name and Car Model.")
                else:
                    with engine.begin() as conn:
                        conn.execute(
                            sa.text("""INSERT INTO Parts (PartName, CarModel, Price, StockQty) 
                                       VALUES (:n, :m, :p, :q)"""),
                            {"n": new_name, "m": new_model, "p": new_price, "q": new_qty}
                        )
                    st.success(f"🚀 {new_name} for {new_model} has been added to the system!")
                    st.rerun()
