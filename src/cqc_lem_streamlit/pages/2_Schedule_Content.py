import streamlit as st
import requests
from datetime import datetime, time

from cqc_lem.api.main import PostRequest
from cqc_lem.utilities.jaeger_tracer_helper import get_jaeger_tracer
from cqc_lem.utilities.utils import get_best_posting_time, get_12h_format_best_time

st.title("Schedule Your Post")

# Initialize session state
if "content" not in st.session_state:
    st.session_state.content = ""

# Input fields for content and time
content = st.text_area("Post Content", value=st.session_state.content)

# Date input for selecting the date
selected_date = st.date_input("Select Date", min_value=datetime.today().date())

# Get the best time for the selected date
best_time = get_best_posting_time(selected_date)

#Format the best time to 12-hour format
best_time_12hr = get_12h_format_best_time(best_time)

# Alert the user the ideal posting time has been selected based on their post day
st.info(f"The best time to post on {selected_date.strftime('%A')} is {best_time_12hr}")

# Time input for selecting the time, prefilled with the best time in 12-hour format
selected_time = st.time_input("Select Time", value=best_time)

# Combine the selected date and time into a single datetime object
scheduled_datetime = datetime.combine(selected_date, selected_time)

# Add input for email address
email = st.text_input("Email Address")

tracer = get_jaeger_tracer("streamlit", __name__)

with tracer.start_as_current_span("schedule_post"):

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
