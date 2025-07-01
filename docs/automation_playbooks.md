# Automation Playbooks Implementation

This document describes the implementation of automation playbooks for LinkedIn Engagement Manager (LEM).

## Overview

The automation playbooks have been implemented in `src/cqc_lem/app/run_automation.py` to handle the following events:

1. **After Receiving a Recommendation**
2. **After an Interview** 
3. **For a Successful Collaboration**
4. **General Appreciation Messages**

## Implementation Details

### Helper Functions

Four new helper functions have been added to support the automation playbooks:

#### `get_recent_recommendations(user_id: int) -> dict`
- **Purpose**: Retrieves recent recommendations received by the user
- **Returns**: Dictionary with profile_url as key and recommender name as value
- **Current Status**: Placeholder implementation returning empty dict

#### `get_recent_interviews(user_id: int) -> dict`
- **Purpose**: Retrieves recent completed interviews for the user
- **Returns**: Dictionary with profile_url as key and interviewer/company name as value  
- **Current Status**: Placeholder implementation returning empty dict

#### `get_successful_collaborations(user_id: int) -> dict`
- **Purpose**: Retrieves recently completed successful collaborations
- **Returns**: Dictionary with profile_url as key and collaborator name as value
- **Current Status**: Placeholder implementation returning empty dict

#### `get_general_appreciation_contacts(user_id: int) -> dict`
- **Purpose**: Retrieves contacts for general appreciation messages
- **Returns**: Dictionary with profile_url as key and contact info as value (can be string or dict with 'name' and 'topic' keys)
- **Current Status**: Placeholder implementation returning empty dict

### Automation Logic

The automation logic has been implemented in the `automate_appreciation_dms_for_user` function:

#### After Receiving a Recommendation
```python
recommendations_received = get_recent_recommendations(user_id)
for profile_url, name in recommendations_received.items():
    message = f"Hi {name}, thank you so much for the thoughtful recommendation! Your kind words truly mean a lot to me, and I'm grateful for your support. It's wonderful to have colleagues like you who take the time to recognize others' work."
    send_private_dm.apply_async(kwargs={"user_id": user_id, "profile_url": profile_url, "message": message})
```

#### After an Interview
```python
recent_interviews = get_recent_interviews(user_id)
for profile_url, interviewer_name in recent_interviews.items():
    message = f"Hi {interviewer_name}, I wanted to thank you for taking the time to interview me. I really enjoyed our conversation and learning more about the role and your team. I appreciate the opportunity and look forward to hearing from you soon."
    send_private_dm.apply_async(kwargs={"user_id": user_id, "profile_url": profile_url, "message": message})
```

#### For a Successful Collaboration
```python
successful_collaborations = get_successful_collaborations(user_id)
for profile_url, collaborator_name in successful_collaborations.items():
    message = f"Hi {collaborator_name}, I wanted to reach out and thank you for the fantastic collaboration on our recent project. Working with you was truly a pleasure, and I'm proud of what we accomplished together. I hope we get the chance to collaborate again soon!"
    send_private_dm.apply_async(kwargs={"user_id": user_id, "profile_url": profile_url, "message": message})
```

#### General Appreciation
```python
general_appreciation_contacts = get_general_appreciation_contacts(user_id)
for profile_url, contact_info in general_appreciation_contacts.items():
    # Extract name and topic from contact_info if it's a dict, otherwise use it as name
    if isinstance(contact_info, dict):
        name = contact_info.get('name', 'there')
        topic = contact_info.get('topic', 'your recent insights')
    else:
        name = contact_info
        topic = 'your recent insights'
    
    message = f"Hi {name}, I really appreciate your insights on {topic}. Your perspective helped me see things differently, and I'm grateful for the opportunity to learn from you."
    send_private_dm.apply_async(kwargs={"user_id": user_id, "profile_url": profile_url, "message": message})
```

## Message Templates

### Recommendation Thank You
> "Hi [Name], thank you so much for the thoughtful recommendation! Your kind words truly mean a lot to me, and I'm grateful for your support. It's wonderful to have colleagues like you who take the time to recognize others' work."

### Interview Follow-up
> "Hi [Interviewer Name], I wanted to thank you for taking the time to interview me. I really enjoyed our conversation and learning more about the role and your team. I appreciate the opportunity and look forward to hearing from you soon."

### Collaboration Appreciation  
> "Hi [Collaborator Name], I wanted to reach out and thank you for the fantastic collaboration on our recent project. Working with you was truly a pleasure, and I'm proud of what we accomplished together. I hope we get the chance to collaborate again soon!"

### General Appreciation
> "Hi [Name], I really appreciate your insights on [topic]. Your perspective helped me see things differently, and I'm grateful for the opportunity to learn from you."

## Future Enhancements

To make these automation playbooks fully functional, the following implementations are needed:

1. **Event Detection Logic**: Implement actual detection mechanisms for each event type
   - LinkedIn API integration for recommendations
   - Calendar integration for interviews  
   - Project management system integration for collaborations
   - Activity tracking for general appreciation opportunities

2. **Database Integration**: Store and track automation events to avoid duplicate messages

3. **Customization Options**: Allow users to customize message templates

4. **Scheduling Options**: Add configurable timing for sending appreciation messages

5. **Analytics**: Track engagement rates and response rates for different message types

## Testing

A test suite has been created in `tests/test_automation_playbooks.py` to validate the implementation:

- Tests for each helper function
- Integration test for the complete automation flow
- Message template validation

## Usage

The automation playbooks are automatically executed when the `automate_appreciation_dms_for_user` Celery task runs. The task will:

1. Check for each event type using the helper functions
2. Generate appropriate messages for each detected event
3. Queue private DM tasks using `send_private_dm.apply_async()`

Currently, since the helper functions return empty dictionaries, no messages will be sent until the actual event detection logic is implemented.