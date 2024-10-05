from google.oauth2 import service_account
import streamlit as st
import gspread
from cloudinary.uploader import upload as cloudinary_upload
from datetime import datetime
import os
import tempfile
from PIL import Image  # Pillow library for image processing
from datetime import date
import cloudinary


def app():

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


    # Cloudinary configuration
    cloudinary.config(
        cloud_name=st.secrets['cloudinary']['cloud_name'],  # Your Cloudinary cloud name
        api_key=st.secrets['cloudinary']['api_key'],        # Your Cloudinary API key
        api_secret=st.secrets['cloudinary']['api_secret']   # Your Cloudinary API secret
    )

    # Initialize Google Sheets connection
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
        
        # Access the Members and Transactions Sheets
        spreadsheet_id = st.secrets["google_sheets"]["spreadsheet_id"]
        members_sheet = client.open_by_key(spreadsheet_id).worksheet('Members')
        transactions_sheet = client.open_by_key(spreadsheet_id).worksheet('Transactions')

        return client, members_sheet, transactions_sheet

    client, members_sheet, transactions_sheet = init_connection()

    # Define membership types and their durations
    membership_types = {
        "BULANAN": {"id": 1, "duration": 30}
    }
    payment_types = {
        "Cash": {"id": 1, "payment_method": 'cash'},  
        "Trf/Qris": {"id": 2, "payment_method": 'e-money'}, 
    }

    # Resize and upload image to Cloudinary
    def upload_image_to_cloudinary(file):
        temp_file_path = None
        
        try:
            # Open the uploaded image file using Pillow (not resizing here)
            image = Image.open(file)

            # Save the original image to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
                image.save(temp_file, format='JPEG')
                temp_file_path = temp_file.name  # Get the path of the temporary file

            # Upload the original file to Cloudinary
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

    # Function to register a new member
    # Function to register a new member
    # ... [Your existing imports and functions]

    # Function to register a new member
    def register_member():
        with st.form("register_form"):
            nick_name = st.text_input("Nickname", key="nick")
            full_name = st.text_input("Full Name", key="full")
            gender = st.selectbox("Gender", ["Male", "Female", "Other"], key="gender")
            birth_date = st.date_input("Date of Birth", value=datetime.today(), min_value=date(1950, 1, 1), max_value=datetime.today(), key="birth")

            phone_number = st.text_input("Phone Number", key="phone")
            medical_info = st.text_area("Medical Information", key="medical")
            fitness_goal = st.text_input("Fitness Goal", key="goal")
            
            workout_times = ["8am-10am", "11am-12pm", "1pm-3pm", "4pm-6pm", "6pm-7pm", "7pm-8pm", "8pm-9pm", "9pm-10pm"]
            preferred_workout_time = st.selectbox("Preferred Workout Time", workout_times, key="workout")

            membership_type = st.selectbox("Membership Type", list(membership_types.keys()), key="member_type")
            transaction_date = st.date_input("Membership Start Date", datetime.today(), key="trans_date")
            
            payment_method_key = st.selectbox("Payment Method", list(payment_types.keys()), key="payment")
            
            photo = st.file_uploader("Upload Member's Photo", type=["jpg", "jpeg", "png"], key="photo")

            submit = st.form_submit_button("Submit")

            if submit:
                # Validate required fields
                if not all([nick_name, full_name, gender, phone_number, fitness_goal, preferred_workout_time, photo]):
                    st.error("Please fill out all required fields.")
                else:
                    # Format phone number
                    formatted_phone = format_phone_number(phone_number)
                    if not formatted_phone:
                        st.error("Invalid phone number format. Please enter a valid Indonesian phone number.")
                    else:
                        with st.spinner("Uploading photo and registering member..."):
                            photo_url, temp_file_path, upload_status = upload_image_to_cloudinary(photo)

                            if upload_status == 0:  # Successful upload
                                try:
                                    member_id = len(members_sheet.get_all_records()) + 1
                                    members_sheet.append_row([
                                        member_id,
                                        nick_name,
                                        full_name,
                                        gender,
                                        str(birth_date),
                                        formatted_phone,  # Store formatted phone number
                                        medical_info,
                                        fitness_goal,
                                        preferred_workout_time,
                                        photo_url
                                    ])

                                    transaction_id = f"{datetime.now().strftime('%Y%m%d')}-{member_id}"
                                    membership_type_id = membership_types[membership_type]["id"]
                                    amount = 100  # Assuming a fixed amount for simplicity
                                    payment_method = payment_types[payment_method_key]["payment_method"]

                                    transactions_sheet.append_row([
                                        transaction_id,
                                        member_id,
                                        membership_type_id,
                                        "signup",
                                        amount,
                                        payment_method,
                                        str(transaction_date)
                                    ])
                                    st.success(f"Member '{full_name}' registered successfully with photo uploaded!")
                                except Exception as e:
                                    st.error(f"Error while updating spreadsheet: {e}")
                            else:
                                st.error("Failed to upload photo to Cloudinary.")

    # Streamlit app entry point
    st.title('Sign Up')
    register_member()
