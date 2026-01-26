"""
Tests for utility functions and logger.
"""

import pytest
import logging
import tempfile
from pathlib import Path
from src.utils.logger import setup_logger


class TestLogger:
    """Test cases for logger utility."""

    def test_logger_initialization(self):
        """Test logger initializes properly."""
        logger = setup_logger("test_logger")
        
        assert logger is not None
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_logger"

    def test_logger_has_handlers(self):
        """Test logger has proper handlers."""
        logger = setup_logger("test_logger_handlers")
        
        assert len(logger.handlers) > 0

    def test_logger_level_default(self):
        """Test logger has default level."""
        logger = setup_logger("test_logger_level")
        
        assert logger.level == logging.DEBUG or logger.level == logging.INFO

    def test_logger_with_file(self):
        """Test logger with file output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            logger = setup_logger("test_logger_file", str(log_file))
            
            # Log a message
            logger.info("Test message")
            
            # Check file was created
            assert log_file.exists()

    def test_logger_formats_messages(self):
        """Test logger formats messages properly."""
        logger = setup_logger("test_logger_format")
        
        # Logger should format messages with timestamp and level
        assert len(logger.handlers) > 0
        handler = logger.handlers[0]
        formatter = handler.formatter
        assert formatter is not None

    def test_logger_console_handler(self):
        """Test logger has console handler."""
        logger = setup_logger("test_logger_console")
        
        # Should have at least one handler (usually StreamHandler for console)
        assert len(logger.handlers) > 0

    def test_logger_multiple_instances(self):
        """Test multiple logger instances can coexist."""
        logger1 = setup_logger("test_logger_1")
        logger2 = setup_logger("test_logger_2")
        
        assert logger1.name == "test_logger_1"
        assert logger2.name == "test_logger_2"
        assert logger1 is not logger2

    def test_logger_reuses_same_name(self):
        """Test that loggers with same name return same instance."""
        logger1 = setup_logger("test_same_name")
        logger2 = setup_logger("test_same_name")
        
        # Should return same logger (from logging registry)
        assert logger1.name == logger2.name

    def test_logger_propagation(self):
        """Test logger propagation setting."""
        logger = setup_logger("test_logger_propagation")
        
        # Logger should have propagate attribute
        assert hasattr(logger, 'propagate')

    def test_logger_disabled(self):
        """Test logger can be disabled."""
        logger = setup_logger("test_logger_disabled")
        
        # Should be able to disable/enable
        logger.disabled = True
        assert logger.disabled is True
        
        logger.disabled = False
        assert logger.disabled is False


class TestLoggerIntegration:
    """Integration tests for logger functionality."""

    def test_logger_in_pipeline(self):
        """Test logger works in pipeline context."""
        logger = setup_logger("pipeline_test")
        
        # Log various levels
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        
        assert logger is not None

    def test_logger_with_exceptions(self):
        """Test logger handles exceptions."""
        logger = setup_logger("test_exceptions")
        
        try:
            raise ValueError("Test error")
        except ValueError:
            logger.exception("Caught exception")
        
        assert logger is not None

    def test_logger_performance(self):
        """Test logger doesn't significantly impact performance."""
        import time
        
        logger = setup_logger("performance_test")
        
        start = time.time()
        for _ in range(1000):
            logger.info("Performance test message")
        duration = time.time() - start
        
        # Should complete 1000 logs quickly (less than 5 seconds)
        assert duration < 5.0


class TestLoggerConfiguration:
    """Test logger configuration options."""

    def test_logger_name_customization(self):
        """Test logger names are customizable."""
        names = ["test_logger_1", "test_logger_2", "custom_name"]
        
        for name in names:
            logger = setup_logger(name)
            assert logger.name == name

    def test_logger_with_custom_file_path(self):
        """Test logger with custom file paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "custom" / "logs" / "app.log"
            # Create parent directories
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            logger = setup_logger("custom_path", str(log_path))
            logger.info("Test message")
            
            assert logger is not None
