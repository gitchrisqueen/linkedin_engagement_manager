from cqc_lem.run_automation import accept_connection_request, send_private_dm


def test_accept_invites():
    user_id = 60

    invitations_accepted = accept_connection_request(user_id)

    # Display how many invitations found
    print(f"Invitations Found: {len(invitations_accepted)}")

    # Send a private DM for each inviations
    for profile_url, name in invitations_accepted.items():
        message = f"Hi {name}, I appreciate you connecting with me on LinkedIn. I look forward to learning more about you and your work."
        # Print the message and where its going to
        send_private_dm(user_id, profile_url, message)

def test_send_dm():
    user_id = 60
    profile_url = "https://www.linkedin.com/in/meet-sabhaya/"
    name = "Meet Sabhaya"
    message = f"Hi {name}, I appreciate you connecting with me on LinkedIn. I look forward to learning more about you and your work."
    send_private_dm(user_id, profile_url, message)




if __name__ == "__main__":
    #test_accept_invites()
    test_send_dm()
