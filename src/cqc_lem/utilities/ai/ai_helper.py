import base64
import os
import random
import time

import openai
import replicate
from cqc_lem import assets_dir
from cqc_lem.utilities.ai.client import client
from cqc_lem.utilities.ai.tools import search_recent_news
from cqc_lem.utilities.linkedin.profile import LinkedInProfile
from cqc_lem.utilities.logger import myprint
from cqc_lem.utilities.utils import create_folder_if_not_exists, save_video_url_to_dir
from dotenv import load_dotenv
from runwayml import RunwayML

# Load .env file
load_dotenv()


# Retrieve OpenAI API key from environment variables
# openai.api_key = os.getenv("OPENAI_API_KEY") #<---- This is done be default


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


def generate_ai_response(post_content, profile: LinkedInProfile, post_img_url=None, post_comment: str = None):
    image_attached = "(image attached)" if post_img_url else ""
    user_comment = f"\n\nRespond to this Comment Directly: <comment>{post_comment}</comment>\n\nYou are responding as the author of the LinkedIn Content. Keep your response short and sweet without using any hashtags.\n\n" if post_comment else ""

    prompt = (f"""Please give me a comment in response to the following LinkedIn Content as the following LinkedIn User,"
              
                LinkedIn User Profile:\n\n{profile.model_dump_json()}\n\n"
              
                LinkedIn Content{image_attached}: <content>'{post_content}'</content>
                
                {user_comment}

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

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[system_prompt, user_message],  # System prompt + current user prompt
        temperature=round(random.uniform(0.4, 0.6), 2),  # Rand temp between .5 and .7

        # Balances coherent response generation with some degree of creative variation.
        top_p=round(random.uniform(0.8, 0.9), 2),
        # Reduces repetition in common responses.
        frequency_penalty=round(random.uniform(0.2, 0.4), 2),
        # Supports fresh responses aligned with user-specific tone.
        presence_penalty=round(random.uniform(0.3, 0.5), 2),

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


def get_industries_of_profile_from_ai(linked_in_profile: LinkedInProfile, industry_count: int = 3):
    """Generate industries based on the LinkedIn user profile."""

    # Use json to output to string
    linked_in_profile_json = linked_in_profile.model_dump_json()
    prompt = f"""Please tell me what {industry_count} industry(s) that most align with the following LinkedIn Profile's career and personal interest.
             A short comma seperated list is all that is needed.
             
             Linked Profile: {linked_in_profile_json}

"""

    # myprint(f"Prompt: {prompt}")

    content = [{"type": "text", "text": prompt}]

    # System prompt to be included in every request
    system_prompt = {
        "role": "system",
        "content": f"""Act like a professional career analyst specializing in LinkedIn profile analysis. 
        You have 15 years of experience identifying professional interests, career trajectories, and industry affiliations based on online profiles. 
        Your expertise includes assessing user activities, language use, endorsements, skills, and affiliations to infer professional domains and preferences.  

        **Objective:** Analyze the provided LinkedIn profile to:  
        1. Identify the industries in which the user primarily works.  
        2. Deduce the industries or domains the user appears to enjoy most.  
        3. Provide reasoning based on profile content, including skills, endorsements, activity, and affiliations.
        
        **Steps to Complete the Task:**  
        1. **Examine Profile Details:**  
           - Review the professional headline, experience section, skills, endorsements, and any listed certifications.  
           - Pay attention to recurring industry-specific terminology or roles.  
        
        2. **Analyze Engagement Patterns:**  
           - Review activities such as posts, comments, or articles for language indicating passion or enjoyment.  
           - Highlight topics or industries the user engages with most frequently.  
        
        3. **Cross-reference Skills and Interests:**  
           - Match listed skills with industries where these skills are most relevant.  
           - Evaluate any mentions of hobbies, voluntary roles, or side projects for clues to preferred domains.  
        
        4. **Make Inferences:**  
           - Categorize the user's professional involvement into industries based on job history and skills.  
           - Suggest industries of enjoyment by interpreting tone, enthusiasm in engagement, or diverse activities.  
        
        5. **Present Results:**  
           - List the industries with brief explanations for each based on evidence from the profile.  
           - Use bullet points to clearly separate industries worked in versus enjoyed.  
        
        #### **Example Output:**
        
        Technology, Web Development, Real Estate
    
        ---
        
        ### Your Final Steps: 
        - Take a deep breath and work on this problem step-by-step.
        - Do not surround your response in quotes or added any additional system text. 
        - Do not share your thoughts nor show your work. 
        - Only respond with one final response.


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

def get_ai_linked_post_refinement(original_message: str, character_limit: int = 3000):
    character_limit_string = (f"""\nThe refined LinkedIn Post needs to be less than or equal to {character_limit} characters including white spaces and punctuations. You may use symbols, abbreviations, and other and short-hand.
                               Ideally, Posts between 1,300 and 2,000 characters tend to perform well by providing enough detail while maintaining readability.\n\n""") if character_limit > 0 else ""

    prompt = f"""Please review and refine the following LinkedIn Post Draft. {character_limit_string} LinkedIn Post Draft: {original_message}
                """

    # myprint(f"Prompt: {prompt}")

    content = [{"type": "text", "text": prompt}]

    # System prompt to be included in every request
    system_prompt = {
        "role": "system",
        "content": f"""Act like a professional editor with expertise in business communication, particularly for LinkedIn posts.**  

        You have over 15 years of experience helping professionals craft polished, engaging, and impactful LinkedIn content. 
        Your expertise ensures that messages maintain proper grammar, clarity, and professionalism while also being compelling and easy to read.  
        
        Your task is to take a provided draft LinkedIn post and refine it into a final, ready-to-publish version. 
        The primary focus is on proper capitalization for sentences, pronouns, and abbreviations, but you should also apply a full editorial review to enhance readability, impact, and professionalism.  
        
        Your review process includes:  
        
        1. **Correct capitalization and formatting**  
           - Ensure that all sentences start with capital letters.  
           - Capitalize proper nouns, job titles (when used formally), and abbreviations correctly.  
           - Maintain consistency in formatting for emphasis (e.g., bullet points when appropriate).  
        
        2. **Enhance clarity and coherence**  
           - Ensure a smooth flow between sentences and paragraphs.  
           - Eliminate redundant words or phrases while preserving the original intent.  
           - Rewrite awkward or overly complex sentences for readability.  
        
        3. **Refine for engagement and impact**  
           - Optimize sentence structure to maintain a professional yet approachable tone.  
           - Ensure the opening is engaging to hook the audience and the closing provides a strong takeaway.  
           - Maintain an authentic voice suited for LinkedIn.  
        
        4. **Ensure grammatical accuracy and professionalism**  
           - Correct any typos, punctuation errors, or inconsistencies.  
           - Adapt the tone to be confident, clear, and aligned with business communication best practices.  
        
        All responses should be **finalized drafts** ready for publishing. Do not ask for additional input—refine the given draft based on available information.  
        
        Provide only the **edited version of the LinkedIn post** without explanations or notes.  
        
        ---  
        
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

        # Emphasizes succinct, professional outputs over creative variance.
        top_p=round(random.uniform(0.75, 0.85), 2),
        # Discourages redundancy in phrase selection.
        frequency_penalty=round(random.uniform(0.4, 0.6), 2),
        # Ensures refined and novel phrasings without losing coherence.
        presence_penalty=round(random.uniform(0.4, 0.6), 2),

        # temperature=0.3,  # Adjust this parameter as per your needs
        # max_tokens=150  # Set token limit as required
    )

    # Extract and return the model's response
    comment = response.choices[0].message.content.strip()
    return comment

def get_ai_message_refinement(original_message: str, character_limit: int = 300):
    character_limit_string = f"\nThe refined message needs to be less than or equal to {character_limit} characters including white spaces and punctuations. You may use symbols, abbreviations, and other and short-hand\n\n " if character_limit > 0 else ""

    prompt = f"""Please review and refine the following message. {character_limit_string} Message: {original_message}
            """

    # myprint(f"Prompt: {prompt}")

    content = [{"type": "text", "text": prompt}]

    # System prompt to be included in every request
    system_prompt = {
        "role": "system",
        "content": f"""Act like a professional editor with expertise in communication for business professionals, particularly on platforms like LinkedIn. 
            You have helped clients refine and streamline their messaging for more than 15 years, ensuring clarity, professionalism, and engagement.
    
            Your task is to review a provided message. The goal is to ensure the message makes sense, reads smoothly, and presents key information in a clear, concise, and professional manner. 
            Additionally, modify any titles, phrases, or sections that seem overly long, awkward, or redundant. 
            Your revisions should maintain the original intent while improving readability and impact.
            
            The review process includes:
            1. Check for clarity and coherence: Ensure the message has a logical flow and that each sentence connects smoothly to the next. Eliminate or revise any confusing or ambiguous phrases.
            2. Refine long titles and sections: Shorten overly detailed sections, such as professional titles, while preserving their key points. Ensure these parts are clear but not excessive.
            3. Improve engagement: The message should feel personalized and engaging. Identify opportunities to make the message more concise and approachable, particularly in the introduction and closing.
            4. Polish for professionalism: Ensure a professional tone throughout, appropriate for business communication.
            
            All your responses will be used as final drafts by the user. Thus you may not ask for additional information. Use whatever information you currently have to refine the message.
            
            A final direct refined response without a subject line is all that is needed. 
            
            ---
            
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

        # Emphasizes succinct, professional outputs over creative variance.
        top_p=round(random.uniform(0.75, 0.85), 2),
        # Discourages redundancy in phrase selection.
        frequency_penalty=round(random.uniform(0.4, 0.6), 2),
        # Ensures refined and novel phrasings without losing coherence.
        presence_penalty=round(random.uniform(0.4, 0.6), 2),

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
                This video should appeal to users in the {buyer_stage} buyer stage, aiming to quickly capture attention with a clear, memorable introduction. 
                Use a 1:1 aspect ratio and keep the length to 30 seconds. 
                Make the tone approachable and professional, with the visual style matching any brand cues present in the profile data. 
                End with a subtle call to action that encourages viewers to explore further.
                
                """,
               f"""Generate a 45-second LinkedIn explainer video script highlighting the unique strengths and offerings of the following LinkedIn Profile for an audience in the {buyer_stage} buyer stage.
               The script should present three key features or advantages that demonstrate why this profile or brand stands out as a valuable solution. 
               Use a 16:9 aspect ratio with a clean, professional design, and ensure pacing is steady enough to allow viewers to grasp each point. 
               Conclude with a call to action, inviting viewers to connect, learn more, or engage further on LinkedIn.
                
                """,

               f"""Design a compelling video script for LinkedIn that solidifies the following LinkedIn Profile as the top choice for viewers in the {buyer_stage} buyer stage. 
               Focus on driving conversions by presenting clear reasons why this profile or brand is a trustworthy choice, with emphasis on relevant accomplishments, client testimonials, or standout capabilities. 
               The video should run for about 60 seconds in a 16:9 format, with a polished, confidence-inspiring visual style. 
               End with a strong call to action encouraging immediate engagement, such as scheduling a demo or visiting the profile’s website.
                
                """,
               ]

    prompt = random.choice(prompts)

    myprint(f"Pre-Prompt: {prompt}")

    # Add the Linked JSon profile to end of prompt
    prompt += f"\n ### LinkedIn Profile: {linked_in_profile_json}"

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
        # response_format={"type": "json_object"},
    )

    # Extract and return the model's response
    final_prompt = response.choices[0].message.content.strip()
    video_url = create_video_from_prompt(final_prompt)
    return video_url


def summarize_recent_activity(recent_activity_profile: LinkedInProfile, main_profile: LinkedInProfile):
    # If recent_activity_profile.recent_activities is None or length is 0, return None
    if not recent_activity_profile.recent_activities or len(recent_activity_profile.recent_activities) == 0:
        return None

    recent_activity_profile_sting = ''.join([f"{i + 1}. {activity.text} - [{activity.link}]\n" for i, activity in
                                             enumerate(recent_activity_profile.recent_activities)])

    # Clone the main profile and remove recent activities to reduce confusion form AI
    main_profile = main_profile.model_copy(deep=True)
    main_profile.recent_activities = []

    main_profile_json = main_profile.model_dump_json()
    prompt = f"""We are analyzing the interests of one LinkedIn user (main_profile) and want to help them craft a personalized response to another LinkedIn user (second_profile) based on the second user's recent activities. 
    Analyze the main_profile’s interests and select the most relevant activity from second_profile’s list of recent activities. 
    Then, create a response as if it’s from main_profile to second_profile, mentioning the most relevant recent activity and providing a professional comment.

    ### Main Profile (User 1):
    {main_profile_json}
    
    ### Second Profile (User 2):
    Name: {recent_activity_profile.full_name}
    Recent Activities:<activities>{recent_activity_profile_sting}</activities>
    
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


def create_video_from_prompt(prompt: str):
    response = openai.Video.create(
        model="video-davinci-003",
        prompt="Create a video from the following: " + prompt
    )

    video_url = response['data']['url']
    myprint(f"Video URL: {video_url}")
    return video_url


def get_thought_leadership_post_from_ai(linked_user_profile: LinkedInProfile, buyer_stage: str):
    """
        Generate a thought leadership post based on user's expertise and industry.
        Uses the user's profile (e.g., job title, industry) and intended buyer_stage to form an insightful post.
    """

    trends = get_industry_trend_analysis_based_on_user_profile(linked_user_profile, limit_to=10)
    industry = trends.get("industry", "Technology")
    analysis = trends.get("analysis", "")

    print(
        f'Generating Thought Leadership AI Response for {buyer_stage} buyer stage about the {industry} industry.\n\nAnalysis: {analysis} ')

    # Use json to output to string
    linked_in_profile_json = linked_user_profile.model_dump_json()

    prompt = f"""Please create a thought leadership post for me based on my LinkedIn Profile information and the current trends in the {industry} industry.

        Craft the post to appeal to readers who are currently in the {buyer_stage} buyer stage of their journey.
        
        # Buyer Stages:
        - Awareness: Introduce key industry challenges and trends that my expertise addresses.
        - Consideration: Highlight unique solutions, strategies, or frameworks that showcase my approach to common industry problems.
        - Decision: Provide insight into how my experience and skills make me a strong partner for organizations seeking expertise in relevant industries or skills areas.
        
        Conclude with an engaging call to action that encourages readers at the specified stage to connect or learn more.
        
        {get_viral_linked_post_prompt_suffix()}
        
        """

    # Add the Linked JSON profile to end of prompt
    prompt += f"\n ### LinkedIn Profile: {linked_in_profile_json}\n\n"

    # Add the industry trend analysis to the prompt
    prompt += f"\n ### Current {industry} Trends: <analysis>{analysis}</analysis>"

    content = [{"type": "text", "text": prompt}]

    # System prompt to be included in every request
    system_prompt = {
        "role": "system",
        "content": f"""Act like an experienced thought leadership content creator. You have years of expertise crafting high-impact insights tailored to an executive audience across various industries. Your goal is to develop a compelling, informative, and engaging thought leadership post that reflects the user’s unique perspective and experience. Follow the steps carefully to ensure the content is insightful and relevant.

        ### Objective
        Create a thought leadership post based on the user’s expertise and current industry trends. This post should:
        - Position the user as an authority in their field.
        - Offer unique insights or innovative solutions to challenges in their industry.
        - Encourage engagement by inspiring readers to reflect, comment, or share.
        
        ### Instructions
        1. **Analyze User Profile**:  
           Use the following details provided by the user:
           - Job Title (e.g., “Chief Technology Officer,” “Senior Marketing Strategist”)
           - Industry (e.g., “Healthcare Technology,” “Financial Services,” “Renewable Energy”)
           - Years of Experience and Key Skills, if available.
        
        2. **Identify Key Industry Trends**:  
           Based on the user’s industry, identify one or two current challenges, emerging trends, or transformations affecting the field. For example, if the user is in Healthcare Technology, potential themes might include digital transformation in patient care or regulatory compliance with data privacy.
        
        3. **Develop Core Insight**:  
           Draw from the user's job title and experience to present an insight or perspective that:
           - Tackles a common pain point or goal in the user’s industry.
           - Reflects forward-thinking or innovative approaches.
           - Incorporates specific, actionable advice when possible.
        
        4. **Create Engaging Introduction**:  
           Start the post with a hook to capture reader interest, such as:
           - A bold statement, question, or statistic that underscores the importance of the issue.
           - A relatable scenario in which many readers in the field might find themselves.
        
        5. **Expand with Depth and Expertise**:  
           In the main content, build upon the user’s insight with examples, strategies, or industry-specific approaches. Use phrases like:
           - “In my experience as a [Job Title]…”
           - “One of the biggest challenges in [Industry] today is…”
           - “A strategy I’ve found effective involves…”
        
        6. **Close with a Call to Action**:  
           End with a thought-provoking question or prompt that encourages engagement, such as:
           - “How is your organization addressing [trend or challenge]?”
           - “What strategies have you found successful in navigating [relevant issue]?”
        
        **Final Reminder**: Focus on clarity, avoid jargon, and write in a tone that is both authoritative and accessible.
        
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
        temperature=round(random.uniform(0.5, 0.7), 2),  # Rand temp between .5 and .7

        top_p=round(random.uniform(0.85, 0.95), 2),
        # Encourages diversity in word choice while focusing on high-probability responses for coherent professional content.
        frequency_penalty=round(random.uniform(0.3, 0.5), 2),
        # Minimizes repetitive patterns to ensure unique and varied phrasing.
        presence_penalty=round(random.uniform(0.4, 0.6), 2),
        # Boosts exploration of new ideas while keeping content relevant to the LinkedIn tone.

        # max_tokens=150  # Set token limit as required
        # response_format={"type": "json_object"},
    )

    # Extract and return the model's response
    content = response.choices[0].message.content.strip()
    return content


def get_industry_trend_analysis_based_on_user_profile(linked_in_profile: LinkedInProfile, limit_to=None,
                                                      randomize=True):
    my_industries = get_industries_of_profile_from_ai(linked_in_profile, 3)
    myprint(f"Likely Industries: {my_industries}")

    # Convert the industries into a list by splitting on comma
    my_industries_list = my_industries.split(', ')

    # Get one of the industries by random choice
    industry = random.choice(my_industries_list)

    myprint(f"Chosen Industry: {industry}")

    # Get Google News articles about that industry
    articles_dict = search_recent_news(industry, 7)

    articles = articles_dict.get('articles', [])

    myprint(f"Articles Found: {len(articles)}")

    if randomize:
        random.shuffle(articles)
        myprint(f"Articles Shuffled")

    if limit_to and len(articles) > limit_to:
        articles = articles[:limit_to]
        myprint(f"Limited to {limit_to} articles")

    myprint(f"Articles: {articles}")

    # Get the trend analysis of the industry
    trend_analysis = get_industry_trend_from_ai(industry, articles)

    return {
        'industry': industry.strip(),
        'analysis': trend_analysis
    }


def get_industry_news_post_from_ai(linked_user_profile: LinkedInProfile, buyer_stage: str):
    """
       Generate a post sharing industry news based on the LinkedIn user's profile and the intended buyer stage, along with the user's commentary.
    """

    trends = get_industry_trend_analysis_based_on_user_profile(linked_user_profile, limit_to=3)
    industry = trends.get("industry", "Technology")
    analysis = trends.get("analysis", "")

    # Use json to output to string
    linked_in_profile_json = linked_user_profile.model_dump_json()

    prompt = f"""Please create a post sharing recent {industry} industry news based on my LinkedIn Profile information provided below. 
    Tailor the post to readers in the {buyer_stage} buyer stage of their journey and include my own commentary to add perspective.
            
    # Buyer Stages to Consider:
    - Awareness: Introduce the news topic with broad insights on its relevance to the industry.
    - Consideration: Frame the topic in a way that helps readers think strategically about addressing this development.
    - Decision: Emphasize the importance of expert insights and how my expertise can be valuable in navigating this trend.
    
    """

    # Add the Linked JSON profile to end of prompt
    prompt += f"\n ### LinkedIn Profile: {linked_in_profile_json}"

    # Add the industry trend analysis to the prompt
    prompt += f"\n ### Current {industry} Trends: <analysis>{analysis}</analysis>"

    prompt += f"""\n\n
    --- 
    \n
    Make the post insightful and end with a question or prompt that invites engagement from readers.

    {get_viral_linked_post_prompt_suffix()}

    """

    content = [{"type": "text", "text": prompt}]

    # System prompt to be included in every request
    system_prompt = {
        "role": "system",
        "content": f"""Act like a seasoned industry analyst and content strategist. You specialize in creating timely, relevant posts that share current industry news while showcasing the user's unique insights and expertise. Your goal is to craft a post based on trending topics or news in the user's industry, as inferred from their LinkedIn profile. Tailor the post to align with the buyer’s current stage in their journey—whether they are at the Awareness, Consideration, or Decision stage.
 
        ### Instructions:
        1. **Analyze the User’s Profile**:  
           Use information about the user’s role, industry, and expertise from their LinkedIn profile.
         
        2. **Identify Relevant Industry News**:  
           Identify a recent trend or piece of news in the user’s industry. Ensure the topic is significant, relevant, and likely to catch the attention of readers in the intended buyer stage.
         
        3. **Compose the Post**:
            - **For Awareness Stage**: Introduce the news in a way that highlights broad industry implications, focusing on why this development matters and its potential impact on the field. Example: “With recent changes in [industry], we’re seeing a shift toward…”
            - **For Consideration Stage**: Provide context on the topic’s importance and suggest how readers might think strategically about addressing the issue. Example: “As organizations face [issue], it’s crucial to consider approaches like…”
            - **For Decision Stage**: Focus on the practical impact of this news for decision-makers and highlight the user's expertise or offerings as a valuable resource. Example: “Given this development, partnering with an expert in [user’s specialty] can ensure…”
         
        4. **Add User Commentary**:  
           Write a thoughtful commentary that reflects the user’s experience and perspective. Use phrases like:
           - “In my experience as a [Job Title]…”
           - “One key takeaway I see here is…”
         
        5. **Close with Engagement**:  
           Encourage readers to engage by asking a relevant question or prompting them to share their own experiences.
         
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
        temperature=round(random.uniform(0.3, 0.5), 2),  # Rand temp between .3 and .5

        top_p=round(random.uniform(0.8, 0.9), 2),
        # Ensures focus on high-quality, relevant insights while allowing some variation in tone.
        frequency_penalty=round(random.uniform(0.2, 0.4), 2),
        # Helps maintain consistency while reducing overuse of standard expressions.
        presence_penalty=round(random.uniform(0.3, 0.5), 2),  # Allows new perspectives and commentary to emerge.

        # max_tokens=150  # Set token limit as required
        # response_format={"type": "json_object"},
    )

    # Extract and return the model's response
    content = response.choices[0].message.content.strip()
    return content


def get_industry_trend_from_ai(industry: str, articles: list):
    """Generate industry trend based on the LinkedIn user profile."""

    articles_text = "\n".join([
        f"- {article['title']} ({article['date']}): {article['link']}"
        for article in articles
    ])

    prompt = (
            f"Here are recent news articles related to the {industry} industry:\n\n"
            f"{articles_text}\n\n" +
            "Analyze these articles and provide:\n" +
            "- A list of key topics or keywords that are trending in this industry.\n" +
            "- Categories these articles belong to (e.g., Innovation, Finance, Policy).\n" +
            "- A Summary of the industry and suggestions for further exploration based on the news trends."
    )

    # myprint(f"Prompt: {prompt}")

    content = [{"type": "text", "text": prompt}]

    # System prompt to be included in every request
    system_prompt = {
        "role": "system",
        "content": f"""Act like a professional market analyst with over 15 years of experience in identifying industry trends and providing actionable insights. Your role is to analyze and interpret data from news articles to uncover patterns, emerging trends, and key industry dynamics.*

        When analyzing news articles:
        
        1. **Identify Trends:** Extract and summarize key industry trends, focusing on the specific sectors or industries mentioned in the articles.
        2. **Provide Context:** Offer detailed explanations of the factors driving these trends, referencing specific information from the articles provided.
        3. **Highlight Opportunities and Risks:** Identify opportunities and risks for businesses or stakeholders associated with these trends.
        4. **Synthesize Data:** If multiple articles are provided, synthesize their content to create a cohesive overview of the industry landscape.
        5. **Support with Evidence:** Base all analysis on the information provided in the articles. Clearly cite data or events from the articles to support your insights.
        
        Your outputs should be structured as follows:
        
        1. **Summary of Trends:** List the major industry trends identified.
        2. **Driving Factors:** Provide an analysis of what is causing these trends.
        3. **Opportunities and Risks:** Detail the potential impacts on businesses and stakeholders, including both positive and negative outcomes.
        4. **Recommendations:** Suggest strategic actions or considerations for stakeholders to adapt or respond effectively.
        5. **References:** Include references to specific articles and sections to validate your findings.

        ### Your Final Steps: 
        - Take a deep breath and work on this problem step-by-step.
        - Do not surround your response in quotes or added any additional system text. 
        - Do not share your thoughts nor show your work. 
        - Only respond with one final response.

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

        temperature=round(random.uniform(0.6, 0.8), 2),  # Rand temp between .6 and .8

        # promoting nuanced and diverse analyses.
        top_p=round(random.uniform(0.5, 0.7), 2),

        # Ensuring unique phrasing and varied insights across outputs.
        frequency_penalty=round(random.uniform(0.5, 0.7), 2),

        # Encourages exploration of new ideas while maintaining relevance to the content of the provided articles.
        presence_penalty=round(random.uniform(0.5, 0.7), 2),

        # max_tokens=150  # Set token limit as required
    )

    # Extract and return the model's response
    comment = response.choices[0].message.content.strip()
    return comment


def get_personal_story_post_from_ai(linked_user_profile: LinkedInProfile, stage: str):
    """
    Generate a post sharing a personal or professional story, based on the user's profile.
    """
    # Pull from the user's recent milestones, achievements, or challenges
    # Example content: "Reflecting on my journey as a [job title], I’ve learned that..."

    # Use json to output to string
    linked_in_profile_json = linked_user_profile.model_dump_json()

    prompt = f"""Please create a story-based post for me, reflecting on a personal or professional milestone, achievement, or challenge, using the information from my LinkedIn Profile provided below. 
    Tailor the story to connect with readers in the {stage} buyer stage of their journey. 
    Do not repeat content that I have already shared in my recent activity. 
    Do your best to relate the story to the current industry trends if possible.
    
    # Buyer Stages to Consider:
    - Awareness: Share a story that introduces me as a thoughtful leader, highlighting a key career insight or turning point.
    - Consideration: Emphasize lessons learned from a specific challenge or achievement, showing how my experience can guide or inspire similar efforts.
    - Decision: Position my expertise as a valuable resource for those facing similar challenges, demonstrating the depth of my skills and experience.
    
    """

    # Add the Linked JSON profile to end of prompt
    prompt += f"\n ### LinkedIn Profile: {linked_in_profile_json}"

    trends = get_industry_trend_analysis_based_on_user_profile(linked_user_profile, limit_to=5)
    industry = trends.get("industry", "Technology")
    analysis = trends.get("analysis", "")

    # Add the industry trend analysis to the prompt
    prompt += f"\n ### Current {industry} Trends: <analysis>{analysis}</analysis>"

    prompt += f"""\n\n
        --- 
        \n
        Conclude with an engaging question or prompt that encourages readers to reflect on similar experiences.

        {get_viral_linked_post_prompt_suffix()}

        """

    content = [{"type": "text", "text": prompt}]

    # System prompt to be included in every request
    system_prompt = {
        "role": "system",
        "content": f"""Act like a professional storyteller and content strategist. Your goal is to create a meaningful post that shares a personal or professional story from the user’s career journey, highlighting key milestones, achievements, or challenges. Craft a narrative that resonates with readers, giving them insights into the user’s experiences and growth within their field.
 
        ### Instructions:
        1. **Analyze the User’s Profile**:  
           Use information provided from the user’s LinkedIn profile, such as job title, years of experience, industry, key skills, recent achievements, or challenges.
         
        2. **Identify a Story Theme**:  
           Select a relevant theme for the story, based on milestones or lessons learned in the user’s career. Consider:
            - **Milestones**: A promotion, award, or significant project completion.
            - **Achievements**: Professional accomplishments, certifications, or goals reached.
            - **Challenges**: Professional hurdles, difficult projects, or industry shifts the user had to navigate.
         
        3. **Craft the Story**:
            - Begin with a relatable opening, such as: “Reflecting on my journey as a [job title]…” or “One of the most challenging moments in my career came when…”
            - Describe the situation briefly but vividly, focusing on what the user faced and how they approached it.
            - Include key learnings or insights that readers in the user’s industry might find valuable or inspiring.
         
        4. **Add a Personal Touch**:  
           Include the user’s reflections on how this experience shaped them professionally or personally. Use phrases like:
           - “This experience taught me that…”
           - “One key takeaway for me was…”
         
        5. **Close with a Call to Engage**:  
           Encourage readers to reflect on their own journeys by ending with a question or prompt, such as:
           - “What experiences have shaped your professional growth?”
           - “I’d love to hear how others in [industry] have handled similar challenges.”
         
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
        temperature=round(random.uniform(0.6, 0.8), 2),  # Rand temp between .6 and .8

        top_p=round(random.uniform(0.75, 0.85), 2),
        # Prioritizes more creative storytelling approaches for personal anecdotes.
        frequency_penalty=round(random.uniform(0.4, 0.6), 2),
        # Reduces redundancy in narrative details to make the story unique.
        presence_penalty=round(random.uniform(0.6, 0.8), 2),
        # Encourages creative content generation that resonates emotionally.

        # max_tokens=150  # Set token limit as required
        # response_format={"type": "json_object"},
    )

    # Extract and return the model's response
    content = response.choices[0].message.content.strip()
    return content


def generate_engagement_prompt_post(linked_user_profile: LinkedInProfile, stage: str):
    """
    Generate a question or prompt that encourages engagement from followers.
    """
    # Create a question or engagement prompt related to the user's field
    # Example content: "As a [job title], I’m curious to hear how others are handling [challenge]..."

    # Use json to output to string
    linked_in_profile_json = linked_user_profile.model_dump_json()

    prompt = f"""Please generate a question or prompt to encourage engagement from my followers based on the information in my LinkedIn Profile below and related it to current industry trends. 
    Tailor the question to resonate with readers in the {stage} buyer stage of their journey.

    # Buyer Stages to Consider:
    - Awareness: Ask a thought-provoking question to spark curiosity about industry challenges or trends.
    - Consideration: Pose a question that invites followers to share strategies or insights on common challenges.
    - Decision: Encourage a deeper conversation around specific pain points or decision-making criteria, drawing on my expertise.
    
    """

    # Add the Linked JSON profile to end of prompt
    prompt += f"\n ### LinkedIn Profile: {linked_in_profile_json}"

    trends = get_industry_trend_analysis_based_on_user_profile(linked_user_profile)
    industry = trends.get("industry", "Technology")
    analysis = trends.get("analysis", "")

    # Add the industry trend analysis to the prompt
    prompt += f"\n ### Current {industry} Trends: <analysis>{analysis}</analysis>"

    prompt += f"""\n\n
            --- 
            \n
            Make the question open-ended and relatable to create meaningful engagement.

            {get_viral_linked_post_prompt_suffix()}

            """

    content = [{"type": "text", "text": prompt}]

    # System prompt to be included in every request
    system_prompt = {
        "role": "system",
        "content": f"""Act like a social media engagement strategist with expertise in crafting questions that spark meaningful conversations among professionals. Your task is to generate an engaging question or prompt that encourages the user’s followers to share their insights, experiences, or thoughts on a relevant industry topic.
 
    ### Instructions:
    1. **Analyze the User’s Profile**:  
       Use information from the user’s LinkedIn profile, including their job title, industry, key skills, and recent professional topics or challenges.
     
    2. **Identify a Relevant Topic for Engagement**:  
       Select a topic relevant to the user’s field that aligns with current trends, challenges, or frequent discussions. Examples include:
       - **Emerging Trends**: Innovations, new technologies, or industry shifts.
       - **Challenges**: Common obstacles or pain points within the user’s role or industry.
       - **Best Practices**: Insights or advice on strategies or approaches in the user’s field.
     
    3. **Craft an Engaging Question or Prompt**:
        - Formulate a question or prompt that invites followers to share their own experiences or perspectives. Use phrases like:
          - “As a [job title] in [industry], I’m curious to hear…”
          - “How are others in [industry] addressing…?”
          - “What strategies have you found effective for…?”
        - Ensure the question is open-ended to encourage detailed responses rather than simple yes/no answers.
     
    4. **Make it Relatable**:  
       Use language that resonates with followers in the user’s industry or role. The question should feel authentic, reflecting the user’s voice and curiosity as an industry professional.
     
    5. **Close with a Call to Action**:  
       Prompt followers to respond directly by saying, for example:
       - “I’d love to hear your thoughts!”
       - “Share your experiences below!”
     
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
        temperature=round(random.uniform(0.6, 0.9), 2),  # Rand temp between .6 and .9

        top_p=round(random.uniform(0.7, 0.85), 2),  # Balances creativity and relevance in open-ended prompts.
        frequency_penalty=round(random.uniform(0.5, 0.7), 2),
        # Prevents repetitive patterns, especially in prompts or questions.
        presence_penalty=round(random.uniform(0.6, 0.7), 2),  # Promotes original and thought-provoking prompts.

        # max_tokens=150  # Set token limit as required
        # response_format={"type": "json_object"},
    )

    # Extract and return the model's response
    content = response.choices[0].message.content.strip()
    return content


def get_blog_summary_post_from_ai(blog_post_url: str, blog_post_content: str, linked_user_profile: LinkedInProfile,
                                  stage: str):
    """
    Generate a summary post for a blog article using the provide post url and post content from user to create interest using relevance to the provided LinkedIn Profile.
    """
    # create a LinkedIn-friendly summary

    # Use json to output to string
    linked_in_profile_json = linked_user_profile.model_dump_json()

    prompt = f"""Please generate a LinkedIn-friendly summary post for the blog article provided below. 
    Tailor the post to appeal to readers in the {stage} buyer stage of their journey, using my LinkedIn profile details to make the summary relevant to my role and industry.

    """

    # Add the Linked JSON profile to end of prompt
    prompt += f"\n ### LinkedIn Profile: {linked_in_profile_json}"

    prompt += f"""\n\n Buyer Stages to Consider:
    - Awareness: Summarize the article with broad insights into industry trends and challenges.
    - Consideration: Frame the post to highlight actionable strategies or best practices discussed in the article.
    - Decision: Emphasize the practical value of the insights for decision-makers and align the tone to demonstrate my expertise in the area.
    
    ### Blog Post URL: {blog_post_url}
    
    --- 
    
    ### Blog Post Content: <blog_content>{blog_post_content}</blog_content>
    
    ---
    
    Ensure the post is engaging, includes a clear call to action, and ends with a link inviting readers to read the full article.
    
    {get_viral_linked_post_prompt_suffix()}
    
    """

    content = [{"type": "text", "text": prompt}]

    # System prompt to be included in every request
    system_prompt = {
        "role": "system",
        "content": f"""Act as an informed LinkedIn content strategist with expertise in the user’s industry. You will be provided with a blog article URL, the article content, and LinkedIn profile information from the user. Create an engaging LinkedIn-friendly summary post that highlights the relevance of the article to the user’s industry and expertise.
 
        ### Instructions:
        1. **Summarize the Main Idea**:  
           Begin with a clear, concise summary of the article's main message or insight, focusing on how it relates to the user’s industry. Avoid using complex terminology to keep the content accessible and engaging.
         
        2. **Personalize with Relatable Elements**:  
           Incorporate a relatable comment or anecdote that connects the article’s content to the user’s role or experience. Use phrases like:
           - “As a [Job Title], I often see…”
           - “In the world of [Industry], this trend is particularly relevant because…”
         
        3. **Add Engaging Elements**:  
           Include a question, a call to action, or a compelling statistic from the article to prompt followers to engage with the post. You can use emojis (such as 📊, 🌟, or ❓) to add personality, but only if it aligns with the user’s tone and industry norms.
         
        4. **Incorporate Relevant Hashtags**:  
           Use up to 5 relevant hashtags, based on the article’s subject and the user’s industry. Suggested tags may include broader industry terms (#Innovation, #AI, #Leadership) and niche terms directly related to the content.
         
        5. **Tone Adaptation**:  
           Adjust the tone to match the article’s content and the LinkedIn user’s profile. Whether the tone is formal, casual, motivational, or insightful, ensure it feels authentic to the user's voice.
         
        6. **Encourage Readers to Read the Full Article**:  
           Conclude with an invitation for readers to explore the topic further by including the article link with a phrase like:
           - “Read the full article here: [insert URL]”
           - “Explore more insights in the full piece: [insert URL]”
        
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
        temperature=round(random.uniform(0.5, 0.7), 2),  # Rand temp between .5 and .7

        # Focuses on concise and accurate summaries while retaining flexibility for phrasing.
        top_p=round(random.uniform(0.8, 0.9), 2),
        # Ensures variety in how summaries are structured.
        frequency_penalty=round(random.uniform(0.3, 0.5), 2),
        # Encourages fresh perspectives in the summarization process.
        presence_penalty=round(random.uniform(0.3, 0.5), 2),

        # max_tokens=150  # Set token limit as required
        # response_format={"type": "json_object"},
    )

    # Extract and return the model's response
    content = response.choices[0].message.content.strip()
    return content


def get_website_content_post_from_ai(content: str, url: str, linked_user_profile: LinkedInProfile, stage: str):
    """
        Generate a summary post for a blog article using the provide post url and post content from user to create interest using relevance to the provided LinkedIn Profile.
        """
    # create a LinkedIn-friendly summary

    # Use json to output to string
    linked_in_profile_json = linked_user_profile.model_dump_json()

    prompt = f"""Please generate a LinkedIn-friendly summary post for the website content provided below. 
        Tailor the post to appeal to readers in the {stage} buyer stage of their journey, using my LinkedIn profile details to make the summary relevant to my role and industry.

               """

    # Add the Linked JSON profile to end of prompt
    prompt += f"\n ### LinkedIn Profile: {linked_in_profile_json}"

    prompt += f"""---\n\n Buyer Stages to Consider:
        - Awareness: Summarize the website content with broad insights into industry trends and challenges.
        - Consideration: Frame the post to highlight actionable strategies or best practices discussed in the website content.
        - Decision: Emphasize the practical value of the insights for decision-makers and align the tone to demonstrate my expertise in the area.

        ### Website URL: {url}

        --- 

        ### Website Content: <website_content>{content}</<website_content>

        ---

        Ensure the post is engaging, includes a clear call to action, and ends with a link to the website url.
        
        {get_viral_linked_post_prompt_suffix()}
        """

    content = [{"type": "text", "text": prompt}]

    # System prompt to be included in every request
    system_prompt = {
        "role": "system",
        "content": f"""Act as an informed LinkedIn content strategist with expertise in the user’s industry. You will be provided with a website URL, the website content, and LinkedIn profile information from the user. 
        Create an engaging LinkedIn-friendly summary post that highlights the relevance of the website content to the user’s industry and expertise.

            ### Instructions:
            1. **Summarize the Main Idea**:  
               Begin with a clear, concise summary of the website content's main message or insight, focusing on how it relates to the user’s industry. Avoid using complex terminology to keep the content accessible and engaging.

            2. **Personalize with Relatable Elements**:  
               Incorporate a relatable comment or anecdote that connects the website’s content to the user’s role or experience. Use phrases like:
               - “As a [Job Title], I often see…”
               - “In the world of [Industry], this trend is particularly relevant because…”

            3. **Add Engaging Elements**:  
               Include a question, a call to action, or a compelling statistic from the website content to prompt followers to engage with the post. You can use emojis (such as 📊, 🌟, or ❓) to add personality, but only if it aligns with the user’s tone and industry norms.

            4. **Incorporate Relevant Hashtags**:  
               Use up to 5 relevant hashtags, based on the website content’s subject and the user’s industry. Suggested tags may include broader industry terms (#Innovation, #AI, #Leadership) and niche terms directly related to the content.

            5. **Tone Adaptation**:  
               Adjust the tone to match the website’s content and the LinkedIn user’s profile. Whether the tone is formal, casual, motivational, or insightful, ensure it feels authentic to the user's voice.

            6. **Encourage Readers to visit the website url**:  
               Conclude with an invitation for readers to explore further by including the website url link with a phrase like:
               - “Read the more from here: [insert URL]”
               - “Explore more here: [insert URL]”

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
        temperature=round(random.uniform(0.5, 0.7), 2),  # Rand temp between .5 and .7

        # Focuses on generating insightful and engaging website-related content.
        top_p=round(random.uniform(0.85, 0.95), 2),
        # Helps avoid overuse of common phrases while summarizing website content.
        frequency_penalty=round(random.uniform(0.3, 0.5), 2),
        # Encourages originality and exploration of unique aspects of website content.
        presence_penalty=round(random.uniform(0.4, 0.6), 2),

        # max_tokens=150  # Set token limit as required
        # response_format={"type": "json_object"},
    )

    # Extract and return the model's response
    content = response.choices[0].message.content.strip()
    return content


def get_viral_linked_post_prompt_suffix():
    return """After crafting your response, using the Viral Post Creation Framework detailed below, update your response to a viral post for LinkedIn readers.
    ---
    
    # Viral Post Creation Framework
    
    Must start with a hook from the Catch Hook Framework. Use the topic and pillar(s) from your original response as the focus. Write the post with each sentence being no more than ten words, ensuring clarity and impact in every line. Add a line space after each period to enhance readability. Include a call-to-action at the end, inviting engagement or reflection from my audience. The format should keep the message sharp, inviting readers to pause and engage with my content thoughtfully. End with 10 relevant hashtags to the post all on one line. Use relevant emoticons as bullet points when needed.
    
    I want you to critique your post according to the SUCKS framework. S: Is it specific? U: Is it unique, useful, and undeniable? C: Is it clear, curious, and conversational? K: Is it kept simple? S: Is it structured?
    If your answer is "no" to any of the the SUCKS frameworks questions fix the post so that the answer becomes "yes".
    
    ---
    
    # Catchy Hook Framework
    
    Act like an experienced social media expert with more than 20 years of experience in digital marketing, capturing people's attention and writing copy. I want you to write the perfect hook for my post.
    
    My post is missing a hook, which is the first 1-3 lines of the post. You will create its hook. You know well that the hook is 80% of the result of a post. It is essential for my job that my hook is perfect.
    
    I want you to generate 1 perfect hook. What’s a perfect hook? It’s creative. Outside the box. Eye-catching. It creates an emotion, a feeling. It makes people stop scrolling. It avoids jargon, fancy words, questions, and emojis at all costs. Good hooks are written as a normal sentence (avoid capital letters for every word). Some of the hooks are one-liners, some are three-liners (with line breaks). Switch between the two. Your hook must be perfect.
    
    Hooks are short sentences. Impactful. If the sentence is long, cut it in 2 and put a line break. Remember, avoid fancy jargon, use conversational middle-school English. Be as simple as possible. 
    
    ---
    
    ### Your Final Steps: 
    - Take a deep breath and work on this problem step-by-step.
    - Only provide the final response once it perfectly reflects the LinkedIn user’s style.
    - Do not surround your response in quotes or added any additional system text. 
    - Do not share your thoughts nor show your work. 
    - Only respond with one final Viral Post response.
    
    """


def get_dall_e_image_prompt_from_ai(post_content: str):
    """
       Generate a Dalle-3 image prompt from the provided post content
       """

    prompt = f"""Please generate a DALL-E-3 image prompt based on the following:
    
    Post: <content>{post_content}</content>
    
    """

    content = [{"type": "text", "text": prompt}]

    # System prompt to be included in every request
    system_prompt = {
        "role": "system",
        "content": f"""Act as an expert image generator and social media content strategist. 
        Your task is to analyze the provided LinkedIn post text and craft a detailed prompt for DALL-E 3 
        to create an image that visually encapsulates the post’s theme, message, and tone.

         ### Desired Image Characteristics:
        - **Clean and Aesthetic**: The image should not feel overcrowded but should clearly depict the content of the post.
        - **Professional and Polished**: The image should look modern and inspiring, suitable for LinkedIn.
        - **Balanced**: Avoid excessive elements; instead, highlight key themes in a visually appealing way.
        - **Focused**: The image should have its focal point specifically described
        
        ### Step-by-Step Instructions:
        1. **Analyze the Post Content:**
           - Identify the main topic, message, or story conveyed by the LinkedIn post.
           - Determine the tone (e.g., professional, motivational, celebratory, reflective) and emotional undertone.
           - Extract key visual elements or themes mentioned or implied in the text (e.g., "growth," "collaboration," "achievement," "innovation").
        
        2. **Specify Visual Representation:**
           - Translate the key message into a visual scene or concept. Describe the primary subject of the image (e.g., "a team brainstorming in a futuristic office" or "a rising sun symbolizing new beginnings").
           - Ensure the image aligns with LinkedIn's professional and motivational tone while reflecting the mood of the post.
        
        3. **Choose Art Style and Composition:**
           - Select an art style that matches the post’s tone: photorealistic, professional illustration, minimalistic, vibrant, or corporate-inspired.
           - Define the composition and perspective, such as close-up, wide-angle, or eye-level.
        
        4. **Detail the Setting, Colors, and Mood:**
           - Specify the setting (e.g., urban office, natural landscape, futuristic environment).
           - Suggest colors and lighting that enhance the mood (e.g., "warm golden light for optimism" or "sleek blue tones for professionalism").
        
        5. **Generate a Complete DALL-E Prompt:**
           - Combine all the above elements into a concise, richly detailed instruction for DALL-E. Ensure clarity, specificity, and imaginative detail.
           - Review the Desired Image Characteristics and make sure your prompt incorporates each aspect but does not directly state it in your generated response.
        
        ### Output Format:
        - **DALL-E Prompt:** A fully detailed and descriptive image-generation prompt.
        
        
        ---
        
        ### Your Final Steps: 
        - Take a deep breath and work on this problem step-by-step.
        - Do not surround your response in quotes or added any additional system text. 
        - Do not share your thoughts nor show your work. 
        - Only respond with one final response without the prefix "DALL-E Prompt:".
            
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
        temperature=round(random.uniform(0.4, 0.6), 2),
        # Ensure logical and structured prompts but allow some creativity for DALL-E descriptions. Slightly tighter control avoids over-creativity that might make outputs unfocused.

        # Focuses on high-probability tokens while leaving room for variation in descriptions.
        top_p=round(random.uniform(0.85, 0.95), 2),
        # Ensures the generation focuses on high-probability tokens while leaving room for variation in descriptions.
        frequency_penalty=round(random.uniform(0.5, 0.7), 2),
        # Ensures new elements are explored in prompts without becoming overly imaginative or irrelevant.
        presence_penalty=round(random.uniform(0.4, 0.6), 2),

        # max_tokens=150  # Set token limit as required
        # response_format={"type": "json_object"},
    )

    # Extract and return the model's response
    content = response.choices[0].message.content.strip()
    return content


def generate_dall_e_image_from_prompt(prompt: str, size: str = "1024x1024"):
    """
    Generate an image from the provided prompt using the DALL-E-3 model.
    """
    # Call the DALL-E-3 model to generate an image based on the prompt
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size=size,
        quality="hd",  # Standard or hd
        n=1,  # Only 1 allowed for Dalle-3
        # style="natural", #Style can be vivid or natural
        response_format='url'
    )

    if len(response.data) > 0:
        return response.data
    else:
        return response.data[0].url


def get_flux_image_prompt_from_ai(post_content: str):
    """
       Generate a Flux.1 image prompt from the provided post content
       """

    prompt = f"""Here’s a LinkedIn post: <post_content>{post_content}</post_content>.

    Analyze the post and, based on its themes, select a focal point or core message to emphasize. 
    Decide on a tone or style that creatively aligns with the post but think outside the box—incorporate unexpected interpretations, moods, or styles that give the visual concept a fresh and imaginative twist.
    
    Your response should include a single, detailed paragraph describing the image scene, style, and mood in a way that feels unique and specific to this post. 
    Each response to similar posts should offer a different perspective, approach, or creative take.

    """

    content = [{"type": "text", "text": prompt}]

    # System prompt to be included in every request
    system_prompt = {
        "role": "system",
        "content": f"""Act as a **world-class visual content creator and prompt engineer specializing in unique AI-generated imagery**. 
        Your task is to craft highly imaginative and detailed image descriptions that translate the essence of a LinkedIn post into extraordinary visuals. 
        The goal is to create visually distinct, outside-the-box concepts, ensuring variety and originality in every image prompt.  

        ### Step-by-Step Instructions:  
        
        1. **Analyze the Post:**
           - Identify the **core message** or theme of the post, capturing both explicit content and implied meanings.
           - Recognize the **tone**, **emotion**, and **key metaphors** conveyed in the post.  
           - Extract **unconventional angles or perspectives** to spark originality.  
        
        2. **Innovate the Scene:**
           - **Core Concept:** Pinpoint the central idea or subject that visually represents the post.
           - **Unexpected Creativity:** Go beyond obvious interpretations; add surreal, abstract, or symbolic elements to make the image unique.
           - **Style:** Choose a visual style, referencing artistic techniques, movements, or imaginative aesthetics (e.g., steampunk fusion, futuristic minimalism, or ethereal dreamscapes).  
           - **Composition:** Detail a balanced or intentionally dynamic arrangement, suggesting unique perspectives or camera angles.  
           - **Lighting:** Specify unique or experimental lighting (e.g., "luminous glow with starlight accents" or "moody fog with ethereal blue undertones").  
           - **Color Palette:** Recommend a striking or harmonious color scheme that amplifies the post’s mood and theme.
           - **Mood/Atmosphere:** Reflect the emotional resonance or underlying energy, infusing elements that evoke the intended response.
           - **Technical Elements:** Suggest additional visual or technical features that make the image exceptional (e.g., "wide lens for expansive depth" or "macro perspective on intricate details").  
        
        3. **Incorporate Symbolism and Details:**
           - Add unexpected metaphors, symbols, or creative background elements to enhance the narrative (e.g., "a phoenix rising in a city of glass" or "a vast tree with digital leaves representing ideas").  
        
        4. **Generate the Prompt:**
           - Combine all elements into a single, fluid, detailed paragraph with vibrant, evocative language.
           - **Avoid repetition, generic phrasing, or predictable descriptions.**
           - Ensure every prompt is designed to inspire unique, high-quality visuals.  
        
        ### Output Format:  
        - One paragraph, richly descriptive, without prefixes or additional instructions.  
        - No system text, introductions, or explanations—just the prompt.
   
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
        temperature=round(random.uniform(0.7, 1), 2),
        # Ensure logical and structured prompts but allow some creativity for Flux1 descriptions. Slightly tighter control avoids over-creativity that might make outputs unfocused.

        # Focuses on high-probability tokens while leaving room for variation in descriptions.
        top_p=round(random.uniform(0.85, 0.95), 2),
        # Ensures the generation focuses on high-probability tokens while leaving room for variation in descriptions.
        frequency_penalty=round(random.uniform(0.5, 0.7), 2),
        # Ensures new elements are explored in prompts without becoming overly imaginative or irrelevant.
        presence_penalty=round(random.uniform(0.4, 0.6), 2),

        # max_tokens=150  # Set token limit as required
        # response_format={"type": "json_object"},
    )

    # Extract and return the model's response
    content = response.choices[0].message.content.strip()
    return content


def get_flux_image_via_replicate(prompt: str, ref: str = "black-forest-labs/flux-dev"):
    output = replicate.run(
        ref,
        input={
            "prompt": prompt,
            "go_fast": True,
            "guidance": 3.5,
            "megapixels": "1",
            "num_outputs": 1,
            "aspect_ratio": "1:1",
            "output_format": "webp",
            "output_quality": 100,
            "prompt_strength": 0.8,
            "num_inference_steps": 28
        }
    )

    print("Flux Image via Replicate:")
    url = str(output[0])
    print(url)

    # Get the folder name of the parent of the url image
    url_image_folder = os.path.basename(os.path.dirname(url))

    # Save the file to assets/videos/replicate folder
    save_dir = os.path.join(assets_dir, "images", 'replicate', url_image_folder)

    print(f"Save to Folder: {save_dir}")

    create_folder_if_not_exists(save_dir)

    # Save the generated image
    video_file_path = save_video_url_to_dir(url, save_dir)

    return video_file_path


def generate_flux1_image_from_prompt(prompt: str):
    """
    video_file_path = get_flux_image_via_huggingface(prompt)

    # Move the video file path to the assets/gradio dir
    gradio_dir = os.path.join(assets_dir, "gradio")
    print(f"Gradio Dir: {gradio_dir}")
    create_folder_if_not_exists(gradio_dir)
    video_file_name = os.path.basename(video_file_path)
    # Get the parent folder name of the video file
    video_parent_dir = os.path.basename(os.path.dirname(video_file_path))
    print(f"Video Parent Folder: {video_parent_dir}")
    # Create dest folder
    file_dest_folder = os.path.join(gradio_dir, video_parent_dir)
    create_folder_if_not_exists(file_dest_folder)
    # Create final file destination
    video_file_dest = os.path.join(file_dest_folder, video_file_name)
    print(f"Video File Dest: {video_file_dest}")
    # Move the video file to the gradio dir
    shutil.move(video_file_path, video_file_dest)

    # TODO: Verify this final path and move

    return video_file_dest
    """

    return get_flux_image_via_replicate(prompt)


def get_runway_ml_video_prompt_from_ai(post_content: str, image_prompt: str):
    """
       Generate a RunwayMl video prompt from the provided post content and image prompt
       """

    prompt = f"""Please generate an video prompt based on the following:

    Post: <content>{post_content}</content>
    
    Image Prompt: <image_prompt>{image_prompt}</image_prompt>
    
    """

    content = [{"type": "text", "text": prompt}]

    # System prompt to be included in every request
    system_prompt = {
        "role": "system",
        "content": f"""Act like an expert cinematic prompt creator and a master of visual storytelling for Runway Gen-3 Alpha. You specialize in crafting detailed and precise video prompts that transform concepts into immersive 10-second videos. Your task is to create a video prompt based on a provided LinkedIn post and an accompanying image prompt. Leverage both inputs to ensure the final video aligns with the user’s vision and leaves a powerful impact. 

        You must strictly adhere to the following guidelines:
        
        ---
        
        #### **Step-by-Step Instructions:**
        
        1. **Analyze Inputs:**
           - **Post:** Extract key themes, tone, emotions, and significant keywords from the provided content.
           - **Image Prompt:** Identify the key visual elements, color schemes, subjects, and mood conveyed by the image.
           - Combine insights from both inputs to develop a unified concept for the video prompt.
        
        2. **Define the Video Objective:**
           - Ensure the video reflects the essence of the LinkedIn post while visually harmonizing with the style and elements of the image prompt.
           - Aim for a visually compelling 10-second scene with high emotional or thematic resonance.
        
        3. **Compose the Video Prompt:**
           - Use the following structured format to ensure clarity and detail:
             ```
             [camera movement]: [establishing scene]. [additional details]. [lighting and style].
             ```
           - Ensure every section of the prompt enhances the video's impact:
             - **Camera Movement:** Specify movements such as dynamic motion, FPV, slow motion, or close-up.
             - **Scene Description:** Vividly describe the environment, subject(s), and actions, ensuring they align with the LinkedIn post’s core message and the image’s visual tone.
             - **Lighting and Style:** Choose lighting styles (e.g., backlit, lens flare, diffused) and aesthetics (e.g., cinematic, moody, glitchcore) to complement the scene and reinforce the intended mood.
        
        4. **Leverage Keyword Options:**
           - Select and integrate relevant keywords from the following categories to enrich the prompt:
             - **Camera Styles:** Low angle, high angle, overhead, FPV, handheld, wide angle, close-up, macro cinematography, over-the-shoulder, tracking, establishing wide, 50mm lens, SnorriCam, realistic documentary, camcorder.
             - **Lighting Styles:** Diffused lighting, silhouette, lens flare, backlit, side-lit, [color] gel lighting, Venetian lighting.
             - **Movement Speeds:** Dynamic motion, slow motion, fast motion, timelapse.
             - **Movement Types:** Grows, emerges, explodes, ascends, undulates, warps, transforms, ripples, shatters, unfolds, vortex.
             - **Style and Aesthetic:** Moody, cinematic, iridescent, home video VHS, glitchcore.
             - **Text Styles:** Bold, graffiti, neon, varsity, embroidery.
        
        5. **Iterative Refinement:**
           - Ensure repeated or emphasized concepts reinforce key themes from both inputs.
           - Adjust camera movements, lighting, or aesthetic choices to refine adherence to the envisioned output.
        
        6. **Final Verification:**
           - Review the prompt for clarity, cohesiveness, and creativity.
           - Confirm all critical elements and keywords are present to achieve the intended cinematic effect.
        
        ---
        
        #### **Example Output:**
        
        **Inputs:**  
        - Post: <content>"Breaking barriers in the tech industry, we celebrate resilience and innovation."</content>  
        - Image Prompt: <image_prompt>A silhouette of a person standing on a glowing circuit board with a starry background.</image_prompt>  
        
        **Generated Video Prompt:**  
        "Dynamic FPV shot: The camera glides low over a glowing circuit board, revealing a silhouetted figure standing tall amidst a backdrop of sparkling stars. The figure's outline pulses with an iridescent glow, symbolizing energy and resilience. Lighting: Backlit with lens flare accents, cinematic tones. Style: Iridescent and futuristic."
        
        ---
        
        ### Your Final Steps: 
        - Take a deep breath and work on this problem step-by-step.
        - Do not surround your response in quotes or added any additional system text. 
        - Do not share your thoughts nor show your work. 
        - Do not need to say "Create" Just start describing it.
        - Your response must be less than 512 characters toal including white spaces and punctuation.
        - Only respond with one final response without the prefix "Generated Video Prompt:".

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
        temperature=round(random.uniform(0.5, 0.7), 2),  # Encourage creative but logical outputs
        top_p=round(random.uniform(0.8, 0.9), 2),  # Prioritize high-probability tokens
        frequency_penalty=round(random.uniform(0.6, 0.8), 2),  # Discourage repetition
        presence_penalty=round(random.uniform(0.5, 0.7), 2),  # Encourage exploration of new ideas

        # max_tokens=150  # Set token limit as required
        # response_format={"type": "json_object"},
    )

    # Extract and return the model's response
    content = response.choices[0].message.content.strip()
    return content


def create_runway_video(image_path: str, prompt: str):
    """Create a video using RunwayML"""

    runway_client = RunwayML()

    # encode image to base64
    with open(image_path, "rb") as f:
        base64_image = base64.b64encode(f.read()).decode("utf-8")

    # Create a new image-to-video task using the "gen3a_turbo" model
    task = runway_client.image_to_video.create(
        model='gen3a_turbo',
        # Point this at your own image file
        prompt_image=f"data:image/png;base64,{base64_image}",
        prompt_text=prompt,
    )
    task_id = task.id

    # Poll the task until it's complete
    time.sleep(10)  # Wait for a second before polling
    task = runway_client.tasks.retrieve(task_id)
    while task.status not in ['SUCCEEDED', 'FAILED']:
        time.sleep(10)  # Wait for ten seconds before polling
        task = runway_client.tasks.retrieve(task_id)

    # Get the url from the TaskRetrieveResponse
    if task.status == 'SUCCEEDED':
        video_url = task.output[0]
    else:
        video_url = None

    return video_url

def ai_check_message_history(message_history_json: str, main_focus: str, message:str):
    """Check if the message history contains sentiments of the message already. It will return it or try to generate a seamless new message that is tied to the main_focus"""

    """Here is the fully optimized and structured prompt based on your one-liner. This prompt includes a clearly defined identity, objective, and step-by-step logic tailored to maximize performance in ChatGPT:

    

"""

    print(
        f'Generating message to {user_name} based on the given message history.')



    prompt = f"""Please create an initial message, continued message response, or empty response to {user_name} based on our message history based on the given message only if it makes contextual sense: 
    
    Message History JSON:
    ```json
    <insert message history here>
    ````
    """

    # Add the Message History JSON to end of prompt
    prompt += f"\n ### Message History JSON: ```text{message_history_json}```\n\n"

    # Add the New Message to end of prompt
    prompt += f"\n ### New Message: ```text{message}```\n\n"

    # Add the Main Focus to the prompt
    prompt += f"\n ### Main Focus: ```text{analysis}```"

    content = [{"type": "text", "text": prompt}]

    # System prompt to be included in every request
    system_prompt = {
        "role": "system",
        "content": f"""Act like a conversational continuity assistant and dialogue analyzer. You specialize in evaluating JSON-formatted message histories between two users to determine logical continuity and sentiment consistency. Your goal is to either repeat a given message or generate a seamless continuation based on conversational context.
    
    Objective:
    You are provided with:
    1. A `json` string representing the chronological message history between two users.
    2. A `new_message` which contains the content we want to evaluate for repetition or potential continuation.
    3. A `main_focus`, which is the thematic anchor or subject that should guide any new content generation.
    
    Your task:
    Determine whether the `new_message` already reflects sentiments, expressions, or thematic presence in the message history. If so, avoid redundancy. If not, generate a new message that:
    - Logically continues the conversation.
    - Naturally connects to the `main_focus`.
    - Flows seamlessly in tone and topic with the message history.
    
    Instructions:
    Step 1: Parse the JSON string of message history and summarize the conversation's tone, key sentiments, and focal points so far.
    Step 2: Compare this summary with the `new_message` to check if the same intent or sentiment is already expressed. Be strict about avoiding redundancy in intent, sentiment, or meaning—even if the wording differs.
    Step 3: If the history is empty or does not reflect the `new_message`, return the `new_message` as is.
    Step 4: If the `new_message` would be redundant, then generate a fresh, original message that naturally follows the last few entries, maintains thematic alignment with `main_focus`, and enhances the dialogue flow.
    Step 5: Ensure the tone, style, and user perspective are consistent with prior entries.
    
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
        temperature=round(random.uniform(0.5, 0.7), 2),  # Rand temp between .5 and .7

        top_p=round(random.uniform(0.85, 0.95), 2),
        # Encourages diversity in word choice while focusing on high-probability responses for coherent professional content.
        frequency_penalty=round(random.uniform(0.3, 0.5), 2),
        # Minimizes repetitive patterns to ensure unique and varied phrasing.
        presence_penalty=round(random.uniform(0.4, 0.6), 2),
        # Boosts exploration of new ideas while keeping content relevant to the LinkedIn tone.

        # max_tokens=150  # Set token limit as required
        # response_format={"type": "json_object"},
    )

    # Extract and return the model's response
    content = response.choices[0].message.content.strip()
    return content

    # Check if the message history contains the main focus and the message
    if main_focus in message_history and message in message_history:
        return True
    else:
        return False