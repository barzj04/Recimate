import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta, date

# --- AUTH CONFIG ---
USERS = {
    "arleen": {"password": "pass1", "display": "Arleen"},
    "Rachel": {"password": "pass2", "display": "Roommate"},
}
ROOMMATE_PAIRS = {
    "arleen": "Rachel",
    "Rachel": "arleen",
}

# --- SUPABASE ---
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"].strip()
    key = st.secrets["SUPABASE_KEY"].strip()
    return create_client(url, key)

supabase = init_supabase()
DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# --- WEEK HELPERS ---
def get_week_dates(offset=0):
    today = date.today()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=offset)
    return [monday + timedelta(days=i) for i in range(7)]

def format_week_label(dates):
    return f"{dates[0].strftime('%d %b')} – {dates[6].strftime('%d %b %Y')}"

# --- DATA ACTIONS ---
def fetch_schedules():
    response = supabase.table("schedules").select("*").execute()
    return {row["roommate"]: row["schedule"] for row in response.data}

def update_db_schedule(name, schedule_dict):
    supabase.table("schedules").upsert({"roommate": name, "schedule": schedule_dict}).execute()

def fetch_recipes():
    response = supabase.table("recipes").select("*").order("created_at", desc=False).execute()
    return response.data

def add_db_recipe(text, link, when_to_cook):
    supabase.table("recipes").insert({
        "idea": text,
        "link": link if link else None,
        "when_to_cook": when_to_cook if when_to_cook else None
    }).execute()

def delete_db_recipe(recipe_id):
    supabase.table("recipes").delete().eq("id", recipe_id).execute()

def fetch_groceries():
    response = supabase.table("groceries").select("*").order("created_at", desc=False).execute()
    return response.data

def add_grocery(item, price, paid_by):
    supabase.table("groceries").insert({
        "item": item,
        "price": price,
        "paid_by": paid_by,
        "paid_back": False
    }).execute()

def toggle_paid_back(grocery_id, current_val):
    supabase.table("groceries").update({"paid_back": not current_val}).eq("id", grocery_id).execute()

def delete_grocery(grocery_id):
    supabase.table("groceries").delete().eq("id", grocery_id).execute()

# --- PAGE CONFIG ---
st.set_page_config(page_title="Kitchen Co-op", page_icon="🍳", layout="wide")

# --- LOGIN ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None

if not st.session_state.logged_in:
    st.title("🍳 Kitchen Co-op")
    st.subheader("Please log in to continue")
    st.write("")
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        username_input = st.text_input("Username").strip().lower()
        password_input = st.text_input("Password", type="password")
        if st.button("Log In", type="primary", use_container_width=True):
            if username_input in USERS and USERS[username_input]["password"] == password_input:
                st.session_state.logged_in = True
                st.session_state.username = username_input
                st.session_state.week_offset = 0
                st.rerun()
            else:
                st.error("Wrong username or password.")
    st.stop()

# --- SESSION VARS ---
username = st.session_state.username
display_name = USERS[username]["display"]
partner_username = ROOMMATE_PAIRS[username]
partner_display = USERS[partner_username]["display"]

if "week_offset" not in st.session_state:
    st.session_state.week_offset = 0
if "db_schedules" not in st.session_state:
    st.session_state.db_schedules = fetch_schedules()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown(f"### 👤 {display_name}")
    st.caption(f"Paired with: {partner_display}")
    st.divider()
    now = datetime.now()
    st.caption(f"🕐 {now.strftime('%A, %d %b %Y')}")
    st.caption(f"⏰ {now.strftime('%I:%M %p')}")
    st.divider()
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.session_state.db_schedules = fetch_schedules()
        st.rerun()
    st.divider()
    if st.button("🚪 Log Out", use_container_width=True):
        for key in ["logged_in", "username", "db_schedules", "week_offset"]:
            st.session_state.pop(key, None)
        st.rerun()

# --- MAIN ---
st.title("🍳 Kitchen Co-op")
st.subheader(f"Hey {display_name}! Let's coordinate meals 🥘")

tab1, tab2, tab3 = st.tabs(["📅 Schedule", "💡 Recipes", "🛒 Groceries"])

# ──────────────────────────────────────────
# TAB 1: SCHEDULE
# ──────────────────────────────────────────
with tab1:
    # Week navigation
    col_prev, col_label, col_next = st.columns([1, 3, 1])
    with col_prev:
        if st.button("◀ Prev Week"):
            st.session_state.week_offset -= 1
            st.rerun()
    with col_next:
        if st.button("Next Week ▶"):
            st.session_state.week_offset += 1
            st.rerun()
    with col_label:
        week_dates = get_week_dates(st.session_state.week_offset)
        st.markdown(f"<h4 style='text-align:center; margin:0'>📆 {format_week_label(week_dates)}</h4>", unsafe_allow_html=True)
        if st.session_state.week_offset != 0:
            if st.button("↩ Back to This Week", use_container_width=True):
                st.session_state.week_offset = 0
                st.rerun()

    st.write("")

    db_schedules = st.session_state.db_schedules
    my_sched = db_schedules.get(username, {})
    partner_sched = db_schedules.get(partner_username, {})

    my_updates = {}
    st.markdown(f"### 👤 Your Availability This Week")
    st.caption("Tick the meals you're free for each day.")

    for i, day in enumerate(DAYS_OF_WEEK):
        day_date = week_dates[i]
        is_today = day_date == date.today()
        label = f"**{day}** — {day_date.strftime('%d %b')}"
        if is_today:
            label += " 🟢 *Today*"
        st.markdown(label)
        c1, c2 = st.columns(2)
        with c1:
            l_val = st.checkbox("🌞 Lunch", value=my_sched.get(day, {}).get("Lunch", False), key=f"my_l_{day}")
        with c2:
            d_val = st.checkbox("🌙 Dinner", value=my_sched.get(day, {}).get("Dinner", False), key=f"my_d_{day}")
        my_updates[day] = {"Lunch": l_val, "Dinner": d_val}

    st.write("")
    if st.button("💾 Save My Schedule", type="primary", use_container_width=True):
        update_db_schedule(username, my_updates)
        st.session_state.db_schedules = fetch_schedules()
        st.success("✅ Schedule saved!")
        st.rerun()

    st.write("---")

    # Matches
    st.markdown(f"### 🤝 Overlap with {partner_display}")
    db_schedules = st.session_state.db_schedules
    my_fresh = db_schedules.get(username, {})
    partner_fresh = db_schedules.get(partner_username, {})

    lunch_matches = [d for d in DAYS_OF_WEEK if my_fresh.get(d, {}).get("Lunch") and partner_fresh.get(d, {}).get("Lunch")]
    dinner_matches = [d for d in DAYS_OF_WEEK if my_fresh.get(d, {}).get("Dinner") and partner_fresh.get(d, {}).get("Dinner")]

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        if lunch_matches:
            st.success(f"🌞 **Shared Lunch:** {', '.join(lunch_matches)}")
        else:
            st.warning("⏳ No shared lunch slots yet.")
    with col_m2:
        if dinner_matches:
            st.success(f"🌙 **Shared Dinner:** {', '.join(dinner_matches)}")
        else:
            st.warning("⏳ No shared dinner slots yet.")
    st.caption(f"💡 Hit **Refresh Data** in the sidebar to see {partner_display}'s latest schedule.")

# ──────────────────────────────────────────
# TAB 2: RECIPES
# ──────────────────────────────────────────
with tab2:
    st.header("💡 Shared Recipe Ideas")

    with st.form("recipe_form", clear_on_submit=True):
        new_recipe = st.text_input("Dish name or description *", placeholder="e.g. Spaghetti Aglio e Olio")
        col_a, col_b = st.columns(2)
        with col_a:
            new_link = st.text_input("Recipe link (optional)", placeholder="https://...")
        with col_b:
            when_options = ["", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "Anytime"]
            new_when = st.selectbox("When to cook (optional)", options=when_options)
        submitted = st.form_submit_button("➕ Add to Pool", type="primary")
        if submitted:
            if new_recipe.strip():
                add_db_recipe(new_recipe.strip(), new_link.strip(), new_when)
                st.success("Recipe added!")
                st.rerun()
            else:
                st.warning("Please enter a dish name.")

    st.write("")
    current_recipes = fetch_recipes()
    if current_recipes:
        st.markdown("### 🛒 Brainstorm List")
        for item in current_recipes:
            col_text, col_del = st.columns([0.92, 0.08])
            with col_text:
                line = f"🍽️ **{item['idea']}**"
                if item.get("when_to_cook"):
                    line += f" — 📅 {item['when_to_cook']}"
                if item.get("link"):
                    line += f" — [🔗 Recipe]({item['link']})"
                st.markdown(line)
            with col_del:
                if st.button("🗑️", key=f"del_r_{item['id']}"):
                    delete_db_recipe(item['id'])
                    st.rerun()
    else:
        st.caption("The pool is empty. Drop some recipe ideas above!")

# ──────────────────────────────────────────
# TAB 3: GROCERIES
# ──────────────────────────────────────────
with tab3:
    st.header("🛒 Shared Groceries")

    # Add item form
    with st.form("grocery_form", clear_on_submit=True):
        col_i, col_p, col_who = st.columns([2, 1, 1])
        with col_i:
            g_item = st.text_input("Item *", placeholder="e.g. Eggs")
        with col_p:
            g_price = st.number_input("Price (RM)", min_value=0.0, step=0.10, format="%.2f")
        with col_who:
            g_paid_by = st.selectbox("Paid by", options=[display_name, partner_display])
        g_submit = st.form_submit_button("➕ Add Item", type="primary")
        if g_submit:
            if g_item.strip():
                add_grocery(g_item.strip(), g_price, g_paid_by)
                st.success("Item added!")
                st.rerun()
            else:
                st.warning("Please enter an item name.")

    st.write("")
    groceries = fetch_groceries()

    if groceries:
        # Bill summary
        total = sum(g.get("price", 0) or 0 for g in groceries)
        each_owes = total / 2

        paid_by_me = sum(g.get("price", 0) or 0 for g in groceries if g.get("paid_by") == display_name)
        paid_by_partner = sum(g.get("price", 0) or 0 for g in groceries if g.get("paid_by") == partner_display)

        st.markdown("### 💰 Bill Summary")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Total Spent", f"RM {total:.2f}")
        with c2:
            st.metric(f"Paid by {display_name}", f"RM {paid_by_me:.2f}")
        with c3:
            st.metric(f"Paid by {partner_display}", f"RM {paid_by_partner:.2f}")

        st.write("")

        # Who owes who
        balance = paid_by_me - each_owes
        if abs(balance) < 0.01:
            st.success("✅ All settled up!")
        elif balance > 0:
            st.info(f"💸 **{partner_display}** owes **{display_name}** RM {balance:.2f}")
        else:
            st.info(f"💸 **{display_name}** owes **{partner_display}** RM {abs(balance):.2f}")

        st.write("---")
        st.markdown("### 🧾 Grocery List")

        # Header row
        h1, h2, h3, h4, h5 = st.columns([2.5, 1, 1.2, 1.5, 0.5])
        h1.markdown("**Item**")
        h2.markdown("**Price**")
        h3.markdown("**Paid by**")
        h4.markdown("**Paid back ✓**")
        h5.markdown("**Del**")

        for g in groceries:
            c1, c2, c3, c4, c5 = st.columns([2.5, 1, 1.2, 1.5, 0.5])
            with c1:
                st.write(g["item"])
            with c2:
                st.write(f"RM {g.get('price', 0):.2f}")
            with c3:
                st.write(g.get("paid_by", "-"))
            with c4:
                paid_back = g.get("paid_back", False)
                if paid_back:
                    st.markdown("✅ Paid back")
                else:
                    if st.button("Mark as paid back", key=f"pb_{g['id']}"):
                        toggle_paid_back(g["id"], paid_back)
                        st.rerun()
            with c5:
                if st.button("🗑️", key=f"del_g_{g['id']}"):
                    delete_grocery(g["id"])
                    st.rerun()
    else:
        st.caption("No groceries added yet. Add your first item above!")
