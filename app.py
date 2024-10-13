import streamlit as st
import memberlist_page
import registration_page
import edit_members
from auth import authenticate


PAGES = {
    "Registration": registration_page,
    "Member List": memberlist_page,
    "Edit Member's Data": edit_members
}

def main():
    if 'refresh_counter' not in st.session_state:
        st.session_state['refresh_counter'] = 0
    

    col1, col2 = st.columns([0.3, 0.7])
    
    with col1:
       
    # Import Google Font
        st.markdown("""
        <head>
        <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@700&display=swap" rel="stylesheet">
        </head>
        <style>
        .custom-font {
            font-family: 'Roboto', sans-serif; /* This font is now from Google Fonts */
            font-size: 36px; /* Slightly larger font size */
            color: #2A9D8F; /* A teal color */
        }
        </style>
        """, unsafe_allow_html=True)

        # Use the custom style class in your Markdown
        st.markdown('<p class="custom-font">BROTOT 💪</p>', unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div style='height: 100%; display: flex; flex-direction: column; justify-content: flex-end;'>
            <p style='text-align: left; color: gray; margin: 0; padding-top: 40px;'>
                by bli kadek
            </p>
        </div>
        """, unsafe_allow_html=True)    

    if authenticate():  # Checks if the user is authenticated
        st.sidebar.title("Navigation")
        with st.sidebar.expander("Pages"):
            selection = st.sidebar.radio("Go to", list(PAGES.keys()))
        page = PAGES[selection]
        page.app()
    else:
        st.warning("Please log in to continue")

if __name__ == "__main__":
    main()
