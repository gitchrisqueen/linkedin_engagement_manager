import json
import os
import sys
from collections import OrderedDict
from datetime import datetime, timedelta

from dotenv import load_dotenv
from imessage_reader import fetch_data
from openai import OpenAI
from fpdf import FPDF

class EnvironmentLoader:
    @staticmethod
    def load_env(file_path='focus_group.env'):
        load_dotenv(file_path)
        focus_group_str = os.getenv('FOCUS_GROUP')
        focus_group_str = focus_group_str.replace('\\"', '"')  # Unescape double quotes
        #print(f"FOCUS_GROUP: {focus_group_str}")  # Debugging line
        return {
            'DB_PATH': os.getenv('DB_PATH'),
            'FONT_PATH': os.getenv('FONT_PATH'),
            'PDF_BASE_FILE_NAME': os.getenv('PDF_BASE_FILE_NAME'),
            'FOCUS_GROUP': json.loads(focus_group_str)
        }

class DatabaseHandler:
    def __init__(self, db_path):
        self.db_path = os.path.expanduser(db_path)
        self._validate_db_path()
        self.fd = fetch_data.FetchData(self.db_path)

    def _validate_db_path(self):
        if not os.path.exists(self.db_path):
            sys.exit(f"Error: The database file '{self.db_path}' does not exist.")
        if not os.access(self.db_path, os.R_OK):
            sys.exit(f"Error: The database file '{self.db_path}' is not readable.")

    def fetch_messages(self):
        return self.fd.get_messages()

class DataProcessor:
    @staticmethod
    def filter_messages(messages, focus_group, days=7):
        test_data = {}
        for user_id, message, date, service, account, is_from_me in messages:

            # Debugging line
            if is_from_me:
                #print(f"From Me User ID : {user_id} | Account: {account} |  Message:  {message}")
                # See if it is to someone else in the focus group
                if user_id in focus_group:
                    user_id = account # Swap the user id with the account
                else:
                    continue

            if user_id not in focus_group:
                continue

            date_obj = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
            if date_obj < datetime.now() - timedelta(days=days):
                continue

            if user_id not in test_data:
                test_data[user_id] = []

            if message is not None:
                test_data[user_id].append(message)
        return test_data

class Summarizer:
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)

    def summarize(self, messages):
        prompt = (f"""Analyze the provided messages and determine the person’s political stance based on the following criteria:

                    1. Political Affiliation
                    2. Political Wing
                    3. Supported and Opposed Policies
                    4. Additional Observations

                    Provide the summary in JSON format as specified.

                    Messages::\n\n{messages}\n\n"

                    Take a deep breath and work on this problem step-by-step.""")

        content = [{"type": "text", "text": prompt}]
        system_prompt = {
            "role": "system",
            "content": f"""Act as a political analyst with expertise in U.S. politics. You will receive a list of text messages from a single individual, each reflecting their personal views on various political topics. Your objective is to analyze the text messages and determine the person’s political stance based on the following criteria:

            1. **Political Affiliation**: Based on the content, identify the political party or movement that best aligns with the individual’s beliefs (e.g., Democratic, Republican, Libertarian, Green, etc.).

            2. **Political Wing**: Assess whether they lean more towards the left, center-left, center, center-right, or right-wing based on the topics discussed and the tone of their responses.

            3. **Supported and Opposed Policies**: Identify specific political policies they support or oppose. Include stances on economic issues, social issues, healthcare, immigration, education, environmental policies, and foreign relations, if mentioned.

            4. **Additional Observations**: Note any significant ideological patterns, specific values (e.g., individual freedom, social equity), or concerns that stand out.

            Provide the summary in a concise JSON format with each of these aspects in clearly labeled fields.

            Here is the format for the JSON response:
            ```json
            {{
            "PoliticalAffiliation": "Party or movement name",
              "PoliticalWing": "left, center-left, center, center-right, or right",
              "SupportedPolicies": ["List of policies they support"],
              "OpposedPolicies": ["List of policies they oppose"],
              "AdditionalObservations": ["Any notable patterns or values in their views"]
            }}
            ```

            Take a deep breath and work on this problem step-by-step.
            """
        }

        user_message = {
            "role": "user",
            "content": content
        }

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[system_prompt, user_message],
            temperature=0.5,
            response_format={"type": "json_object"},
        )

        return response.choices[0].message.content.strip()

class PDFGenerator(FPDF):
    def __init__(self, font_path):
        super().__init__()
        self.add_font('ArialUnicode', '', os.path.join(font_path, 'Arial-Unicode-MS.ttf'), uni=True)
        self.add_font('ArialUnicode', 'B', os.path.join(font_path, 'Arial-Unicode-Bold.ttf'), uni=True)
        self.add_font('ArialUnicode', 'I', os.path.join(font_path, 'Arial-Unicode-Italic.ttf'), uni=True)
        self.add_font('ArialUnicode', 'BI', os.path.join(font_path, 'Arial-Unicode-Bold-Italic.ttf'), uni=True)

    def get_brand_colors_hex(self, level: int = 0):
        colors = {0: "000000", 1: "B8860B"}
        level = max(0, min(level, len(colors) - 1))
        return colors[level]

    @staticmethod
    def hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

    def header(self):
        self.set_font('ArialUnicode', 'B', 12)
        self.set_text_color(*self.hex_to_rgb(self.get_brand_colors_hex(1)))
        self.cell(0, 10, 'SPR 07 Gamma I - Political Analysis', 0, 1, 'C')

    def footer(self):
        self.set_y(-15)
        self.set_font('ArialUnicode', 'I', 8)
        self.set_text_color(*self.hex_to_rgb(self.get_brand_colors_hex(0)))
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def chapter_title(self, title):
        self.set_font('ArialUnicode', 'B', 14)
        self.set_text_color(*self.hex_to_rgb(self.get_brand_colors_hex(1)))
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(4)

    def chapter_body(self, body):
        self.set_font('ArialUnicode', '', 12)
        self.set_text_color(*self.hex_to_rgb(self.get_brand_colors_hex(0)))
        self.set_text_color(*self.hex_to_rgb(self.get_brand_colors_hex(0)))
        self.multi_cell(0, 10, body)
        self.ln()

    def add_bullet_points(self, items):
        self.set_font('ArialUnicode', '', 12)
        self.set_text_color(*self.hex_to_rgb(self.get_brand_colors_hex(0)))
        for item in items:
            self.multi_cell(0, 10, f'• {item}', 0, 'L')
        self.ln()

    def generate_pdf(self, user_summaries, focus_group, base_file_name):
        filename = f"{base_file_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        for user_id, summary in user_summaries.items():
            self.add_page()
            self.set_font('ArialUnicode', '', 16)
            self.cell(0, 10, f"Summary for {focus_group[user_id]}", 0, 1, 'C')
            self.set_font('ArialUnicode', 'B', 12)

            summary_data = json.loads(summary)
            self.chapter_title("Political Affiliation")
            self.chapter_body(summary_data["PoliticalAffiliation"])

            self.chapter_title("Political Wing")
            self.chapter_body(summary_data["PoliticalWing"])

            self.chapter_title("Supported Policies")
            self.add_bullet_points(summary_data["SupportedPolicies"])

            self.chapter_title("Opposed Policies")
            self.add_bullet_points(summary_data["OpposedPolicies"])

            self.chapter_title("Additional Observations")
            self.add_bullet_points(summary_data["AdditionalObservations"])

            self.ln()
            self.set_font('ArialUnicode', 'I', 10)
            self.cell(0, 10, f"End Summary Of: {focus_group[user_id]}", 0, 1, 'R')

        if os.path.exists(filename):
            os.remove(filename)
        self.output(filename)
        print(f"PDF file saved as '{filename}'")

def main():
    env_vars = EnvironmentLoader.load_env()
    db_handler = DatabaseHandler(env_vars['DB_PATH'])
    messages = db_handler.fetch_messages()
    test_data = DataProcessor.filter_messages(messages, env_vars['FOCUS_GROUP'])

    load_dotenv()
    summarizer = Summarizer(api_key=os.getenv("OPENAI_API_KEY"))

    user_summaries = OrderedDict()
    for user_id, messages in test_data.items():
        messages.reverse()
        text = " \n".join(messages)
        summary = summarizer.summarize(text)
        user_summaries[user_id] = summary
        #break # TODO: delete this stopping for one here

    pdf_generator = PDFGenerator(env_vars['FONT_PATH'])
    pdf_generator.generate_pdf(user_summaries, env_vars['FOCUS_GROUP'], env_vars['PDF_BASE_FILE_NAME'])

if __name__ == "__main__":
    main()