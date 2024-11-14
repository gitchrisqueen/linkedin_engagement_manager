import os

import streamlit as st
from linkedin_api.clients.auth.client import AuthClient

from cqc_lem_streamlit.utils import get_file_as_data_image


# Function to load user data (replace with actual data loading logic)
def load_user_data():
    # TODO: Implement thisi function
    return {
        "username": "christopher.queen",
        "email": "christopher.queen@gmail.com",
        "blog_url": "https://www.christopherqueenconsulting.com/blog",
        "sitemap_url": "https://www.christopherqueenconsulting.com/sitemap.xml"
    }


# Function to save user data (replace with actual data saving logic)
def save_user_data(user_data):
    # Implement the logic to save user data
    pass


def main():
    st.set_page_config(layout="wide", page_title="My Account", page_icon="👤")

    st.header("My Account")

    # Load user data
    user_data = load_user_data()

    # Display user information
    st.subheader("User Information")
    st.text(f"Username: {user_data['username']}")
    st.text(f"Email: {user_data['email']}")

    # Editable fields for blog URL and sitemap URL
    st.subheader("Edit URLs")
    blog_url = st.text_input("Blog URL", user_data["blog_url"])
    sitemap_url = st.text_input("Sitemap URL", user_data["sitemap_url"])

    # Save button
    if st.button("Save"):
        user_data["blog_url"] = blog_url
        user_data["sitemap_url"] = sitemap_url
        save_user_data(user_data)
        st.success("User data updated successfully!")

    # Checkbox for user to consent to storing LinkedIn Data
    st.subheader("LinkedIn Data Consent")
    agreement_label = "I agree to let LinkedIn Engagement Manager store my LinkedIn data."
    consent = st.checkbox(agreement_label)

    current_dir = os.path.dirname(__file__)
    active_image_path = os.path.join(current_dir,
                                     '../libs/signin_with_linkedin-buttons/Retina/Sign-In-Small---Active.png')
    hover_image_path = os.path.join(current_dir,
                                    '../libs/signin_with_linkedin-buttons/Retina/Sign-In-Small---Hover.png')

    auth_url = ''

    if consent:
        # Get needed environment variables
        client_id = os.getenv("LI_CLIENT_ID")
        client_secret = os.getenv("LI_CLIENT_SECRET")
        redirect_url = os.getenv("LI_REDIRECT_URL")
        state = os.getenv("LI_STATE_SALT")

        #  Exchange code for access token
        client = AuthClient(client_id, client_secret, redirect_url)

        auth_url = client.generate_member_auth_url(
            state=state,
            scopes=["openid", "profile", "email", "w_member_social"]
        )

        #st.write(f"""Auth URL: {auth_url}""")

        # Authorize LinkedIn for API Usage
        st.markdown(
            f"""
            <style>
            .button {{
                background-image: url('{get_file_as_data_image(active_image_path)}');
                background-repeat: no-repeat;
                background-size: cover;
                width: 292px;
                height: 40px;
                border: none;
                cursor: pointer;
            }}
            .button:hover {{
                background-image: url('{get_file_as_data_image(hover_image_path)}');
            }}
            .button:disabled {{
                cursor: not-allowed;
                opacity: 0.5;
            }}
            </style>
            
            """,
            unsafe_allow_html=True
        )

    st.link_button(label=f"Sign In with LinkedIn", url=auth_url, disabled=not consent)


if __name__ == '__main__':
    main()
