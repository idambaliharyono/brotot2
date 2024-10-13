import streamlit as st
from google.oauth2 import service_account
import gspread
import pandas as pd
from datetime import datetime
import cloudinary
import cloudinary.uploader
import tempfile
import os
from PIL import Image

def app():
    # Initialize Cloudinary
    cloudinary.config(
        cloud_name=st.secrets['cloudinary']['cloud_name'],
        api_key=st.secrets['cloudinary']['api_key'],
        api_secret=st.secrets['cloudinary']['api_secret']
    )

    # Function to initialize Google Sheets connection
    def init_connection():
        scope = [
            "https://spreadsheets.google.com/feeds",
            'https://www.googleapis.com/auth/spreadsheets',
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = service_account.Credentials.from_service_account_info(
                    st.secrets["gcp_service_account"],
                    scopes=scope
                )
        client = gspread.authorize(creds)

        # Access the Members Sheet
        spreadsheet_id = st.secrets["google_sheets"]["spreadsheet_id"]
        members_sheet = client.open_by_key(spreadsheet_id).worksheet('Members')

        return client, members_sheet

    # Function to fetch member data
    @st.cache_data
    def get_member_data(_client):
        spreadsheet_id = st.secrets["google_sheets"]["spreadsheet_id"]
        members_sheet = client.open_by_key(spreadsheet_id).worksheet('Members')
        members_data = members_sheet.get_all_records()
        members_df = pd.DataFrame(members_data)
        return members_df

    # Function to format phone numbers
    def format_phone_number(phone_number):
        phone_number = phone_number.strip()  # Remove any leading/trailing spaces
        if phone_number.startswith('0'):
            formatted_number = '62' + phone_number[1:]
        elif phone_number.startswith('+62'):
            formatted_number = phone_number.replace('+', '')
        else:
            formatted_number = phone_number  # Assume it's already in correct format
        # Remove any non-digit characters
        formatted_number = ''.join(filter(str.isdigit, formatted_number))
        return formatted_number

    # Function to upload image to Cloudinary
    def upload_image_to_cloudinary(file):
        temp_file_path = None

        try:
            # Open the uploaded image file using Pillow
            image = Image.open(file)

            # Save the image to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
                image.save(temp_file, format='JPEG')
                temp_file_path = temp_file.name  # Get the path of the temporary file

            # Upload the file to Cloudinary
            upload_result = cloudinary.uploader.upload(temp_file_path, folder="gym_members")
            if 'url' in upload_result:
                return upload_result['url'], temp_file_path, 0  # Success
            else:
                return None, None, 1  # Error: No URL found in response

        except Exception as e:
            st.error(f"Error during image upload: {e}")
            return None, None, 2  # Error during image upload

        finally:
            # Clean up the temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except Exception as cleanup_error:
                    st.error(f"Error cleaning up temporary file: {cleanup_error}")

    # Function to update member information
    def update_member_info(client, member_id, updated_data):
        spreadsheet_id = st.secrets["google_sheets"]["spreadsheet_id"]
        members_sheet = client.open_by_key(spreadsheet_id).worksheet('Members')

        # Find the row number where the member_id is located
        cell = members_sheet.find(str(member_id))
        if cell:
            row_number = cell.row
            headers = members_sheet.row_values(1)

            # Update each field specified in updated_data
            for key, value in updated_data.items():
                if key in headers:
                    col_index = headers.index(key) + 1  # Google Sheets columns start at 1
                    members_sheet.update_cell(row_number, col_index, value)
                else:
                    st.warning(f"Field '{key}' not found in the sheet headers.")
        else:
            st.error(f"Member ID {member_id} not found in the sheet.")

    # Function to add background image
    def add_bg_from_url():
        st.markdown(
            """
            <style>
            body {
                background: linear-gradient(rgba(0, 0, 0, 0.5), rgba(0, 0, 0, 0.5)),
                            url("https://images.unsplash.com/photo-1649068618811-9f3547ef98fc?w=800&auto=format&fit=crop&q=60&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8Mjd8fGd5bSUyMGVxdWlwbWVudHxlbnwwfHwwfHx8MA%3D%3D");
                background-size: cover;
                background-position: center;
                background-attachment: fixed;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

    # Main code for the edit member page
    add_bg_from_url()
    st.title('Edit Member Information')

    # Initialize Google Sheets connection
    client, members_sheet = init_connection()
    members_df = get_member_data(client)

    # Create a selection box for members
    members_df['display_name'] = members_df['nick_name'] + ' (' + members_df['full_name'] + ')'
    member_selection = st.selectbox('Select a member to edit:', members_df['display_name'])

    # Get the selected member's data
    selected_member = members_df[members_df['display_name'] == member_selection].iloc[0]
    member_id = selected_member['member_id']

    # Pre-fill the form with the selected member's data
    with st.form(f"edit_form_{member_id}"):
        nick_name = st.text_input("Nickname", value=selected_member['nick_name'])
        full_name = st.text_input("Full Name", value=selected_member['full_name'])
        gender_options = ["Male", "Female", "Other"]
        gender = st.selectbox(
            "Gender",
            gender_options,
            index=gender_options.index(selected_member.get('gender', 'Male'))
        )

        # Handle birth date
        birth_date_str = selected_member.get('birth_date', datetime.today().strftime('%Y-%m-%d'))
        try:
            birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d")
        except ValueError:
            birth_date = datetime.today()
        birth_date = st.date_input("Date of Birth", value=birth_date)

        phone_number = st.text_input("Phone Number", value=selected_member.get('phone_number', ''))
        medical_info = st.text_area("Medical Information", value=selected_member.get('medical_info', ''))
        fitness_goal = st.text_input("Fitness Goal", value=selected_member.get('fitness_goal', ''))

        workout_times = ["8am-10am", "11am-12pm", "1pm-3pm", "4pm-6pm", "6pm-7pm", "7pm-8pm", "8pm-9pm", "9pm-10pm"]
        preferred_workout_time = st.selectbox(
            "Preferred Workout Time",
            workout_times,
            index=workout_times.index(selected_member.get('preferred_workout_time', workout_times[0]))
        )

        # Display current photo
        st.write("Current Photo:")
        st.image(selected_member.get('photo_url', ''), width=200)

        # File uploader for new photo
        new_photo = st.file_uploader("Upload New Photo", type=["jpg", "jpeg", "png"])

        submit = st.form_submit_button("Update")

        if submit:
            # Collect updated data
            updated_data = {
                'nick_name': nick_name,
                'full_name': full_name,
                'gender': gender,
                'birth_date': birth_date.strftime('%Y-%m-%d'),
                'phone_number': format_phone_number(phone_number),
                'medical_info': medical_info,
                'fitness_goal': fitness_goal,
                'preferred_workout_time': preferred_workout_time
            }

            # Handle photo upload
            if new_photo is not None:
                with st.spinner("Uploading new photo..."):
                    photo_url, temp_file_path, upload_status = upload_image_to_cloudinary(new_photo)
                    if upload_status == 0:
                        updated_data['photo_url'] = photo_url
                    else:
                        st.error("Failed to upload new photo.")
                        st.stop()  # Stop execution if photo upload fails
            else:
                updated_data['photo_url'] = selected_member.get('photo_url', '')  # Keep existing photo

            # Update member information in Google Sheets
            with st.spinner("Updating member information..."):
                update_member_info(client, member_id, updated_data)
                st.success("Member information updated!")

                # Clear cached data to refresh member data
                get_member_data.clear()

                # Optionally, rerun the app to reflect changes
                st.rerun()
