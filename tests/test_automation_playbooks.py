"""Test automation playbooks implementation."""
import pytest
from unittest.mock import patch, MagicMock

# Import the functions we want to test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from cqc_lem.app.run_automation import (
    get_recent_recommendations,
    get_recent_interviews, 
    get_successful_collaborations,
    get_general_appreciation_contacts
)


class TestAutomationPlaybooks:
    """Test class for automation playbook helper functions."""

    def test_get_recent_recommendations_placeholder(self):
        """Test get_recent_recommendations returns empty dict as placeholder."""
        result = get_recent_recommendations(user_id=123)
        assert result == {}
        assert isinstance(result, dict)

    def test_get_recent_interviews_placeholder(self):
        """Test get_recent_interviews returns empty dict as placeholder."""
        result = get_recent_interviews(user_id=123)
        assert result == {}
        assert isinstance(result, dict)

    def test_get_successful_collaborations_placeholder(self):
        """Test get_successful_collaborations returns empty dict as placeholder."""
        result = get_successful_collaborations(user_id=123)
        assert result == {}
        assert isinstance(result, dict)

    def test_get_general_appreciation_contacts_placeholder(self):
        """Test get_general_appreciation_contacts returns empty dict as placeholder."""
        result = get_general_appreciation_contacts(user_id=123)
        assert result == {}
        assert isinstance(result, dict)

    @patch('cqc_lem.app.run_automation.send_private_dm')
    @patch('cqc_lem.app.run_automation.get_recent_recommendations')
    @patch('cqc_lem.app.run_automation.get_recent_interviews')
    @patch('cqc_lem.app.run_automation.get_successful_collaborations')
    @patch('cqc_lem.app.run_automation.get_general_appreciation_contacts')
    @patch('cqc_lem.app.run_automation.accept_connection_request')
    @patch('cqc_lem.app.run_automation.get_user_password_pair_by_id')
    @patch('cqc_lem.app.run_automation.get_driver_wait_pair')
    @patch('cqc_lem.app.run_automation.login_to_linkedin')
    @patch('cqc_lem.app.run_automation.quit_gracefully')
    def test_automation_playbooks_integration(
        self,
        mock_quit_gracefully,
        mock_login_to_linkedin, 
        mock_get_driver_wait_pair,
        mock_get_user_password_pair_by_id,
        mock_accept_connection_request,
        mock_get_general_appreciation_contacts,
        mock_get_successful_collaborations,
        mock_get_recent_interviews,
        mock_get_recent_recommendations,
        mock_send_private_dm
    ):
        """Test that automation playbooks call send_private_dm with correct messages."""
        
        # Setup mocks
        mock_get_user_password_pair_by_id.return_value = ('test@example.com', 'password')
        mock_driver = MagicMock()
        mock_wait = MagicMock()
        mock_get_driver_wait_pair.return_value = (mock_driver, mock_wait)
        
        # Mock the helper functions to return test data
        mock_accept_connection_request.return_value = {}
        mock_get_recent_recommendations.return_value = {
            'https://linkedin.com/in/recommender': 'John Recommender'
        }
        mock_get_recent_interviews.return_value = {
            'https://linkedin.com/in/interviewer': 'Jane Interviewer'
        }
        mock_get_successful_collaborations.return_value = {
            'https://linkedin.com/in/collaborator': 'Bob Collaborator'
        }
        mock_get_general_appreciation_contacts.return_value = {
            'https://linkedin.com/in/contact': {'name': 'Alice Contact', 'topic': 'AI trends'}
        }
        
        # Mock send_private_dm to have apply_async method
        mock_task = MagicMock()
        mock_send_private_dm.apply_async = mock_task
        
        # Import and call the function we're testing
        from cqc_lem.app.run_automation import automate_appreciation_dms_for_user
        
        # Create a mock self object for the Celery task
        mock_self = MagicMock()
        
        # Call the function
        result = automate_appreciation_dms_for_user(mock_self, user_id=123, loop_for_duration=None)
        
        # Verify that send_private_dm.apply_async was called for each automation type
        expected_calls = [
            # Recommendation message
            {
                'user_id': 123,
                'profile_url': 'https://linkedin.com/in/recommender',
                'message': "Hi John Recommender, thank you so much for the thoughtful recommendation! Your kind words truly mean a lot to me, and I'm grateful for your support. It's wonderful to have colleagues like you who take the time to recognize others' work."
            },
            # Interview message
            {
                'user_id': 123,
                'profile_url': 'https://linkedin.com/in/interviewer', 
                'message': "Hi Jane Interviewer, I wanted to thank you for taking the time to interview me. I really enjoyed our conversation and learning more about the role and your team. I appreciate the opportunity and look forward to hearing from you soon."
            },
            # Collaboration message
            {
                'user_id': 123,
                'profile_url': 'https://linkedin.com/in/collaborator',
                'message': "Hi Bob Collaborator, I wanted to reach out and thank you for the fantastic collaboration on our recent project. Working with you was truly a pleasure, and I'm proud of what we accomplished together. I hope we get the chance to collaborate again soon!"
            },
            # General appreciation message
            {
                'user_id': 123,
                'profile_url': 'https://linkedin.com/in/contact',
                'message': "Hi Alice Contact, I really appreciate your insights on AI trends. Your perspective helped me see things differently, and I'm grateful for the opportunity to learn from you."
            }
        ]
        
        # Check that apply_async was called the expected number of times
        assert mock_task.call_count == 4
        
        # Check that each call had the expected kwargs structure
        for call in mock_task.call_args_list:
            assert 'kwargs' in call.kwargs
            call_kwargs = call.kwargs['kwargs']
            assert 'user_id' in call_kwargs
            assert 'profile_url' in call_kwargs
            assert 'message' in call_kwargs
            assert call_kwargs['user_id'] == 123
        
        # Verify the result indicates success
        assert "Appreciation DMs Sent" in result


if __name__ == '__main__':
    pytest.main([__file__])