import streamlit as st
import pandas as pd
from dataclasses import dataclass
from datetime import date as dt_date, datetime

# =========================
# Helper Functions
# =========================
def month_key_from_date(d):
    return d.strftime("%Y-%m")

def calc_status(spent, limit):
    if limit <= 0:
        return "ℹ️"
    ratio = spent / limit
    if ratio < 0.50:
        return "✅"
    if ratio < 0.80:
        return "⚠️"
    if ratio < 1.00:
        return "🔶"
    return "🛑"

def get_progress_color(ratio):
    if ratio < 0.50:
        return "#4CAF50"  # Green (Safe)
    elif ratio < 0.80:
        return "#FFC107"  # Yellow (Alert)
    elif ratio < 1.00:
        return "#FF9800"  # Orange (Warning)
    else:
        return "#F44336"  # Red (Danger)

# =========================
# Data Models
# =========================
@dataclass
class Category:
    name: str
    limit_type: str  # "percent" or "fixed"
    value: float     # percent or SAR

    def calc_limit(self, monthly_budget):
        if self.limit_type == "percent":
            return monthly_budget * (self.value / 100.0)
        return self.value

    def display_limit(self):
        if self.limit_type == "percent":
            return f"{self.value:g}%"
        return f"{self.value:g} SAR"

@dataclass
class Expense:
    expense_id: int
    d: dt_date
    amount: float
    category: str
    description: str

class BudgetMonth:
    def __init__(self, month_key):
        self.month_key = month_key
        self.budget = None
        self.categories = {}
        self.expenses = []
        self._next_expense_id = 1

    def is_setup(self):
        return self.budget is not None and len(self.categories) > 0

    def set_budget(self, new_budget):
        self.budget = new_budget

    def add_category(self, cat):
        name = cat.name.strip()
        if not name or name in self.categories:
            return False
        self.categories[name] = cat
        return True

    def update_category_limit(self, name, limit_type, value):
        if name not in self.categories:
            return False
        self.categories[name].limit_type = limit_type
        self.categories[name].value = value
        return True

    def category_has_expenses(self, name):
        return any(e.category == name for e in self.expenses)

    def delete_category(self, name, move_to_other):
        if name not in self.categories:
            return False, "❌ Category not found."
        if self.category_has_expenses(name):
            if not move_to_other:
                return False, "ℹ️ Deletion cancelled."
            if "Other" not in self.categories:
                self.categories["Other"] = Category("Other", "fixed", 10**18)
            for e in self.expenses:
                if e.category == name:
                    e.category = "Other"
        del self.categories[name]
        return True, f"✅ Category '{name}' deleted successfully."

    def add_expense(self, d, amount, category, description):
        exp = Expense(
            expense_id=self._next_expense_id,
            d=d,
            amount=amount,
            category=category,
            description=description.strip()
        )
        self._next_expense_id += 1
        self.expenses.append(exp)
        return exp

    def delete_expense_by_id(self, expense_id):
        for i, e in enumerate(self.expenses):
            if e.expense_id == expense_id:
                self.expenses.pop(i)
                return True
        return False

    def get_expense_by_id(self, expense_id):
        for e in self.expenses:
            if e.expense_id == expense_id:
                return e
        return None

    def total_expenses(self):
        return sum(e.amount for e in self.expenses)

    def total_by_category(self):
        totals = {}
        for e in self.expenses:
            totals[e.category] = totals.get(e.category, 0.0) + e.amount
        return totals

    def top_and_lowest_category(self):
        totals = self.total_by_category()
        if not totals:
            return None, None
        top = max(totals.items(), key=lambda x: x[1])
        low = min(totals.items(), key=lambda x: x[1])
        return top, low

    def highest_spending_day(self):
        if not self.expenses:
            return None
        daily = {}
        for e in self.expenses:
            daily[e.d] = daily.get(e.d, 0.0) + e.amount
        return max(daily.items(), key=lambda x: x[1])

    def status_summary_counts(self):
        counts = {"✅": 0, "⚠️": 0, "🔶": 0, "🛑": 0}
        if self.budget is None:
            return counts
        totals = self.total_by_category()
        for name, cat in self.categories.items():
            limit = cat.calc_limit(self.budget)
            spent = totals.get(name, 0.0)
            icon = calc_status(spent, limit)
            if icon in counts:
                counts[icon] += 1
        return counts

class BudgetTrackerApp:
    def __init__(self):
        self.months = {}
        self.default_categories = [
            Category("Expenses", "percent", 50.0),
            Category("Entertainment", "percent", 10.0),
            Category("Charity", "percent", 10.0),
            Category("Savings", "percent", 10.0),
            Category("Investment", "percent", 10.0),
            Category("Education", "percent", 10.0),
        ]

    def get_month(self, month_key):
        if month_key not in self.months:
            self.months[month_key] = BudgetMonth(month_key)
        return self.months[month_key]

# =========================
# Streamlit UI Components
# =========================
def init_session():
    if 'app' not in st.session_state:
        st.session_state.app = BudgetTrackerApp()

def main():
    st.set_page_config(page_title="Budget Tracker", page_icon="💰", layout="wide")
    init_session()
    app = st.session_state.app

    st.title("💰 Personal Budget Tracker")

    # Sidebar for global month selection
    st.sidebar.header("Navigation")
    today_key = month_key_from_date(dt_date.today())
    
    # Ensure current month exists in dropdown options
    app.get_month(today_key) 
    month_options = sorted(list(app.months.keys()), reverse=True)
    selected_month_key = st.sidebar.selectbox("Select Month Context", month_options)
    
    current_month = app.get_month(selected_month_key)

    # Main UI Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["⚙️ Month Setup", "➕ Add Expense", "📊 Overview", "🛠️ Settings"])

    # ------------------ TAB 1: Setup ------------------

    # with tab1:
    #     st.header(f"Setup for {selected_month_key}")
    #     if current_month.is_setup():
    #         st.success("✅ This month is already set up! Head to Settings if you need to make changes.")
    #     else:
    #         budget_input = st.number_input("Monthly Budget (SAR)", min_value=1.0, value=8000.0, step=100.0)
    #         cat_choice = st.radio("Category Setup", ["Use Default Categories", "Create Custom Categories"])
            
    #         if cat_choice == "Use Default Categories":
    #             st.write("**Default Categories Preview:**")
    #             preview_data = [{"Category": c.name, "Type": c.limit_type.title(), "Limit": c.display_limit(), "Est. SAR": c.calc_limit(budget_input)} for c in app.default_categories]
    #             st.dataframe(pd.DataFrame(preview_data), hide_index=True)
                
    #             if st.button("Save Month Setup"):
    #                 current_month.set_budget(budget_input)
    #                 for c in app.default_categories:
    #                     current_month.add_category(Category(c.name, c.limit_type, c.value))
    #                 st.success("✅ Month setup saved!")
    #                 st.rerun()
    #         else:
    #             st.info("Custom categories can be added individually in the Settings tab after setting the initial budget.")
    #             if st.button("Save Budget & Proceed to Settings"):
    #                 current_month.set_budget(budget_input)
    #                 st.success("✅ Budget saved! Please go to the Settings tab to add your custom categories.")
    #                 st.rerun()


    # ------------------ TAB 1: Setup ------------------
    with tab1:
        st.header(f"Setup for {selected_month_key}")
        if current_month.is_setup():
            st.success("✅ This month is already set up! Head to Settings if you need to make changes.")
        else:
            budget_input = st.number_input("Monthly Budget (SAR)", min_value=1.0, value=8000.0, step=100.0)
            cat_choice = st.radio("Category Setup", ["Use Default Categories", "Create Custom Categories"])
            
            if cat_choice == "Use Default Categories":
                st.write("**Default Categories Preview:**")
                preview_data = [{"Category": c.name, "Type": c.limit_type.title(), "Limit": c.display_limit(), "Est. SAR": c.calc_limit(budget_input)} for c in app.default_categories]
                st.dataframe(pd.DataFrame(preview_data), hide_index=True)
                
                if st.button("Save Month Setup"):
                    current_month.set_budget(budget_input)
                    for c in app.default_categories:
                        current_month.add_category(Category(c.name, c.limit_type, c.value))
                    st.success("✅ Month setup saved!")
                    st.rerun()
            else:

                st.subheader("Define Custom Categories")
                
                if 'temp_cats' not in st.session_state:
                    st.session_state.temp_cats = []

                # 1. Calculate how much is already allocated in SAR
                allocated_sar = sum(c.calc_limit(budget_input) for c in st.session_state.temp_cats)
                remaining_sar = budget_input - allocated_sar
                remaining_pct = (remaining_sar / budget_input) * 100 if budget_input > 0 else 0

                # Display remaining allocation info
                col_info1, col_info2 = st.columns(2)
                col_info1.metric("Remaining Amount", f"{max(0.0, remaining_sar):.2f} SAR")
                col_info2.metric("Remaining Percentage", f"{max(0.0, remaining_pct):.2f}%")

                # Form to add a category
                with st.form("custom_cat_adder", clear_on_submit=True):
                    col1, col2, col3 = st.columns([3, 2, 2])
                    new_name = col1.text_input("Category Name")
                    new_type = col2.selectbox("Type", ["percent", "fixed"])
                    new_val = col3.number_input("Value", min_value=0.0, step=1.0)
                    
                    if st.form_submit_button("➕ Add to List"):
                        # Requirement 1: Prevent zero value
                        if new_val <= 0:
                            st.error("❌ Value must be greater than zero.")
                        elif not new_name.strip():
                            st.error("❌ Category name is required.")
                        else:
                            # Calculate what this new entry would cost in SAR
                            requested_sar = new_val if new_type == "fixed" else (new_val / 100 * budget_input)
                            
                            # Requirement 2 & 3: Prevent exceeding remaining budget
                            if requested_sar > (remaining_sar + 1e-9): # 1e-9 handles floating point precision
                                if new_type == "percent":
                                    st.error(f"❌ Limits exceeded. Max available: {remaining_pct:.2f}%")
                                else:
                                    st.error(f"❌ Limits exceeded. Max available: {remaining_sar:.2f} SAR")
                            else:
                                st.session_state.temp_cats.append(Category(new_name, new_type, new_val))
                                st.rerun()

                # Display and Save logic
                if st.session_state.temp_cats:
                    st.write("**Your Custom Categories:**")
                    temp_df = pd.DataFrame([
                        {"Category": c.name, "Type": c.limit_type, "Limit": c.display_limit(), "SAR Value": c.calc_limit(budget_input)} 
                        for c in st.session_state.temp_cats
                    ])
                    st.dataframe(temp_df, hide_index=True)

                    if st.button("Clear List"):
                        st.session_state.temp_cats = []
                        st.rerun()

                    if st.button("Finalize Setup & Save All"):
                        current_month.set_budget(budget_input)
                        for c in st.session_state.temp_cats:
                            current_month.add_category(c)
                        st.session_state.temp_cats = [] 
                        st.success("✅ Custom setup saved!")
                        st.rerun()



    # ------------------ TAB 2: Add Expense ------------------
    with tab2:
        st.header("Add a New Expense")
        if not current_month.is_setup():
            st.warning("⚠️ Please set up this month in the 'Month Setup' tab first.")
        else:
            with st.form("add_expense_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    exp_date = st.date_input("Expense Date", value=dt_date.today())
                    exp_cat = st.selectbox("Category", list(current_month.categories.keys()))
                with col2:

                    exp_amount = st.number_input("Amount (SAR)", min_value=0.00, value=0.00, step=10.0)
                    exp_desc = st.text_input("Description")
                
                submit_expense = st.form_submit_button("Save Expense")
                
                if submit_expense:
                    # Add the check for zero value here
                    if exp_amount <= 0:
                        st.error("❌ The expense amount must be greater than 0.00 SAR.")
                    else:

                        target_month_key = month_key_from_date(exp_date)
                        target_month = app.get_month(target_month_key)
                        
                        if not target_month.is_setup():
                            st.error(f"❌ The month {target_month_key} is not set up. Set it up first.")
                        else:
                            current_total = target_month.total_expenses()
                            if current_total + exp_amount > target_month.budget + 1e-9:
                                st.error(f"🛑 Monthly budget exceeded! You only have {target_month.budget - current_total:.2f} SAR left.")
                            else:
                                target_month.add_expense(exp_date, exp_amount, exp_cat, exp_desc)
                                st.success(f"✅ Expense of {exp_amount:.2f} SAR added to {exp_cat} on {exp_date}!")
                                st.rerun()

    # ------------------ TAB 3: Overview ------------------
    with tab3:
        st.header(f"Expenses Overview ({selected_month_key})")
        if not current_month.is_setup():
            st.warning("⚠️ Month not set up yet.")
        else:
            total_spent = current_month.total_expenses()
            remaining = current_month.budget - total_spent
            
            # Metrics
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Budget", f"{current_month.budget:.2f} SAR")
            col2.metric("Total Spent", f"{total_spent:.2f} SAR")
            col3.metric("Remaining", f"{remaining:.2f} SAR", delta=f"{-total_spent:.2f} SAR", delta_color="inverse")
            
            st.divider()
            
            # Category Progress


            # st.subheader("Category Limits & Progress")
            # totals = current_month.total_by_category()
            # for cat_name, cat in current_month.categories.items():
            #     spent = totals.get(cat_name, 0.0)
            #     limit = cat.calc_limit(current_month.budget)
            #     icon = calc_status(spent, limit)
            #     pct = 0.0 if limit <= 0 else (spent / limit)
                
            #     st.write(f"**{cat_name}** {icon} ({spent:.2f} / {limit:.2f} SAR)")
            #     # Cap at 1.0 for Streamlit progress bar to prevent errors
            #     st.progress(min(pct, 1.0))
            
            # st.divider()
            




            st.subheader("Category Limits & Progress")
            totals = current_month.total_by_category()
            for cat_name, cat in current_month.categories.items():
                spent = totals.get(cat_name, 0.0)
                limit = cat.calc_limit(current_month.budget)
                icon = calc_status(spent, limit)
                pct = 0.0 if limit <= 0 else (spent / limit)
                
                st.write(f"**{cat_name}** {icon} ({spent:.2f} / {limit:.2f} SAR)")
                
                # Get the dynamic color based on spending ratio
                bar_color = get_progress_color(pct)
                
                # Cap the visual width at 100% so it doesn't break the container
                visual_width = min(pct * 100, 100)
                
                # Create a custom HTML progress bar
                custom_progress_html = f"""
                <div style="width: 100%; background-color: #444444; border-radius: 5px; margin-bottom: 20px;">
                    <div style="width: {visual_width}%; height: 8px; background-color: {bar_color}; border-radius: 5px; transition: width 0.5s;"></div>
                </div>
                """
                st.markdown(custom_progress_html, unsafe_allow_html=True)




            # # Expense Table
            st.subheader("Recent Expenses")
            if not current_month.expenses:
                st.info("No expenses logged yet.")
            else:
                df = pd.DataFrame([vars(e) for e in current_month.expenses])
                df.rename(columns={'expense_id': 'ID', 'd': 'Date', 'amount': 'Amount (SAR)', 'category': 'Category', 'description': 'Description'}, inplace=True)
                st.dataframe(df, use_container_width=True, hide_index=True)




    # ------------------ TAB 4: Settings ------------------
    with tab4:
        st.header("Settings")
        if not current_month.is_setup():
            st.warning("⚠️ Please complete Month Setup first.")
        else:
            with st.expander("Update Monthly Budget"):
                new_budget = st.number_input("New Budget (SAR)", min_value=1.0, value=current_month.budget, step=100.0)
                if st.button("Update Budget"):
                    current_month.set_budget(new_budget)
                    st.success("✅ Budget updated!")
                    st.rerun()

            with st.expander("Manage Categories"):




                # # Add Category Form
                # st.subheader("Add New Category")
                # with st.form("add_cat_form"):
                #     new_c_name = st.text_input("Category Name")
                #     new_c_type = st.selectbox("Limit Type", ["percent", "fixed"])
                #     new_c_val = st.number_input("Value", min_value=0.0, step=10.0)
                #     if st.form_submit_button("Add Category"):
                #         if current_month.add_category(Category(new_c_name, new_c_type, new_c_val)):
                #             st.success(f"✅ {new_c_name} added!")
                #             st.rerun()
                #         else:
                #             st.error("❌ Invalid name or category already exists.")
                
                # st.divider()
                # # Delete Category Form
                # st.subheader("Delete Category")
                # del_c_name = st.selectbox("Select Category to Delete", list(current_month.categories.keys()))
                # del_move = st.checkbox("Move existing expenses to 'Other'?", value=True)
                # if st.button("Delete Selected Category"):
                #     ok, msg = current_month.delete_category(del_c_name, del_move)
                #     if ok:
                #         st.success(msg)
                #         st.rerun()
                #     else:
                #         st.error(msg)


                st.subheader("Current Allocation")
                
                # 1. Calculate real-time allocation
                # We calculate based on existing categories in the current_month object
                allocated_sar = sum(c.calc_limit(current_month.budget) for c in current_month.categories.values())
                remaining_sar = current_month.budget - allocated_sar
                remaining_pct = (remaining_sar / current_month.budget) * 100 if current_month.budget > 0 else 0

                col_info1, col_info2 = st.columns(2)
                col_info1.metric("Remaining Amount", f"{max(0.0, remaining_sar):.2f} SAR")
                col_info2.metric("Remaining Percentage", f"{max(0.0, remaining_pct):.1f}%")

                st.divider()

                # 2. Add New Category Form (Same logic as Setup)
                st.write("**Add New Category**")
                with st.form("settings_cat_adder", clear_on_submit=True):
                    col1, col2, col3 = st.columns([3, 2, 2])
                    new_name = col1.text_input("Category Name")
                    new_type = col2.selectbox("Type", ["percent", "fixed"])
                    new_val = col3.number_input("Value", min_value=0.0, step=1.0)
                    
                    if st.form_submit_button("➕ Add Category"):
                        if new_val <= 0:
                            st.error("❌ Value must be greater than zero.")
                        elif not new_name.strip():
                            st.error("❌ Category name is required.")
                        elif new_name in current_month.categories:
                            st.error("❌ A category with this name already exists.")
                        else:
                            requested_sar = new_val if new_type == "fixed" else (new_val / 100 * current_month.budget)
                            
                            if requested_sar > (remaining_sar + 1e-9):
                                if new_type == "percent":
                                    st.error(f"❌ Limits exceeded. Max available: {remaining_pct:.2f}%")
                                else:
                                    st.error(f"❌ Limits exceeded. Max available: {remaining_sar:.2f} SAR")
                            else:
                                if current_month.add_category(Category(new_name, new_type, new_val)):
                                    st.success(f"✅ {new_name} added!")
                                    st.rerun()

                st.divider()

                # 3. Delete Category Section
                st.write("**Delete Category**")
                if not current_month.categories:
                    st.info("No categories to delete.")
                else:
                    del_c_name = st.selectbox("Select Category to Remove", list(current_month.categories.keys()))
                    del_move = st.checkbox("Move existing expenses to 'Other'?", value=True)
                    
                    if st.button("🗑️ Delete Selected Category"):
                        ok, msg = current_month.delete_category(del_c_name, del_move)
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)






            with st.expander("Manage Expenses (Edit/Delete)"):
                if not current_month.expenses:
                    st.info("No expenses to manage.")
                else:
                    exp_options = {e.expense_id: f"ID {e.expense_id}: {e.d} - {e.category} - {e.amount} SAR" for e in current_month.expenses}
                    selected_exp_id = st.selectbox("Select Expense", list(exp_options.keys()), format_func=lambda x: exp_options[x])
                    
                    target_exp = current_month.get_expense_by_id(selected_exp_id)
                    
                    col_del, col_edit = st.columns(2)
                    with col_del:
                        if st.button("🗑️ Delete Expense", type="primary"):
                            current_month.delete_expense_by_id(selected_exp_id)
                            st.success("✅ Expense deleted.")
                            st.rerun()
                    
                    st.write("---")
                    st.write("**Edit Expense details:**")
                    with st.form("edit_exp_form"):
                        edit_amt = st.number_input("New Amount", min_value=0.01, value=float(target_exp.amount), step=10.0)
                        edit_cat = st.selectbox("New Category", list(current_month.categories.keys()), index=list(current_month.categories.keys()).index(target_exp.category))
                        edit_desc = st.text_input("New Description", value=target_exp.description)
                        
                        if st.form_submit_button("💾 Save Changes"):
                            target_exp.amount = edit_amt
                            target_exp.category = edit_cat
                            target_exp.description = edit_desc
                            st.success("✅ Expense updated!")
                            st.rerun()

if __name__ == "__main__":
    main()
