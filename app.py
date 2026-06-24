import streamlit as st
from supabase import create_client, Client
import json

@st.cache_resource
def init_supabase() -> Client:
    url = "https://qwpladpytaygcrvuxfqq.supabase.co"
    # Fixed the 't' back to a 'd' in the middle of the key string here:
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF3cGxhZHB5dGF5Z2NydnV4ZnFnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODIyNzM2OTgsImV4cCI6MjA5Nzg0OTY5OH0.ChL-UX2sT351Yd9i5RxFOLwNNpPG-FK8EYrHkJXrCrY"
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
    response = supabase.table("recipes").select("*").order("created_at", descending=False).execute()
    return response.data

def add_db_recipe(text):
    supabase.table("recipes").insert({"idea": text}).execute()

def delete_db_recipe(recipe_id):
    supabase.table("recipes").delete().eq("id", recipe_id).execute()

# --- INTERFACE SETUP ---
st.set_page_config(page_title="Kitchen Co-op", page_icon="🍳", layout="wide")
st.title("🍳 Kitchen Co-op")
st.subheader("Coordinate meals around crazy class schedules")

db_schedules = fetch_schedules()
roommates = list(db_schedules.keys()) if len(db_schedules) >= 2 else ["Roommate A", "Roommate B"]

# --- SIDEBAR: NAMES ---
with st.sidebar:
    st.header("👥 Profiles")
    r1 = st.text_input("Your Name", roommates[0])
    r2 = st.text_input("Roommate's Name", roommates[1])

st.write("---")

# --- CALENDAR TRACKER ---
st.header("📅 Weekly Cooking Availability")
st.caption("Check off the slots when you are free to cook/eat together.")

r1_sched = db_schedules.get(r1, {day: {"Lunch": False, "Dinner": False} for day in DAYS_OF_WEEK})
r2_sched = db_schedules.get(r2, {day: {"Lunch": False, "Dinner": False} for day in DAYS_OF_WEEK})

# Match Calculations
lunch_matches = [day for day in DAYS_OF_WEEK if r1_sched.get(day, {}).get("Lunch") and r2_sched.get(day, {}).get("Lunch")]
dinner_matches = [day for day in DAYS_OF_WEEK if r1_sched.get(day, {}).get("Dinner") and r2_sched.get(day, {}).get("Dinner")]

col_m1, col_m2 = st.columns(2)
with col_m1:
    if lunch_matches:
        st.success(f"🌞 **Shared Lunch Days:** {', '.join(lunch_matches)}")
    else:
        st.warning("⏳ No shared lunch slots found.")
with col_m2:
    if dinner_matches:
        st.success(f"🌙 **Shared Dinner Days:** {', '.join(dinner_matches)}")
    else:
        st.warning("⏳ No shared dinner slots found.")

st.write("")

# Calendar Input Grid
col_r1, col_r2 = st.columns(2)
r1_updates, r2_updates = {}, {}

with col_r1:
    st.markdown(f"### 👤 {r1}'s Schedule")
    for day in DAYS_OF_WEEK:
        st.markdown(f"**{day}**")
        c1, c2 = st.columns(2)
        with c1:
            l_val = st.checkbox("Free Lunch", value=r1_sched.get(day, {}).get("Lunch", False), key=f"r1_l_{day}")
        with c2:
            d_val = st.checkbox("Free Dinner", value=r1_sched.get(day, {}).get("Dinner", False), key=f"r1_d_{day}")
        r1_updates[day] = {"Lunch": l_val, "Dinner": d_val}

with col_r2:
    st.markdown(f"### 👥 {r2}'s Schedule")
    for day in DAYS_OF_WEEK:
        st.markdown(f"**{day}**")
        c1, c2 = st.columns(2)
        with c1:
            l_val = st.checkbox("Free Lunch", value=r2_sched.get(day, {}).get("Lunch", False), key=f"r2_l_{day}")
        with c2:
            d_val = st.checkbox("Free Dinner", value=r2_sched.get(day, {}).get("Dinner", False), key=f"r2_d_{day}")
        r2_updates[day] = {"Lunch": l_val, "Dinner": d_val}

# Immediate auto-saving to DB if checkboxes change
if r1_updates != r1_sched:
    update_db_schedule(r1, r1_updates)
    st.rerun()
if r2_updates != r2_sched:
    update_db_schedule(r2, r2_updates)
    st.rerun()

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
