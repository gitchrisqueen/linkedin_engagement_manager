import streamlit as st

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

if __name__ == '__main__':
    main()