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

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[system_prompt, user_message],  # System prompt + current user prompt
        temperature=round(random.uniform(0.4, 0.6), 2),  # Rand temp between .5 and .7
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

    # Use json to output to string
    linked_in_profile_json = linked_user_profile.model_dump_json()

    prompt = f"""Please create a thought leadership post for me based on my LinkedIn Profile information.

        Craft the post to appeal to readers who are currently in the {buyer_stage} of their journey.
        
        # Buyer Stages:
        - Awareness: Introduce key industry challenges and trends that my expertise addresses.
        - Consideration: Highlight unique solutions, strategies, or frameworks that showcase my approach to common industry problems.
        - Decision: Provide insight into how my experience and skills make me a strong partner for organizations seeking expertise in relevant industries or skills areas].
        
        Conclude with an engaging call to action that encourages readers at the specified stage to connect or learn more.
        
        {get_viral_linked_post_prompt_suffix()}
        
        """

    # Add the Linked JSON profile to end of prompt
    prompt += f"\n ### LinkedIn Profile: {linked_in_profile_json}"

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
        # max_tokens=150  # Set token limit as required
        # response_format={"type": "json_object"},
    )

    # Extract and return the model's response
    content = response.choices[0].message.content.strip()
    return content


def get_industry_news_post_from_ai(linked_user_profile: LinkedInProfile, buyer_stage: str):
    """
       Generate a post sharing industry news based on the LinkedIn user's profile and the intended buyer stage, along with the user's commentary.
    """
    # Find trending topics or news in the user's industry and craft a commentary around it
    # Example content: "With recent changes in [industry], we’re seeing a shift toward..."

    # Use json to output to string
    linked_in_profile_json = linked_user_profile.model_dump_json()

    prompt = f"""Please create a post sharing recent industry news based on my LinkedIn Profile information provided below. 
    Tailor the post to readers in the {buyer_stage} of their journey and include my own commentary to add perspective.
            
    # Buyer Stages to Consider:
    - Awareness: Introduce the news topic with broad insights on its relevance to the industry.
    - Consideration: Frame the topic in a way that helps readers think strategically about addressing this development.
    - Decision: Emphasize the importance of expert insights and how my expertise can be valuable in navigating this trend.
    
    """

    # Add the Linked JSON profile to end of prompt
    prompt += f"\n ### LinkedIn Profile: {linked_in_profile_json}"

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
        # max_tokens=150  # Set token limit as required
        # response_format={"type": "json_object"},
    )

    # Extract and return the model's response
    content = response.choices[0].message.content.strip()
    return content


def get_personal_story_post_from_ai(linked_user_profile: LinkedInProfile, stage: str):
    """
    Generate a post sharing a personal or professional story, based on the user's profile.
    """
    # Pull from the user's recent milestones, achievements, or challenges
    # Example content: "Reflecting on my journey as a [job title], I’ve learned that..."

    # Use json to output to string
    linked_in_profile_json = linked_user_profile.model_dump_json()

    prompt = f"""Please create a story-based post for me, reflecting on a personal or professional milestone, achievement, or challenge, using the information from my LinkedIn Profile provided below. 
    Tailor the story to connect with readers in the {stage} stage of their journey.
    
    # Buyer Stages to Consider:
    - Awareness: Share a story that introduces me as a thoughtful leader, highlighting a key career insight or turning point.
    - Consideration: Emphasize lessons learned from a specific challenge or achievement, showing how my experience can guide or inspire similar efforts.
    - Decision: Position my expertise as a valuable resource for those facing similar challenges, demonstrating the depth of my skills and experience.
    
    """

    # Add the Linked JSON profile to end of prompt
    prompt += f"\n ### LinkedIn Profile: {linked_in_profile_json}"

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

    prompt = f"""Please generate a question or prompt to encourage engagement from my followers based on the information in my LinkedIn Profile below. 
    Tailor the question to resonate with readers in the {stage} of their journey.

    # Buyer Stages to Consider:
    - Awareness: Ask a thought-provoking question to spark curiosity about industry challenges or trends.
    - Consideration: Pose a question that invites followers to share strategies or insights on common challenges.
    - Decision: Encourage a deeper conversation around specific pain points or decision-making criteria, drawing on my expertise.
    
    """

    # Add the Linked JSON profile to end of prompt
    prompt += f"\n ### LinkedIn Profile: {linked_in_profile_json}"

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
    Tailor the post to appeal to readers in the {stage} of their journey, using my LinkedIn profile details to make the summary relevant to my role and industry.

    """

    # Add the Linked JSON profile to end of prompt
    prompt += f"\n ### LinkedIn Profile: {linked_in_profile_json}"

    prompt += f"""\n\n Buyer Stages to Consider:
    - Awareness: Summarize the article with broad insights into industry trends and challenges.
    - Consideration: Frame the post to highlight actionable strategies or best practices discussed in the article.
    - Decision: Emphasize the practical value of the insights for decision-makers and align the tone to demonstrate my expertise in the area.
    
    ### Blog Post URL: {blog_post_url}
    
    --- 
    
    ### Blog Post Content: {blog_post_content}
    
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
        Tailor the post to appeal to readers in the {stage} of their journey, using my LinkedIn profile details to make the summary relevant to my role and industry.

               """

    # Add the Linked JSON profile to end of prompt
    prompt += f"\n ### LinkedIn Profile: {linked_in_profile_json}"

    prompt += f"""---\n\n Buyer Stages to Consider:
        - Awareness: Summarize the website content with broad insights into industry trends and challenges.
        - Consideration: Frame the post to highlight actionable strategies or best practices discussed in the website content.
        - Decision: Emphasize the practical value of the insights for decision-makers and align the tone to demonstrate my expertise in the area.

        ### Website URL: {url}

        --- 

        ### Website Content: {content}

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