# streamlit_app.py
import io
import streamlit as st
import requests
from PIL import Image
import json

API_URL = "http://127.0.0.1:8081"

if 'token' not in st.session_state: 
    st.session_state.token=None
if 'chat_history' not in st.session_state: 
    st.session_state.chat_history=[]

# ---------------- LOGIN ----------------
if not st.session_state.token:
    st.title("Login / Register")
    name = st.text_input("Name (for register)")
    email = st.text_input("Email")
    
    pwd = st.text_input("Password", type="password")
    confirm_pwd = st.text_input("Confirm Password", type="password")
    col1,col2 = st.columns(2)
    with col1:
        if st.button("Login"):
            r = requests.post(f"{API_URL}/login", params={
                "email":email,"password":pwd,
                })
            if r.status_code==200: 
                st.session_state.token=r.json()["token"]
            else: 
                st.error(r.json()["detail"])
    with col2:
        if st.button("Register"):
            r = requests.post(f"{API_URL}/register", params={
                "email": email,
                "password": pwd,
                "confirm_password": confirm_pwd,
                "name": name
                })
            if r.status_code == 200:
             st.success("Registered! Please login now.")
            else:
             st.error(r.json()["detail"])
else:
    st.sidebar.title("AI Personal Assistant")
    choice = st.sidebar.radio("Navigate", ["Chat with AI", "Profile"])

    
    if choice == "Chat with AI":
        st.title("💬 Chat with Assistant")

        # Display chat history
        for chat in st.session_state.chat_history:
            with st.chat_message(chat["role"]):
                if chat.get("type") == "image":
                    st.image(chat["content"], caption=chat.get("title",""))
                else:
                    st.markdown(chat["content"])

        # User message input
        msg = st.chat_input("Type your message...")
        if msg:
            st.session_state.chat_history.append({"role": "user", "content": msg})
            r = requests.post(f"{API_URL}/process", params={"token": st.session_state.token, "message": msg})
            if r.status_code == 200:
                reply = r.json().get("reply", "")
                st.session_state.chat_history.append({"role": "assistant", "content": reply})
            else:
                st.error(r.json().get("detail", "Error"))


        
    # ----------------- PROFILE -----------------
    elif choice == "Profile":
        st.title("👤 My Profile")
        # Fetch user info from backend (simplified as stored info)
        r = requests.post(f"{API_URL}/process", params={"token": st.session_state.token, "message": "list user info"})
        if r.status_code == 200:
            info_list = r.json().get("reply", [])
            # Only display Name, Email, Gender
            user_info = {"Name": "", "Email": "", "Gender": ""}
            for item in info_list:
                content = item.get("content", "")
                if "name" in content.lower(): user_info["Name"] = content
                if "email" in content.lower(): user_info["Email"] = content
                if "gender" in content.lower(): user_info["Gender"] = content
            st.markdown(f"**Name:** {user_info['Name']}")
            st.markdown(f"**Email:** {user_info['Email']}")
            st.markdown(f"**Gender:** {user_info['Gender']}")
        else:
            st.error("Could not fetch profile information.")