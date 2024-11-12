import random

import openai
from dotenv import load_dotenv
from openai import OpenAI

from cqc_lem.linked_in_profile import LinkedInProfile
from cqc_lem.utilities.logger import myprint

# Load .env file
load_dotenv()

# Retrieve OpenAI API key from environment variables
# openai.api_key = os.getenv("OPENAI_API_KEY") #<---- This is done be default
client = OpenAI(
    # This is the default and can be omitted
    # api_key=os.environ.get("OPENAI_API_KEY"),
)


def generate_ai_response_test():
    post_content = "Today was a good day to go outside"
    post_img_url = None,
    expertise = "dog that speaks to humans"

    prompt = f"Please tell me:\n\n'{post_content}'"

    content = [{"type": "text", "text": prompt}]

    if post_img_url:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"{post_img_url}"},
        })

    # System prompt to be included in every request
    system_prompt = {
        "role": "system",
        "content": f"""Act like a {expertise}. Respond to all user prompts with 'bark bark' followed by your response to the prompt then ending in 'bark bark'"""
    }

    # User prompt to be sent with each API call
    user_message = {
        "role": "user",
        "content": content
    }

    # Call the API with the system and user prompt only (no memory of past prompts)
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # Specify the model you want to use
        messages=[system_prompt, user_message],  # System prompt + current user prompt
        # temperature=0.3,  # Adjust this parameter as per your needs
        # max_tokens=150  # Set token limit as required
    )

    # Extract and return the model's response
    comment = response.choices[0].message.content.strip()
    return comment


def generate_ai_response(post_content, profile: LinkedInProfile, post_img_url=None):
    image_attached = "(image attached)" if post_img_url else ""

    prompt = (f"""Please give me a comment in response to the following LinkedIn Content as the following LinkedIn User,"
              
                LinkedIn User Profile:\n\n{profile.model_dump_json()}\n\n"
              
                LinkedIn Content{image_attached}:\n\n'{post_content}'

                Only provide the final comment once it perfectly reflects the LinkedIn user’s style
                
                Do not surround your response in quotes or added any additional system text.

                Take a deep breath and work on this problem step-by-step.""")

    content = [{"type": "text", "text": prompt}]

    if post_img_url:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"{post_img_url}"},
        })

    # System prompt to be included in every request
    system_prompt = {
        "role": "system",
        "content": f"""Act like the LinkedIn profile user whose details you are about to analyze. 
        You have an extensive background in LinkedIn engagement, social media, and social marketing, with a specific expertise in aligning comments and content to an individual’s personal and professional style. 
        You excel at understanding a person's tone, interests, and the way they communicate online, especially on LinkedIn.
        
        Your main objective is to generate insightful, relevant comments in response to provided content, using the tone, voice, and style of the profile user. 
        These comments should align with the user’s professional identity and communication style, fostering engagement and authority.
        
        Step-by-step process:
        1. Analyze the LinkedIn profile provided: Carefully examine the user's tone, interests, and speaking style based on their LinkedIn activity. Identify patterns in how they engage with others—whether their tone is formal or informal, motivational or technical, concise or elaborate.
        2. Assess the content to be responded to: Identify the key points in the content you need to respond to. Make sure you understand its context within the broader conversation.
        3. Generate a response: Craft a thoughtful, insightful comment that matches the voice and style of the LinkedIn profile user. Use the following guidelines:
            - Reflect the user’s professional expertise and unique style of communication.
            - Keep the tone either conversational or authoritative, depending on the user’s style.
            - Engage others by making your response relevant to the ongoing conversation.
            - Be concise but impactful—focus on making the first 2-3 lines (~400 characters) compelling to encourage readers to expand and read more.
        4. Ensure relevance: The response should contribute value to the conversation. Draw connections between the content presented and the user's professional background.
        5. Maintain brevity and engagement: Keep the comment under 1250 characters, including spaces and punctuation. Aim to foster further discussion without overwhelming the reader with excessive information.
        6. Incorporate links if relevant: If there are links in the original content or discussion, briefly reference them if they are directly applicable. Use this to add depth to your response.
        
        Be original, creative, and insightful in your comment, always aiming to mirror the LinkedIn profile user’s tone, foster engagement, and drive further conversation.
        
        Take a deep breath and work on this problem step-by-step.
        
        Only respond with your final comment once you are satisfied with its quality, relevance, and alignment with the LinkedIn user’s style.
        """
    }

    # User prompt to be sent with each API call
    user_message = {
        "role": "user",
        "content": content
    }

    # Choose temperature between .5 and .7 rounded to 2 decimal places
    temperature = round(random.uniform(.5, .7), 2)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[system_prompt, user_message],  # System prompt + current user prompt
        temperature=temperature,  # Adjust this parameter as per your needs
        # max_tokens=150  # Set token limit as required
    )

    comment = response.choices[0].message.content.strip()
    return comment


def get_ai_description_of_profile(linked_in_profile: LinkedInProfile):
    # Use json to output to string
    linked_in_profile_json = linked_in_profile.model_dump_json()
    prompt = f"""Please tell me what appears to be this person's personal interest based on their current job, skills, and recent activities.
             A short summary of your analysis of around 500 characters is all that is needed.
             Person: {linked_in_profile_json}"""

    # myprint(f"Prompt: {prompt}")

    content = [{"type": "text", "text": prompt}]

    # System prompt to be included in every request
    system_prompt = {
        "role": "system",
        "content": f"""Act like a professional career coach and personality analyst with over 20 years of experience in understanding human behavior through social media profiles, particularly LinkedIn. Your expertise is in evaluating profiles to determine personal and professional character traits based on the content of their work experience, endorsements, skills, recommendations, posts, and interactions.

        Your objective is to thoroughly analyze LinkedIn profile data to extract insights about the individual’s character traits, such as leadership, teamwork, creativity, reliability, adaptability, communication skills, and more. Use subtle cues from the person's descriptions of job roles, their endorsements from others, the language used in their recommendations, and their professional interactions to form a comprehensive assessment. Ensure to identify both overt and nuanced traits, and support each finding with examples from the profile content. Pay special attention to the consistency between the skills endorsed by others and the responsibilities listed by the individual.
        
        Follow these steps:
        1. Start by identifying the general tone and language used in the profile, which may indicate personality traits like enthusiasm, confidence, or humility.
        2. Examine the person’s job titles and descriptions to identify traits such as leadership, initiative, and problem-solving abilities.
        3. Analyze the endorsements and recommendations, looking for patterns in how others describe the individual. Highlight any common traits mentioned (e.g., dependability, collaboration).
        4. Evaluate posts or comments for signs of professional engagement, thought leadership, or community involvement.
        5. Conclude with a comprehensive summary that combines these insights into a clear picture of the individual’s character traits, citing specific parts of the profile to support your findings.
        
        Take a deep breath and work on this problem step-by-step."""
    }

    # User prompt to be sent with each API call
    user_message = {
        "role": "user",
        "content": content
    }

    # Call the API with the system and user prompt only (no memory of past prompts)
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # Specify the model you want to use
        messages=[system_prompt, user_message],  # System prompt + current user prompt
        # temperature=0.3,  # Adjust this parameter as per your needs
        # max_tokens=150  # Set token limit as required
    )

    # Extract and return the model's response
    comment = response.choices[0].message.content.strip()
    return comment


def get_ai_message_refinement(original_message: str, character_limit: int = 300):
    character_limit_string = f"\nThe refined message needs to be less than or equal to {character_limit} characters including white spaces.\n\n " if character_limit > 0 else ""

    prompt = f"""Please review and refine the following message. {character_limit_string} Message: {original_message}
            """

    # myprint(f"Prompt: {prompt}")

    content = [{"type": "text", "text": prompt}]

    # System prompt to be included in every request
    system_prompt = {
        "role": "system",
        "content": f"""Act like a professional editor with expertise in communication for business professionals, particularly on platforms like LinkedIn. 
            You have helped clients refine and streamline their messaging for more than 15 years, ensuring clarity, professionalism, and engagement.
    
            Your task is to review a provided message. The goal is to ensure the message makes sense, reads smoothly, and presents key information in a clear, concise, and professional manner. Additionally, modify any titles, phrases, or sections that seem overly long, awkward, or redundant. 
            Your revisions should maintain the original intent while improving readability and impact.
            
            The review process includes:
            1. Check for clarity and coherence: Ensure the message has a logical flow and that each sentence connects smoothly to the next. Eliminate or revise any confusing or ambiguous phrases.
            2. Refine long titles and sections: Shorten overly detailed sections, such as professional titles, while preserving their key points. Ensure these parts are clear but not excessive.
            3. Improve engagement: The message should feel personalized and engaging. Identify opportunities to make the message more concise and approachable, particularly in the introduction and closing.
            4. Polish for professionalism: Ensure a professional tone throughout, appropriate for business communication.
            
            A final direct refined response without a subject line is all that is needed. 
            
            Take a deep breath and work on this problem step-by-step.
            """
    }

    # User prompt to be sent with each API call
    user_message = {
        "role": "user",
        "content": content
    }

    # Call the API with the system and user prompt only (no memory of past prompts)
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # Specify the model you want to use
        messages=[system_prompt, user_message],  # System prompt + current user prompt
        # temperature=0.3,  # Adjust this parameter as per your needs
        # max_tokens=150  # Set token limit as required
    )

    # Extract and return the model's response
    comment = response.choices[0].message.content.strip()
    return comment


def get_video_content_from_ai(linked_user_profile: LinkedInProfile, buyer_stage: str):
    """Generate video content based on the LinkedIn user profile and buyer stage."""

    # Use json to output to string
    linked_in_profile_json = linked_user_profile.model_dump_json()

    prompts = [f"""Create a short, high-impact video script tailored for LinkedIn to introduce and build awareness about the expertise or unique value of the profile represented by the following LinkedIn Profile. 
                This video should appeal to users in the {buyer_stage} stage, aiming to quickly capture attention with a clear, memorable introduction. 
                Use a 1:1 aspect ratio and keep the length to 30 seconds. 
                Make the tone approachable and professional, with the visual style matching any brand cues present in the profile data. 
                End with a subtle call to action that encourages viewers to explore further.
                
                """,
               f"""Generate a 45-second LinkedIn explainer video script highlighting the unique strengths and offerings of the following LinkedIn Profile for an audience in the {buyer_stage} stage.
               The script should present three key features or advantages that demonstrate why this profile or brand stands out as a valuable solution. 
               Use a 16:9 aspect ratio with a clean, professional design, and ensure pacing is steady enough to allow viewers to grasp each point. 
               Conclude with a call to action, inviting viewers to connect, learn more, or engage further on LinkedIn.
                
                """,

               f"""Design a compelling video script for LinkedIn that solidifies the following LinkedIn Profile as the top choice for viewers in the {buyer_stage} stage. 
               Focus on driving conversions by presenting clear reasons why this profile or brand is a trustworthy choice, with emphasis on relevant accomplishments, client testimonials, or standout capabilities. 
               The video should run for about 60 seconds in a 16:9 format, with a polished, confidence-inspiring visual style. 
               End with a strong call to action encouraging immediate engagement, such as scheduling a demo or visiting the profile’s website.
                
                """,
               ]

    prompt = random.choice(prompts)

    myprint(f"Pre-Prompt: {prompt}")

    # Add the Linked JSon profile to end of prompt
    prompt += f"\n ###LinkedIn Profile: {linked_in_profile_json}"

    content = [{"type": "text", "text": prompt}]

    # System prompt to be included in every request
    system_prompt = {
        "role": "system",
        "content": f"""Act like an experienced video marketing strategist and content creator.** You have years of expertise in crafting LinkedIn-specific video content designed to appeal to distinct stages of the buyer's journey, from awareness to decision. Your goal is to ensure the video aligns closely with the user's input and ChatGPT's known limitations, providing a professional, impactful result.

        ### Objective
        Based on the LinkedIn profile data and specified buyer’s journey stage provided by the user, generate a script and design elements for a LinkedIn-optimized video. This video should resonate with the intended audience and adhere to LinkedIn’s best practices for viewer engagement and platform compatibility.
        
        ### Requirements
        
        1. **Define the Purpose and Audience:**
           - **Purpose:** Confirm the video's intent (e.g., “Introduce brand expertise in X industry,” “Engage and educate,” or “Drive contact form submissions”).
           - **Audience:** Tailor content to specific audience characteristics (e.g., “Industry experts seeking solutions,” “New users in discovery phase,” or “Decision-makers comparing vendors”).
        
        2. **Content and Visual Elements:**
           - **Script/Text Content:** Use clear, persuasive language that aligns with the provided buyer’s journey stage. Include main points, key messages, or highlights of the LinkedIn profile as relevant to that stage.
           - **Visual Style Preferences:** Specify tone and branding style—options may include minimalist/professional, vibrant/playful, or tech-focused. Match any color schemes or styles from the LinkedIn profile to ensure consistency.
           - **Incorporate Media Elements:** Define any required images, logos, icons, or infographics and where they should appear. Provide guidance on placement if the user has particular preferences.
           - **Backgrounds:** Determine whether a plain color, gradient, or branded background image will support the video’s professionalism and viewer engagement.
        
        3. **Format and Resolution:**
           - **Resolution and Aspect Ratio:** For LinkedIn, prioritize clarity in 1080p for visibility. Common aspect ratios include:
             - **16:9 (Landscape)** – ideal for general LinkedIn posts or YouTube.
             - **1:1 (Square)** – suitable for LinkedIn feeds.
             - **9:16 (Vertical)** – optimized for LinkedIn Stories and mobile users.
        
        4. **Timing and Pacing:**
           - **Length:** Define video length in seconds, aligning with LinkedIn’s ideal engagement window (e.g., keep under 30 seconds for promotions or under 60 seconds for short explainer videos).
           - **Pacing:** Match the video speed to the stage of the buyer’s journey (e.g., fast-paced for awareness, slower for in-depth explanation or education).
        
        5. **Audio Considerations:**
           - **Voiceover and Background Music:** Specify if a voiceover is desired, with script options if relevant. If using AI narration, ensure the voice tone matches the audience’s preferences (e.g., authoritative, friendly, or conversational). Mention any background music styles that enhance the mood without detracting from the message.
        
        6. **Clear Call to Action (CTA):**
           - **CTA**: Specify the ending message, logo placement, and any desired CTAs, such as “Connect with us on LinkedIn,” “Learn more on our website,” or “Request a free demo.”
        
        Take a deep breath and work on this problem step-by-step. 
    """
    }

    # User prompt to be sent with each API call
    user_message = {
        "role": "user",
        "content": content
    }

    # Call the API with the system and user prompt only (no memory of past prompts)
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # Specify the model you want to use
        messages=[system_prompt, user_message],  # System prompt + current user prompt
        # temperature=0.3,  # Adjust this parameter as per your needs
        # max_tokens=150  # Set token limit as required
        #response_format={"type": "json_object"},
    )

    # Extract and return the model's response
    final_prompt = response.choices[0].message.content.strip()
    video_url = create_video_from_prompt(final_prompt)
    return video_url


def summarize_recent_activity(recent_activity_profile: LinkedInProfile, main_profile: LinkedInProfile):
    recent_activity_profile_sting = ''.join([f"{i + 1}. {activity.text} - [{activity.link}]\n" for i, activity in
                                             enumerate(recent_activity_profile.recent_activities)])

    # Clone the main profile and remove recent activities to reduce confusion form AI
    main_profile = main_profile.model_copy(deep=True)
    main_profile.recent_activities = []

    main_profile_json = main_profile.model_dump_json()
    prompt = f"""We are analyzing the interests of one LinkedIn user (main_profile) and want to help them craft a personalized response to another LinkedIn user (second_profile) based on the second user's recent activities. 
    Analyze the main_profile’s interests and select the most relevant activity from second_profile’s list of recent activities. 
    Then, create a response as if it’s from main_profile to second_profile, mentioning the most relevant recent activity and providing a professional comment.

    Main Profile (User 1):
    {main_profile_json}
    
    Second Profile (User 2):
    Name: {recent_activity_profile.full_name}
    Recent Activities:
    {recent_activity_profile_sting}
    
    Create a response from {main_profile.full_name} to {recent_activity_profile.full_name} that references the most relevant recent activity from {recent_activity_profile.full_name}’s list.

    A short final response starting with 'I saw your recent post about' is all that is needed.
    """

    # myprint(f"Prompt: {prompt}")

    content = [{"type": "text", "text": prompt}]

    # System prompt to be included in every request
    system_prompt = {
        "role": "system",
        "content": f"""Act like a professional career coach and personality analyst with over 20 years of experience in analyzing LinkedIn profiles and assessing professional interests. Your expertise lies in evaluating profiles to understand character traits and key interests, as well as identifying relevant connections between users based on their professional activities and interactions.

        You will be provided with details of a LinkedIn profile (main_profile) and a list of recent activities from another profile (recent_activities). Your objective is twofold:
        
        1. Analyze the main_profile to understand their core professional interests, focus areas, and potential motivations.
        2. Review the recent_activities and select the one that is most relevant to the interests of the main_profile. This may include shared professional fields, emerging trends that match their focus, or topics that directly address the needs of the main_profile.
        
        Once you identify the most relevant recent activity, compose a professional response. The response should acknowledge the activity and link it to the main_profile’s interests using a thoughtful and engaging tone. Use the following structure:
        
        - Begin by referencing the recent activity in a polite and personalized manner.
        - Summarize the most relevant recent activity.
        - Include the link for reference.
        - Provide a brief, positive analysis using a professional adjective to describe the relevance of the activity to the main_profile.
        
        Follow these steps:
        1. Analyze the provided main_profile data to understand their professional interests and areas of focus.
        2. Review the list of recent_activities, including the text and links, and identify the one that most closely aligns with the main_profile’s interests.
        3. Craft a response using the format: 'I also saw your recent post about [most relevant activity text summary] [insert_link_recent_activity] and found it [insert_professional_adjective]'. Ensure the adjective aligns with the nature of the content (e.g., insightful, innovative, thought-provoking, etc.).
        
        Take a deep breath and work on this problem step-by-step."""
    }

    # User prompt to be sent with each API call
    user_message = {
        "role": "user",
        "content": content
    }

    # Call the API with the system and user prompt only (no memory of past prompts)
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # Specify the model you want to use
        messages=[system_prompt, user_message],  # System prompt + current user prompt
        # temperature=0.3,  # Adjust this parameter as per your needs
        # max_tokens=150  # Set token limit as required
    )

    # Extract and return the model's response
    result = response.choices[0].message.content.strip()
    return result

def create_video_from_prompt(prompt :str):
    response = openai.Video.create(
        model="video-davinci-003",
        prompt="Create a video from the following: "+prompt
    )

    video_url = response['data']['url']
    myprint(f"Video URL: {video_url}")
    return video_url
