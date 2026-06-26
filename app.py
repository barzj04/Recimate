import streamlit as st
from supabase import create_client, Client
from datetime import timedelta, date, datetime
from zoneinfo import ZoneInfo

# --- AUTH CONFIG ---
USERS = {
    "arleen": {"password": "pass1", "display": "Arleen"},
    "rachel": {"password": "pass2", "display": "Rachel"},
}
ROOMMATE_PAIRS = {
    "arleen": "rachel",
    "rachel": "arleen",
}

# --- SUPABASE ---
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"].strip()
    key = st.secrets["SUPABASE_KEY"].strip()
    return create_client(url, key)

supabase = init_supabase()
DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MYT = ZoneInfo("Asia/Kuala_Lumpur")

# --- WEEK HELPERS ---
def get_week_dates(offset=0):
    today = date.today()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=offset)
    return [monday + timedelta(days=i) for i in range(7)]

def format_week_label(dates):
    return f"{dates[0].strftime('%d %b')} – {dates[6].strftime('%d %b %Y')}"

# --- SCHEDULE ---
def fetch_schedules():
    response = supabase.table("schedules").select("*").execute()
    return {row["roommate"]: row["schedule"] for row in response.data}

def update_db_schedule(name, schedule_dict):
    supabase.table("schedules").upsert({"roommate": name, "schedule": schedule_dict}).execute()

# --- RECIPES ---
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

# --- GROCERIES ---
def fetch_groceries():
    response = supabase.table("groceries").select("*").order("created_at", desc=False).execute()
    return response.data

def add_grocery(item, price, paid_by):
    supabase.table("groceries").insert({
        "item": item, "price": price, "paid_by": paid_by, "paid_back": False
    }).execute()

def toggle_paid_back(grocery_id, current_val):
    supabase.table("groceries").update({"paid_back": not current_val}).eq("id", grocery_id).execute()

def delete_grocery(grocery_id):
    supabase.table("groceries").delete().eq("id", grocery_id).execute()

def clear_all_groceries():
    supabase.table("groceries").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

# --- GROCERY WISHLIST ---
def fetch_grocery_wishlist():
    response = supabase.table("grocery_wishlist").select("*").order("created_at", desc=False).execute()
    return response.data

def add_grocery_wishlist(item, added_by):
    supabase.table("grocery_wishlist").insert({"item": item, "added_by": added_by}).execute()

def delete_grocery_wishlist(item_id):
    supabase.table("grocery_wishlist").delete().eq("id", item_id).execute()

def move_to_groceries(item_id, item_name, paid_by):
    supabase.table("groceries").insert({
        "item": item_name, "price": 0.0, "paid_by": paid_by, "paid_back": False
    }).execute()
    supabase.table("grocery_wishlist").delete().eq("id", item_id).execute()

# --- PERSONAL WISHLIST ---
def fetch_personal_wishlist(owner):
    response = supabase.table("personal_wishlist").select("*").eq("owner", owner).order("created_at", desc=False).execute()
    return response.data

def add_personal_wishlist(owner, item):
    supabase.table("personal_wishlist").insert({"owner": owner, "item": item, "done": False}).execute()

def toggle_personal_wishlist(item_id, current_val):
    supabase.table("personal_wishlist").update({"done": not current_val}).eq("id", item_id).execute()

def delete_personal_wishlist(item_id):
    supabase.table("personal_wishlist").delete().eq("id", item_id).execute()

# --- PERSONAL TODO ---
def fetch_personal_todo(owner):
    response = supabase.table("personal_todo").select("*").eq("owner", owner).order("created_at", desc=False).execute()
    return response.data

def add_personal_todo(owner, task):
    supabase.table("personal_todo").insert({"owner": owner, "task": task, "done": False}).execute()

def toggle_personal_todo(task_id, current_val):
    supabase.table("personal_todo").update({"done": not current_val}).eq("id", task_id).execute()

def delete_personal_todo(task_id):
    supabase.table("personal_todo").delete().eq("id", task_id).execute()

# --- PAGE CONFIG ---
st.set_page_config(page_title="Kitchen Co-op", page_icon="🍳", layout="wide")

st.markdown("""
    <style>
        [data-testid="stSidebar"] { display: none; }
        [data-testid="collapsedControl"] { display: none; }
        .done-item { text-decoration: line-through; color: #999; }
    </style>
""", unsafe_allow_html=True)

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
                st.error("❌ Wrong username or password.")
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
if "confirm_clear_groceries" not in st.session_state:
    st.session_state.confirm_clear_groceries = False
if "confirm_delete_recipe" not in st.session_state:
    st.session_state.confirm_delete_recipe = None
if "confirm_delete_grocery" not in st.session_state:
    st.session_state.confirm_delete_grocery = None
if "confirm_delete_gwish" not in st.session_state:
    st.session_state.confirm_delete_gwish = None
if "confirm_delete_pwish" not in st.session_state:
    st.session_state.confirm_delete_pwish = None
if "confirm_delete_todo" not in st.session_state:
    st.session_state.confirm_delete_todo = None
if "toast" not in st.session_state:
    st.session_state.toast = None

if st.session_state.toast:
    st.toast(st.session_state.toast)
    st.session_state.toast = None

# --- TOP BAR ---
now = datetime.now(MYT)
col_left, col_mid, col_right = st.columns([3, 2, 2])
with col_left:
    st.markdown("### 🍳 Kitchen Co-op")
    st.caption(f"👤 **{display_name}** · paired with **{partner_display}**")
with col_mid:
    st.markdown(f"🗓️ {now.strftime('%A, %d %b %Y')}")
    st.markdown(f"⏰ {now.strftime('%I:%M %p')} MYT")
with col_right:
    btn1, btn2 = st.columns(2)
    with btn1:
        if st.button("🔄 Refresh", use_container_width=True):
            st.session_state.db_schedules = fetch_schedules()
            st.session_state.toast = "🔄 Data refreshed!"
            st.rerun()
    with btn2:
        if st.button("🚪 Log Out", use_container_width=True):
            for key in list(st.session_state.keys()):
                st.session_state.pop(key, None)
            st.rerun()

st.divider()

# --- TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["📅 Schedule", "💡 Recipes", "🛒 Groceries", "🔒 Personal"])

# ══════════════════════════════════════════
# TAB 1: SCHEDULE
# ══════════════════════════════════════════
with tab1:
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
    my_sched = st.session_state.db_schedules.get(username, {})
    my_updates = {}

    st.markdown("### 👤 Your Availability This Week")
    st.caption("Tick the meals you're free for each day, then hit Save.")

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
        st.session_state.toast = "✅ Schedule saved!"
        st.rerun()

    st.write("---")
    st.markdown(f"### 🤝 Overlap with {partner_display}")
    my_fresh = st.session_state.db_schedules.get(username, {})
    partner_fresh = st.session_state.db_schedules.get(partner_username, {})
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
    st.caption(f"💡 Hit **Refresh** at the top to see {partner_display}'s latest schedule.")

# ══════════════════════════════════════════
# TAB 2: RECIPES
# ══════════════════════════════════════════
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
        if st.form_submit_button("➕ Add to Pool", type="primary"):
            if new_recipe.strip():
                add_db_recipe(new_recipe.strip(), new_link.strip(), new_when)
                st.session_state.toast = "🍽️ Recipe added!"
                st.rerun()
            else:
                st.warning("Please enter a dish name.")

    st.write("")
    current_recipes = fetch_recipes()
    if current_recipes:
        st.markdown("### 🍽️ Brainstorm List")
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
                if st.session_state.confirm_delete_recipe == item['id']:
                    st.warning("Sure?")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✅", key=f"yes_r_{item['id']}"):
                            delete_db_recipe(item['id'])
                            st.session_state.confirm_delete_recipe = None
                            st.session_state.toast = "🗑️ Recipe deleted."
                            st.rerun()
                    with c2:
                        if st.button("❌", key=f"no_r_{item['id']}"):
                            st.session_state.confirm_delete_recipe = None
                            st.rerun()
                else:
                    if st.button("🗑️", key=f"del_r_{item['id']}"):
                        st.session_state.confirm_delete_recipe = item['id']
                        st.rerun()
    else:
        st.caption("The pool is empty. Drop some recipe ideas above!")

# ══════════════════════════════════════════
# TAB 3: GROCERIES
# ══════════════════════════════════════════
with tab3:
    st.header("🛒 Shared Groceries")

    gtab1, gtab2 = st.tabs(["🧾 Current Bill", "📋 Future Ingredients Wishlist"])

    # ── GROCERY BILL TAB ──
    with gtab1:
        with st.form("grocery_form", clear_on_submit=True):
            col_i, col_p, col_who = st.columns([2, 1, 1])
            with col_i:
                g_item = st.text_input("Item *", placeholder="e.g. Eggs")
            with col_p:
                g_price = st.number_input("Price (RM)", min_value=0.0, step=0.10, format="%.2f")
            with col_who:
                g_paid_by = st.selectbox("Paid by", options=[display_name, partner_display])
            if st.form_submit_button("➕ Add Item", type="primary"):
                if g_item.strip():
                    add_grocery(g_item.strip(), g_price, g_paid_by)
                    st.session_state.toast = f"🛒 '{g_item.strip()}' added!"
                    st.rerun()
                else:
                    st.warning("Please enter an item name.")

        st.write("")
        groceries = fetch_groceries()

        if groceries:
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
            balance = paid_by_me - each_owes
            if abs(balance) < 0.01:
                st.success("✅ All settled up!")
            elif balance > 0:
                st.info(f"💸 **{partner_display}** owes **{display_name}** RM {balance:.2f}")
            else:
                st.info(f"💸 **{display_name}** owes **{partner_display}** RM {abs(balance):.2f}")

            st.write("---")

            if st.session_state.confirm_clear_groceries:
                st.warning("⚠️ This will delete ALL grocery items and reset the bill. Are you sure?")
                cc1, cc2, cc3 = st.columns([1, 1, 4])
                with cc1:
                    if st.button("✅ Yes, clear all", type="primary"):
                        clear_all_groceries()
                        st.session_state.confirm_clear_groceries = False
                        st.session_state.toast = "🧹 Grocery list cleared!"
                        st.rerun()
                with cc2:
                    if st.button("❌ Cancel"):
                        st.session_state.confirm_clear_groceries = False
                        st.rerun()
            else:
                if st.button("🧹 Clear All & Restart"):
                    st.session_state.confirm_clear_groceries = True
                    st.rerun()

            st.markdown("### 🧾 Grocery List")
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
                            st.session_state.toast = "💰 Marked as paid back!"
                            st.rerun()
                with c5:
                    if st.session_state.confirm_delete_grocery == g['id']:
                        if st.button("✅", key=f"yes_g_{g['id']}"):
                            delete_grocery(g['id'])
                            st.session_state.confirm_delete_grocery = None
                            st.session_state.toast = "🗑️ Item deleted."
                            st.rerun()
                        if st.button("❌", key=f"no_g_{g['id']}"):
                            st.session_state.confirm_delete_grocery = None
                            st.rerun()
                    else:
                        if st.button("🗑️", key=f"del_g_{g['id']}"):
                            st.session_state.confirm_delete_grocery = g['id']
                            st.rerun()
        else:
            st.caption("No groceries added yet. Add your first item above!")

    # ── GROCERY WISHLIST TAB ──
    with gtab2:
        st.markdown("### 📋 Future Ingredients to Buy Someday")
        st.caption("Shared list — both of you can add and view. Move an item to the bill once you've bought it.")

        with st.form("gwish_form", clear_on_submit=True):
            col_wi, col_wb = st.columns([3, 1])
            with col_wi:
                gw_item = st.text_input("Ingredient or item", placeholder="e.g. Miso paste, Tahini")
            if st.form_submit_button("➕ Add to Wishlist", type="primary"):
                if gw_item.strip():
                    add_grocery_wishlist(gw_item.strip(), display_name)
                    st.session_state.toast = "📋 Added to wishlist!"
                    st.rerun()
                else:
                    st.warning("Please enter an item.")

        st.write("")
        wishlist_items = fetch_grocery_wishlist()
        if wishlist_items:
            h1, h2, h3, h4 = st.columns([2.5, 1.2, 1.5, 0.5])
            h1.markdown("**Item**")
            h2.markdown("**Added by**")
            h3.markdown("**Move to Bill**")
            h4.markdown("**Del**")

            for w in wishlist_items:
                c1, c2, c3, c4 = st.columns([2.5, 1.2, 1.5, 0.5])
                with c1:
                    st.write(w["item"])
                with c2:
                    st.write(w.get("added_by", "-"))
                with c3:
                    if st.button("➡️ Move to Bill", key=f"move_{w['id']}"):
                        move_to_groceries(w["id"], w["item"], display_name)
                        st.session_state.toast = f"✅ '{w['item']}' moved to grocery bill!"
                        st.rerun()
                with c4:
                    if st.session_state.confirm_delete_gwish == w['id']:
                        if st.button("✅", key=f"yes_gw_{w['id']}"):
                            delete_grocery_wishlist(w['id'])
                            st.session_state.confirm_delete_gwish = None
                            st.session_state.toast = "🗑️ Removed from wishlist."
                            st.rerun()
                        if st.button("❌", key=f"no_gw_{w['id']}"):
                            st.session_state.confirm_delete_gwish = None
                            st.rerun()
                    else:
                        if st.button("🗑️", key=f"del_gw_{w['id']}"):
                            st.session_state.confirm_delete_gwish = w['id']
                            st.rerun()
        else:
            st.caption("Nothing on the wishlist yet. Add future ingredients above!")

# ══════════════════════════════════════════
# TAB 4: PERSONAL
# ══════════════════════════════════════════
with tab4:
    st.header(f"🔒 {display_name}'s Personal Space")
    st.caption("Only you can see this. Your roommate has their own private version.")

    ptab1, ptab2 = st.tabs(["🛍️ To-Buy Wishlist", "✅ To-Do List"])

    # ── PERSONAL WISHLIST ──
    with ptab1:
        st.markdown("### 🛍️ Things I Want to Buy")

        with st.form("pwish_form", clear_on_submit=True):
            pw_item = st.text_input("Item", placeholder="e.g. New earphones, Skincare serum")
            if st.form_submit_button("➕ Add", type="primary"):
                if pw_item.strip():
                    add_personal_wishlist(username, pw_item.strip())
                    st.session_state.toast = "🛍️ Added to your wishlist!"
                    st.rerun()
                else:
                    st.warning("Please enter an item.")

        st.write("")
        pw_items = fetch_personal_wishlist(username)
        if pw_items:
            done_count = sum(1 for i in pw_items if i.get("done"))
            st.caption(f"{done_count}/{len(pw_items)} bought")
            st.progress(done_count / len(pw_items))
            st.write("")

            for pw in pw_items:
                c1, c2, c3 = st.columns([0.08, 0.84, 0.08])
                with c1:
                    checked = st.checkbox("", value=pw.get("done", False), key=f"pw_chk_{pw['id']}")
                    if checked != pw.get("done", False):
                        toggle_personal_wishlist(pw["id"], pw.get("done", False))
                        st.session_state.toast = "✅ Marked as bought!" if checked else "↩️ Unmarked."
                        st.rerun()
                with c2:
                    if pw.get("done"):
                        st.markdown(f"<span class='done-item'>{pw['item']}</span>", unsafe_allow_html=True)
                    else:
                        st.write(pw["item"])
                with c3:
                    if st.session_state.confirm_delete_pwish == pw['id']:
                        if st.button("✅", key=f"yes_pw_{pw['id']}"):
                            delete_personal_wishlist(pw['id'])
                            st.session_state.confirm_delete_pwish = None
                            st.session_state.toast = "🗑️ Removed."
                            st.rerun()
                        if st.button("❌", key=f"no_pw_{pw['id']}"):
                            st.session_state.confirm_delete_pwish = None
                            st.rerun()
                    else:
                        if st.button("🗑️", key=f"del_pw_{pw['id']}"):
                            st.session_state.confirm_delete_pwish = pw['id']
                            st.rerun()
        else:
            st.caption("Nothing on your wishlist yet!")

    # ── PERSONAL TODO ──
    with ptab2:
        st.markdown("### ✅ My To-Do List")

        with st.form("todo_form", clear_on_submit=True):
            todo_task = st.text_input("Task", placeholder="e.g. Clean the fridge, Pay rent")
            if st.form_submit_button("➕ Add Task", type="primary"):
                if todo_task.strip():
                    add_personal_todo(username, todo_task.strip())
                    st.session_state.toast = "📝 Task added!"
                    st.rerun()
                else:
                    st.warning("Please enter a task.")

        st.write("")
        todo_items = fetch_personal_todo(username)
        if todo_items:
            done_count = sum(1 for t in todo_items if t.get("done"))
            st.caption(f"{done_count}/{len(todo_items)} done")
            st.progress(done_count / len(todo_items))
            st.write("")

            for td in todo_items:
                c1, c2, c3 = st.columns([0.08, 0.84, 0.08])
                with c1:
                    checked = st.checkbox("", value=td.get("done", False), key=f"td_chk_{td['id']}")
                    if checked != td.get("done", False):
                        toggle_personal_todo(td["id"], td.get("done", False))
                        st.session_state.toast = "✅ Task done!" if checked else "↩️ Unmarked."
                        st.rerun()
                with c2:
                    if td.get("done"):
                        st.markdown(f"<span class='done-item'>{td['task']}</span>", unsafe_allow_html=True)
                    else:
                        st.write(td["task"])
                with c3:
                    if st.session_state.confirm_delete_todo == td['id']:
                        if st.button("✅", key=f"yes_td_{td['id']}"):
                            delete_personal_todo(td['id'])
                            st.session_state.confirm_delete_todo = None
                            st.session_state.toast = "🗑️ Task removed."
                            st.rerun()
                        if st.button("❌", key=f"no_td_{td['id']}"):
                            st.session_state.confirm_delete_todo = None
                            st.rerun()
                    else:
                        if st.button("🗑️", key=f"del_td_{td['id']}"):
                            st.session_state.confirm_delete_todo = td['id']
                            st.rerun()
        else:
            st.caption("No tasks yet. Add something to get started!")
