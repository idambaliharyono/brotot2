import streamlit as st
import memberlist_page
import registration_page
from auth import authenticate

PAGES = {
    "Registration": registration_page,
    "Member List": memberlist_page
}

def main():
    if 'refresh_counter' not in st.session_state:
        st.session_state['refresh_counter'] = 0

    st.title("BROTOT")
    st.write("by bli kadek")
    if authenticate():  # Checks if the user is authenticated
        st.sidebar.title("Navigation")
        selection = st.sidebar.radio("Go to", list(PAGES.keys()))
        page = PAGES[selection]
        page.app()
    else:
        st.warning("Please log in to continue. The login form is above.")

if __name__ == "__main__":
    main()
