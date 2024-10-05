import streamlit as st

def check_credentials(username, password):
    correct_username = st.secrets["auth"]["username"]
    correct_password = st.secrets["auth"]["password"]
    return username == correct_username and password == correct_password

def authenticate():
    """Display login form and authenticate user if not already authenticated."""
    if 'authenticated' not in st.session_state or not st.session_state['authenticated']:
        st.write("### Please log in to continue")
        with st.form("login_form"):
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", key="login_password", type="password")
            submit = st.form_submit_button("Login")
        if submit:
            if check_credentials(username, password):
                st.session_state['authenticated'] = True
                # Increment refresh_counter to refresh connection after login
                st.session_state['refresh_counter'] = st.session_state.get('refresh_counter', 0) + 1
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Incorrect username or password")
    else:
        return True
