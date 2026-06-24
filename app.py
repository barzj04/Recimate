import streamlit as st
from supabase import create_client, Client

# --- AUTH CONFIG (hardcoded users) ---
USERS = {
    "arleen": {"password": "pass1", "display": "Arleen"},
    "roommate": {"password": "pass2", "display": "Rachel"},
}
ROOMMATE_PAIRS = {
    "arleen": "roommate",
    "roommate": "arleen",
}

# --- SUPABASE ---
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"].strip()
    key = st.secrets["SUPABASE_KEY"].strip()
    return create_client(url, key)

supabase = init_supabase()
DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# --- DATA ACTIONS ---
def fetch_schedules():
    response = supabase.table("schedules").select("*").execute()
    return {row["roommate"]: row["schedule"] for row in response.data}

def update_db_schedule(name, schedule_dict):
    supabase.table("schedules").upsert({"roommate": name, "schedule": schedule_dict}).execute()

def fetch_recipes():
    response = supabase.table("recipes").select("*").order("created_at", desc=False).execute()
    return response.data

def add_db_recipe(text):
    supabase.table("recipes").insert({"idea": text}).execute()

def delete_db_recipe(recipe_id):
    supabase.table("recipes").delete().eq("id", recipe_id).execute()

# --- PAGE CONFIG ---
st.set_page_config(page_title="Kitchen Co-op", page_icon="🍳", layout="wide")

# --- LOGIN SCREEN ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None

if not st.session_state.logged_in:
    st.title("🍳 Kitchen Co-op")
    st.subheader("Please log in to continue")
    st.write("")

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        username = st.text_input("Username").strip().lower()
        password = st.text_input("Password", type="password")
        if st.button("Log In", type="primary", use_container_width=True):
            if username in USERS and USERS[username]["password"] == password:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Wrong username or password.")
    st.stop()

# --- LOGGED IN ---
username = st.session_state.username
display_name = USERS[username]["display"]
partner_username = ROOMMATE_PAIRS[username]
partner_display = USERS[partner_username]["display"]

# Sidebar
with st.sidebar:
    st.markdown(f"### 👤 {display_name}")
    st.caption(f"Paired with: {partner_display}")
    st.divider()
    if st.button("🔄 Refresh Data"):
        st.session_state.db_schedules = fetch_schedules()
        st.rerun()
    st.divider()
    if st.button("🚪 Log Out"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.db_schedules = {}
        st.rerun()

# --- MAIN APP ---
st.title("🍳 Kitchen Co-op")
st.subheader(f"Hey {display_name}! Let's coordinate meals 🥘")

# Load schedules (cached in session)
if "db_schedules" not in st.session_state:
    st.session_state.db_schedules = fetch_schedules()

db_schedules = st.session_state.db_schedules

my_sched = db_schedules.get(username, {day: {"Lunch": False, "Dinner": False} for day in DAYS_OF_WEEK})
partner_sched = db_schedules.get(partner_username, {day: {"Lunch": False, "Dinner": False} for day in DAYS_OF_WEEK})

st.write("---")

# --- MY SCHEDULE ---
st.header("📅 Your Weekly Availability")
st.caption("Tick the slots when you're free to cook or eat together, then save.")

my_updates = {}
for day in DAYS_OF_WEEK:
    st.markdown(f"**{day}**")
    c1, c2 = st.columns(2)
    with c1:
        l_val = st.checkbox("🌞 Free for Lunch", value=my_sched.get(day, {}).get("Lunch", False), key=f"my_l_{day}")
    with c2:
        d_val = st.checkbox("🌙 Free for Dinner", value=my_sched.get(day, {}).get("Dinner", False), key=f"my_d_{day}")
    my_updates[day] = {"Lunch": l_val, "Dinner": d_val}

st.write("")
if st.button("💾 Save My Schedule", type="primary", use_container_width=True):
    update_db_schedule(username, my_updates)
    st.session_state.db_schedules = fetch_schedules()
    st.success("✅ Schedule saved!")
    st.rerun()

st.write("---")

# --- SHARED MATCHES ---
st.header(f"🤝 You & {partner_display}'s Overlap")

# Re-read from updated session after save
db_schedules = st.session_state.db_schedules
my_sched_fresh = db_schedules.get(username, {})
partner_sched_fresh = db_schedules.get(partner_username, {})

lunch_matches = [day for day in DAYS_OF_WEEK if my_sched_fresh.get(day, {}).get("Lunch") and partner_sched_fresh.get(day, {}).get("Lunch")]
dinner_matches = [day for day in DAYS_OF_WEEK if my_sched_fresh.get(day, {}).get("Dinner") and partner_sched_fresh.get(day, {}).get("Dinner")]

col_m1, col_m2 = st.columns(2)
with col_m1:
    if lunch_matches:
        st.success(f"🌞 **Shared Lunch Days:** {', '.join(lunch_matches)}")
    else:
        st.warning("⏳ No shared lunch slots yet.")
with col_m2:
    if dinner_matches:
        st.success(f"🌙 **Shared Dinner Days:** {', '.join(dinner_matches)}")
    else:
        st.warning("⏳ No shared dinner slots yet.")

st.caption(f"💡 Hit **Refresh Data** in the sidebar to see {partner_display}'s latest schedule.")

st.write("---")

# --- RECIPE IDEAS POOL ---
st.header("💡 Shared Recipe Ideas")

with st.form("recipe_form", clear_on_submit=True):
    new_recipe = st.text_input("Got an idea? Enter a dish name or recipe link:")
    submitted = st.form_submit_button("Add to Shared Pool")
    if submitted and new_recipe.strip():
        add_db_recipe(new_recipe.strip())
        st.rerun()

current_recipes = fetch_recipes()
if current_recipes:
    st.markdown("### 🛒 Current Brainstorm List:")
    for item in current_recipes:
        col_text, col_btn = st.columns([0.9, 0.1])
        with col_text:
            st.write(f"- {item['idea']}")
        with col_btn:
            if st.button("🗑️", key=f"del_{item['id']}"):
                delete_db_recipe(item['id'])
                st.rerun()
else:
    st.caption("The pool is empty. Drop some recipe ideas or links above!")
