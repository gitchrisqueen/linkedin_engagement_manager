import pandas as pd
import requests
import streamlit as st
from setuptools.command.editable_wheel import editable_wheel
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode

# Initialize the session state
if "email" not in st.session_state:
    st.session_state.email = ""

if "posts" not in st.session_state:
    st.session_state.posts = []


# API endpoint to get posts
GET_POSTS_URL = "http://localhost:8000/posts/"
# API endpoint to update posts
UPDATE_POST_URL = "http://localhost:8000/update_post/"

st.title("Review and Edit Scheduled Posts")

# Input field for email address
email = st.text_input("Enter your email address")

# On email address change make the call to get posts
if st.session_state.email != email:
    st.session_state.email = email
    response = requests.get(f"{GET_POSTS_URL}?email={email}")

    if response.status_code == 200:
        st.success("Posts fetched successfully")
        st.session_state.posts = response.json()['detail']
    else:
        st.error(f"Error ({response.status_code}): {response.json()["detail"]}")

if st.session_state.posts:
    posts = st.session_state.posts

    # Convert posts to a DataFrame
    df = pd.DataFrame(posts, columns=["post_id", "content", "scheduled_time", "post_type", "status"])

    # Configure the editable grid
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_pagination(paginationAutoPageSize=True)
    gb.configure_default_column(editable=True)
    # Make the post_id column non-editable
    gb.configure_column("post_id", editable=False, hide=True)
    # Configure post_type column as a dropdown with enum values
    gb.configure_column("post_type", editable=True, cellEditor='agSelectCellEditor',
                        cellEditorParams={'values': ['text', 'carousel', 'video']})
    # Configure status column as a dropdown with custom values
    gb.configure_column("status", editable_wheel=True,  cellEditor='agSelectCellEditor',
                        cellEditorParams={'values': ['pending', 'approved', 'rejected', 'scheduled', 'posted']})

    grid_options = gb.build()

    # Display the editable grid
    grid_response = AgGrid(
        df,
        gridOptions=grid_options,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        fit_columns_on_grid_load=True,
    )

    # Get the updated data from the grid
    updated_df = grid_response["data"]

    # Check if the DataFrame has been updated
    if not df.equals(updated_df):
        # Send the updated data back to the API
        for index, row in updated_df.iterrows():
            index_str = str(int(index) + 1)
            post_data = {
                "content": row["content"],
                "scheduled_datetime": row["scheduled_time"],
                "post_type": row["post_type"],
                "status": row["status"],
                "email": email
            }
            # Add the post_id to the request query
            post_id = row["post_id"]
            response = requests.post(f"{UPDATE_POST_URL}?post_id={post_id}", json=post_data)
            if response.status_code == 200:
                st.success(f"Post {index_str} updated successfully")
            else:
                st.error(f"Failed to update post {index_str}. Error ({response.status_code}): {response.json()['detail']}")
