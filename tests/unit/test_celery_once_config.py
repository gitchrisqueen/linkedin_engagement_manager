"""Tests for celery-once configuration with different broker types."""

import os
import pytest
from unittest.mock import patch

# Mock OpenAI to avoid API key requirement
with patch.dict(os.environ, {'OPENAI_API_KEY': 'dummy'}):
    from cqc_lem.app.my_celery import get_celery_once_config


class TestCeleryOnceConfig:
    """Test celery-once configuration for different broker types."""
    
    def test_redis_broker_config(self):
        """Test configuration when using Redis as broker."""
        with patch('cqc_lem.app.my_celery.broker_url', 'redis://redis:6379/0'):
            config = get_celery_once_config()
            
            assert config['backend'] == 'celery_once.backends.Redis'
            assert config['settings']['url'] == 'redis://redis:6379/2'  # Different DB for once
            assert config['settings']['default_timeout'] == 60 * 60
            assert config['settings']['blocking'] is True
            assert config['settings']['blocking_timeout'] == 30
    
    def test_sqs_broker_config(self):
        """Test configuration when using SQS as broker."""
        with patch('cqc_lem.app.my_celery.broker_url', 'sqs://'):
            config = get_celery_once_config()
            
            assert config['backend'] == 'celery_once.backends.Redis'
            assert config['settings']['url'] == 'redis://redis:6379/2'  # Uses default Redis for once
            assert config['settings']['default_timeout'] == 60 * 60
            assert config['settings']['blocking'] is True
            assert config['settings']['blocking_timeout'] == 30
    
    def test_sqs_broker_with_custom_redis(self):
        """Test SQS broker with custom Redis host."""
        with patch('cqc_lem.app.my_celery.broker_url', 'sqs://'), \
             patch.dict(os.environ, {'REDIS_HOST': 'elasticache.example.com', 'REDIS_PORT': '6380'}):
            config = get_celery_once_config()
            
            assert config['backend'] == 'celery_once.backends.Redis'
            assert config['settings']['url'] == 'redis://elasticache.example.com:6380/2'
    
    def test_elasticcache_broker_config(self):
        """Test configuration when using elasticcache:// as broker (legacy)."""
        with patch('cqc_lem.app.my_celery.broker_url', 'elasticcache://'):
            config = get_celery_once_config()
            
            assert config['backend'] == 'celery_once.backends.Redis'
            assert config['settings']['url'] == 'redis://redis:6379/2'
    
    def test_unknown_broker_fallback(self):
        """Test fallback to File backend for unknown broker types."""
        with patch('cqc_lem.app.my_celery.broker_url', 'unknown://broker'):
            config = get_celery_once_config()
            
            assert config['backend'] == 'celery_once.backends.File'
            assert config['settings']['location'] == '/tmp/celery_once'
            assert config['settings']['default_timeout'] == 60 * 60
    
    def test_redis_url_with_custom_db(self):
        """Test Redis broker with custom database number."""
        with patch('cqc_lem.app.my_celery.broker_url', 'redis://redis:6379/5'):
            config = get_celery_once_config()
            
            assert config['backend'] == 'celery_once.backends.Redis'
            assert config['settings']['url'] == 'redis://redis:6379/2'  # Always uses DB 2 for once
    
    def test_redis_url_with_auth_and_custom_db(self):
        """Test Redis broker with authentication and custom database number."""
        with patch('cqc_lem.app.my_celery.broker_url', 'redis://user:pass@redis:6380/1'):
            config = get_celery_once_config()
            
            assert config['backend'] == 'celery_once.backends.Redis'
            assert config['settings']['url'] == 'redis://user:pass@redis:6380/2'  # Preserves auth, uses DB 2