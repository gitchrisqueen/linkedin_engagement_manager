#  Copyright (c) 2024. Christopher Queen Consulting LLC (http://www.ChristopherQueenConsulting.com/)
import os

import streamlit as st

from cqc_lem.streamlit.utils import get_custom_css
from cqc_lem.streamlit.utils import read_file


# Initialize session state variables
# init_session_state()


def main():
    st.set_page_config(layout="wide", page_title="LinkedIn Engagement Manager", page_icon="📚🤖")

    css = get_custom_css()
    st.markdown(
        css,
        unsafe_allow_html=True
    )

     # TODO: Emulate the main page from http://commentify.co (Research what its built on)  - Develop a similar pricing structure with a free timee trial tier

    st.header("Welcome!!! 👋")

    # Get the ReadMe Markdown and display it
    current_directory = os.path.dirname(os.path.abspath(__file__))
    # parent_directory = os.path.dirname(current_directory)
    readme_markdown = read_file(current_directory + "/README.md")

    st.markdown(readme_markdown)


if __name__ == '__main__':
    main()
