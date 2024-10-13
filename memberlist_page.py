import streamlit as st
import pandas as pd
import gspread
from google.oauth2 import service_account
from datetime import datetime, timedelta
import urllib.parse
import cloudinary

def app():
    cloudinary.config(
        cloud_name=st.secrets['cloudinary']['cloud_name'],  # Your Cloudinary cloud name
        api_key=st.secrets['cloudinary']['api_key'],        # Your Cloudinary API key
        api_secret=st.secrets['cloudinary']['api_secret']   # Your Cloudinary API secret
    )

    # Function to format phone numbers
    def format_phone_number(phone_number):
        """
        Formats Indonesian phone numbers to international format without '+'.

        Args:
            phone_number (str): Original phone number (e.g., '08123456789').

        Returns:
            str: Formatted phone number (e.g., '628123456789') or None if invalid.
        """
        phone_number = str(phone_number).strip()
        if phone_number.startswith('0'):
            formatted_number = '62' + phone_number[1:]
        elif phone_number.startswith('+62'):
            formatted_number = phone_number.replace('+', '')
        else:
            formatted_number = phone_number  # Assume it's already in correct format

        # Remove any non-digit characters
        formatted_number = ''.join(filter(str.isdigit, formatted_number))

        # Validate length (Indonesia phone numbers typically have 10-15 digits after country code)
        if 10 <= len(formatted_number) <= 15:
            return formatted_number
        else:
            return None  # Invalid phone number

    def update_phone_number(client, member_id, new_phone_number):
        spreadsheet_id = st.secrets["google_sheets"]["spreadsheet_id"]
        members_sheet = client.open_by_key(spreadsheet_id).worksheet('Members')

        # Find the row number where the member_id is located
        cell = members_sheet.find(str(member_id))
        if cell:
            row_number = cell.row
            # Assuming 'phone_number' is in column 4 (adjust the index as per your sheet)
            phone_number_col_index = members_df.columns.get_loc('phone_number') + 1  # Adding 1 because Google Sheets index starts at 1
            members_sheet.update_cell(row_number, phone_number_col_index, new_phone_number)
        else:
            st.error(f"Member ID {member_id} not found in the sheet.")

    def create_whatsapp_link(formatted_number, message_template):
        """
        Creates a WhatsApp URL with a pre-filled message.

        Args:
            formatted_number (str): Phone number in international format without '+'.
            message_template (str): The message to pre-fill.

        Returns:
            str: WhatsApp URL.
        """
        encoded_message = urllib.parse.quote(message_template)
        whatsapp_url = f"https://wa.me/{formatted_number}?text={encoded_message}"
        return whatsapp_url

    # Define membership types and payment methods
    membership_types = {
        "BULANAN": {"id": 1, "duration": 30}
    }
    payment_types = {
        "Cash": {"id": 1, "payment_method": 'cash'},
        "Trf/Qris": {"id": 2, "payment_method": 'e-money'},
    }

    # Function to calculate membership expiration date
    def calculate_expiration(last_transaction_date, duration_days):
        return last_transaction_date + timedelta(days=duration_days)

    # Initialize Google Sheets connection (without caching)
    def init_connection():
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"],
                scopes=scope
            )
        client = gspread.authorize(creds)
        return client

    # Fetch data from Google Sheets (without caching)
    def get_member_data(_client):
        spreadsheet_id = st.secrets["google_sheets"]["spreadsheet_id"]
        members_sheet = _client.open_by_key(spreadsheet_id).worksheet('Members')
        transactions_sheet = _client.open_by_key(spreadsheet_id).worksheet('Transactions')

        members_data = members_sheet.get_all_records()
        transactions_data = transactions_sheet.get_all_records()

        members_df = pd.DataFrame(members_data)
        transactions_df = pd.DataFrame(transactions_data)

        # Enforce correct data types
        members_df['member_id'] = pd.to_numeric(members_df['member_id'], errors='coerce')
        transactions_df['member_id'] = pd.to_numeric(transactions_df['member_id'], errors='coerce')
        transactions_df['membership_types_id'] = pd.to_numeric(transactions_df['membership_types_id'], errors='coerce')
        transactions_df['transaction_date'] = pd.to_datetime(transactions_df['transaction_date'], errors='coerce')

        # Ensure phone_number is a string
        members_df['phone_number'] = members_df['phone_number'].astype(str)
        members_df['nick_name'] = members_df['nick_name'].astype(str)
        members_df['full_name'] = members_df['full_name'].astype(str)

        # Drop rows with NaN in critical columns
        members_df = members_df.dropna(subset=['member_id'])
        transactions_df = transactions_df.dropna(subset=['member_id', 'membership_types_id', 'transaction_date'])

        # Cast to integer type
        members_df['member_id'] = members_df['member_id'].astype(int)
        transactions_df['member_id'] = transactions_df['member_id'].astype(int)
        transactions_df['membership_types_id'] = transactions_df['membership_types_id'].astype(int)

        return members_df, transactions_df

    # Function to add a new transaction
    def add_transaction(client, transaction_id, member_id, membership_types_id, transaction_type, amount, payment_method, transaction_date, note):
        spreadsheet_id = st.secrets["google_sheets"]["spreadsheet_id"] 
        transactions_sheet = client.open_by_key(spreadsheet_id).worksheet('Transactions')

        # Ensure all values are strings to prevent misinterpretation
        new_transaction = [
            str(transaction_id),       # Transaction ID as string
            str(member_id),            # Member ID as string
            str(membership_types_id),  # Membership Type ID as string
            transaction_type,          # Transaction type
            str(amount),               # Amount as string
            payment_method,            # Payment method
            transaction_date,          # Transaction date as string
            note                       # Note
        ]
        transactions_sheet.append_row(new_transaction, value_input_option='RAW')  # Use 'RAW' to prevent Google Sheets from auto-formatting

    # Create a reverse lookup for membership types
    membership_type_by_id = {v['id']: {'name': k, 'duration': v['duration']} for k, v in membership_types.items()}

    # Function to process member data and assign tags
    def process_member_data(members_df, transactions_df):
        # Merge members_df with transactions_df to get the last transaction for each member
        transactions_df = transactions_df.sort_values(by='transaction_date')
        last_transactions = transactions_df.groupby('member_id').last().reset_index()

        members_with_last_tx = pd.merge(members_df, last_transactions[['member_id', 'transaction_date', 'membership_types_id']], on='member_id', how='left')

        # Calculate membership_expiration
        def calculate_expiration(row):
            last_transaction_date = row['transaction_date']
            membership_type_id = row['membership_types_id']
            if pd.isnull(last_transaction_date) or pd.isnull(membership_type_id):
                return None  # No transactions found
            duration_days = membership_type_by_id.get(membership_type_id, {}).get('duration', 0)
            return last_transaction_date + timedelta(days=duration_days)

        members_with_last_tx['membership_expiration'] = members_with_last_tx.apply(calculate_expiration, axis=1)

        # Calculate days_left
        today = datetime.now().date()
        members_with_last_tx['days_left'] = members_with_last_tx['membership_expiration'].apply(lambda x: (x.date() - today).days if pd.notnull(x) else None)

        # Assign membership_tag
        def assign_membership_tag(days_left):
            if days_left is None or days_left < 0:
                return "Red"
            elif days_left <= 3:
                return "Yellow"
            else:
                return "Green"

        members_with_last_tx['membership_tag'] = members_with_last_tx['days_left'].apply(assign_membership_tag)

        return members_with_last_tx

    # Remove refresh_counter logic since we're using session state
    # Initialize session state variables

    st.session_state['client'] = init_connection()
    st.session_state['members_df'], st.session_state['transactions_df'] = get_member_data(st.session_state['client'])
    
    # Use data from session state
    client = st.session_state['client']
    members_df = st.session_state['members_df']
    transactions_df = st.session_state['transactions_df']

    # Process member data
    members_processed_df = process_member_data(members_df, transactions_df)

    # Streamlit page setup
    st.title("Member List")

    # Filter setup
    search_name = st.text_input("Search", key="search")

    col1, col2 = st.columns(2)

    with col1:
        filter_tag = st.selectbox("Filter by Status", ["All", "Green", "Yellow", "Red"])

    with col2:
        sort_order = st.selectbox("Sort by days left", ["Ascending", "Descending"])

    st.markdown("---")

    # Apply filters
    filtered_df = members_processed_df.copy()

    if filter_tag != "All":
        filtered_df = filtered_df[filtered_df['membership_tag'] == filter_tag]

    # Apply search filter
    if search_name:
        filtered_df = filtered_df[
            filtered_df['nick_name'].str.lower().str.contains(search_name.lower()) |
            filtered_df['full_name'].str.lower().str.contains(search_name.lower())
        ]

    # Apply sorting
    ascending_order = True if sort_order == "Ascending" else False
    filtered_df = filtered_df.sort_values(by='days_left', ascending=ascending_order, na_position='last')

    # Initialize session state for toggling forms
    if 'show_form' not in st.session_state:
        st.session_state['show_form'] = {}

    # Define the message template
    MESSAGE_TEMPLATE = "Good day, resident of Brotot Barbell Club!\nPlease renew your gym membership as soon as possible!\n\nBest Regards,\nIdam"

    # Display each member's details in cards
    for index, row in filtered_df.iterrows():
        member_id = row['member_id']
        membership_expiration = row['membership_expiration']
        days_left = row['days_left']
        membership_tag = row['membership_tag']

        with st.container():
            cols = st.columns([1, 2])

            with cols[0]:
                st.markdown(f"""
                <img src="{row['photo_url']}" style="width:200px; height:266px; object-fit:cover; border-radius:10px;">
                """, unsafe_allow_html=True)
            with cols[1]:
                st.markdown("""
                    <link href="https://fonts.googleapis.com/css2?family=Holtwood+One+SC&display=swap" rel="stylesheet">
                    """, unsafe_allow_html=True)

                st.markdown(f"""
                    <span style='font-family: "Holtwood One SC", serif;
                    font-weight: 400;
                    font-style: normal, cursive; font-size:32px; color:#FFFFFF;'>
                        {row['nick_name']}
                    </span>
                    """, unsafe_allow_html=True)

                # Format the phone number
                original_phone = row['phone_number']
                formatted_phone = format_phone_number(original_phone)
                if formatted_phone:
                    # Create WhatsApp link
                    whatsapp_link = create_whatsapp_link(formatted_phone, MESSAGE_TEMPLATE)
                    # Display clickable phone number
                    st.markdown(f"[**Send Whatsapp Message**]({whatsapp_link})")
                else:
                    st.markdown(f"**Phone Number**: {original_phone} (Invalid Format)")

                # Display the days left with appropriate color coding
                if days_left is None or days_left < 0:
                    st.error(f"Membership expired {abs(days_left) if days_left is not None else ''} days ago.")
                elif days_left <= 3:
                    st.warning(f"Membership expires in {days_left} days.")
                else:
                    st.success(f"Membership expires in {days_left} days.")

                if f"show_form_{index}" not in st.session_state:
                    st.session_state[f"show_form_{index}"] = False

                if st.button("Renew Membership", key=f"renew_{index}"):
                    st.session_state[f"show_form_{index}"] = True

                if st.session_state[f"show_form_{index}"]:
                    with st.form(key=f"renew_form_{index}"):
                        st.write("**Renew Membership**")
                        amount = st.number_input("Amount", min_value=0.0, value=80.0, key=f"amount_{index}")
                        payment_method_key = st.selectbox("Payment Method", list(payment_types.keys()), key=f"payment_{index}")
                        payment_method = payment_types[payment_method_key]["payment_method"]
                        duration_days = st.number_input("Duration (days)", min_value=1, value=30, key=f"duration_{index}")
                        transaction_date_input = st.date_input("Membership Start Date", datetime.today(), key=f"trans_date_{index}")

                        # Optional: Add a field for notes
                        note = st.text_input("Note (optional)", key=f"note_{index}")

                        submitted = st.form_submit_button("Submit")
                        if submitted:
                            # Ensure member_id is correctly typed
                            member_id_str = str(member_id)
                            # Generate transaction_id
                            transaction_id = f"{transaction_date_input.strftime('%Y%m%d')}-{member_id_str}"
                            membership_type_id = 1  # Assuming a fixed membership type for simplicity
                            transaction_type = "renewal"

                            transaction_date_str = transaction_date_input.strftime('%Y-%m-%d')

                            add_transaction(
                                client,
                                transaction_id,
                                member_id_str,
                                membership_type_id,
                                transaction_type,
                                amount,
                                payment_method,
                                transaction_date_str,
                                note
                            )
                            st.success("Membership renewed!")

                            # Remove data from session state to force refresh
                            del st.session_state['members_df']
                            del st.session_state['transactions_df']

                            # Re-fetch the data and store it in session state
                            st.session_state['members_df'], st.session_state['transactions_df'] = get_member_data(client)
                            members_processed_df = process_member_data(st.session_state['members_df'], st.session_state['transactions_df'])

                            # Re-apply filters
                            filtered_df = members_processed_df.copy()
                            if filter_tag != "All":
                                filtered_df = filtered_df[filtered_df['membership_tag'] == filter_tag]
                            if search_name:
                                filtered_df = filtered_df[
                                    filtered_df['nick_name'].str.lower().str.contains(search_name.lower()) |
                                    filtered_df['full_name'].str.lower().str.contains(search_name.lower())
                                ]
                            st.session_state[f"show_form_{index}"] = False

                    if st.button("Cancel", key=f"cancel_{index}"):
                        st.session_state[f"show_form_{index}"] = False

            st.divider()
