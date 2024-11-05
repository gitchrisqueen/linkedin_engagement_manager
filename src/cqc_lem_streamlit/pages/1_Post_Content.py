import streamlit as st
import requests
from datetime import datetime, time

from cqc_lem.api.main import PostRequest

st.title("Schedule Your Post")

# Initialize session state
if "content" not in st.session_state:
    st.session_state.content = ""

# Input fields for content and time
content = st.text_area("Post Content", value=st.session_state.content)
# Date input for selecting the date
selected_date = st.date_input("Select Date", min_value=datetime.today().date())

# Determine the best time for posting based on the selected date
best_times = {
    0: time(14, 0),  # Monday
    1: time(9, 0),   # Tuesday
    2: time(12, 0),  # Wednesday
    3: time(17, 0),  # Thursday
    4: time(23, 0),  # Friday
    5: time(7, 0),   # Saturday
    6: time(9, 0)    # Sunday
}

# Get the best time for the selected date
best_time = best_times[selected_date.weekday()]

#Format the best time to 12-hour format
best_time_12hr = best_time.strftime("%I:%M %p")

# Alert the user the ideal posting time has been selected based on their post day
st.info(f"The best time to post on {selected_date.strftime('%A')} is {best_time_12hr}")

# Time input for selecting the time, prefilled with the best time in 12-hour format
selected_time = st.time_input("Select Time", value=best_time)

# Combine the selected date and time into a single datetime object
scheduled_datetime = datetime.combine(selected_date, selected_time)

# Add input for email address
email = st.text_input("Email Address")


# Button to submit the form
if st.button("Schedule Post"):
    if content and scheduled_datetime and email:
        try:
            post_request = PostRequest(content=content, post_type="text", scheduled_datetime=scheduled_datetime, email=email)

            #st.write(str(post_request.post_json))

            #response = requests.post("http://localhost:8000/schedule_post/", json={
            #    "content": content,
            #    "scheduled_time": scheduled_datetime.isoformat()
            #})
            response = requests.post("http://localhost:8000/schedule_post/", json=post_request.post_json)
            if response.status_code == 200:
                st.success("Post scheduled successfully!")
                # Clear the content field
                st.session_state.content = ''
            else:
                st.error(f"Error ({response.status_code}): {response.json()["detail"]}")
        except ValueError as ve:
            st.error(f"Error: {ve}")
    else:
        st.error("Please provide content,scheduled time and email address.")
