from cqc_lem.utilities.ai.ai_helper import get_dall_e_image_prompt_from_ai, generate_dall_e_image_from_prompt, \
    get_flux_image_prompt_from_ai, generate_flux1_image_from_prompt, get_runway_ml_video_prompt_from_ai, \
    create_runway_video


def test_create_immage_from_prompt():
    post_content = """
    Unlock the full potential of your AI initiatives! 🚀

In today’s AI-driven landscape, here’s what top-performing teams are focusing on:

🔹 Diversity Fuels Innovation: Building inclusive AI teams isn’t just good practice—it drives breakthrough solutions. Let’s create cultures where diverse perspectives thrive.
🔹 Smart AI Investments: Want to make wise investments in AI startups? Learn the key insights for evaluating potential and maximizing returns.
🔹 Personalization in E-commerce: Personalization is a game-changer for customer engagement. E-commerce leaders, explore case studies that highlight incredible results.
🔹 Cybersecurity Reinvented: In a world of cyber threats, AI-powered threat detection is essential. Stay proactive with the latest strategies in AI security.
🔹 No-Code Automation: AI isn’t just for tech experts! No-code platforms empower teams across the board to innovate and automate without coding skills.

Ready to elevate your AI journey? Let’s explore these insights and strategies together.

Explore more insights and strategies here: https://christopherqueenconsulting.com/blog/

#AI #DiversityInTech #Ecommerce #CyberSecurity #Investment #Innovation #NoCode #CustomerEngagement #BusinessGrowth #AITrends"""

    #image_prompt = get_dall_e_image_prompt_from_ai(post_content)
    image_prompt = get_flux_image_prompt_from_ai(post_content)

    print(f"AI Response: {image_prompt}")

    #image_url = generate_dall_e_image_from_prompt(image_prompt)
    image_url = generate_flux1_image_from_prompt(image_prompt)

    print(f"Generated Image URL: {image_url}")

    video_prompt = get_runway_ml_video_prompt_from_ai(post_content,image_prompt)
    print(f"Runway ML Video Prompt: {video_prompt}")

    video_url = create_runway_video(image_url, video_prompt)
    print(f"Generated Video URL: {video_url}")


if __name__ == "__main__":
    test_create_immage_from_prompt()